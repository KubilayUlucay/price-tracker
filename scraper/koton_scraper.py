# scraper/koton_scraper.py

import json
import re
import requests
import time
import random
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

API_URL = "http://127.0.0.1:8000"
USER_DATA_DIR = Path(__file__).parent / "browser_data"

# --- NEW: Define paths for our progress/state files ---
ALL_URLS_FILE = Path(__file__).parent / "all_urls.json"
SCRAPED_URLS_FILE = Path(__file__).parent / "scraped_urls.json"

CATEGORIES_TO_SCRAPE = [
    "https://www.koton.com/kadin-giyim/",
    "https://www.koton.com/kadin-koton-jeans/",
    "https://www.koton.com/sezon-trendleri",
    "https://www.koton.com/kadin-abiye-davet/",
    "https://www.koton.com/kadin-ic-giyim/",
    "https://www.koton.com/sportclub/",
    "https://www.koton.com/kadin-ofis-stili/",
    "https://www.koton.com/kadin-aksesuar/",
    "https://www.koton.com/genc-kadin-yeni-gelenler/",
    "https://www.koton.com/genc-kadin-cok-satanlar/",
    "https://www.koton.com/genc-kadin-giyim/",
    "https://www.koton.com/coklu-paket-urunler-kadin/",
    "https://www.koton.com/erkek-yeni-gelenler/",
    "https://www.koton.com/erkek-giyim/",
    "https://www.koton.com/erkek-koton-jeans/",
    "https://www.koton.com/erkek-anasayfa",
    "https://www.koton.com/erkek-pijama-ev-ve-ic-giyim/",
    "https://www.koton.com/erkek-spor-giyim/",
    "https://www.koton.com/erkek-aksesuar/",
    "https://www.koton.com/indirim-anasayfa",
    "https://www.koton.com/yuzde50-indirimli-urunler/",
]

def save_item_to_db(item_data: dict):
    # This function is unchanged
    try:
        serial_code = item_data.get("serial_code")
        if not serial_code:
            print("❌ No serial code found, cannot save to DB.")
            return False

        response = requests.get(f"{API_URL}/items/by_serial_code/{serial_code}")
        
        if response.status_code == 200:
            print(f"-> Item '{serial_code}' already exists. Skipping.")
            return True # Return True as it's a "successful" outcome for this item
            
        if response.status_code == 404:
            print(f"-> New item '{serial_code}'. Saving to database...")
            create_response = requests.post(f"{API_URL}/items/", json=item_data)
            
            if create_response.status_code == 200:
                print(f"✅ Successfully saved item '{serial_code}'.")
                return True
            else:
                print(f"❌ Failed to save item. API Status: {create_response.status_code}, Response: {create_response.json()}")
                return False
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the backend API. Is the uvicorn server running?")
        return False
    except Exception as e:
        print(f"❌ An error occurred while saving to DB: {e}")
        return False

def scrape_koton_product(page: Page, url: str):
    # This function now returns True on success and False on failure
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        html_content = page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        product_data = None
        for script in soup.find_all('script', type='application/ld+json'):
            if script.string and '"@type":"Product"' in script.string:
                product_data = json.loads(script.string)
                break
        if not product_data:
            raise ValueError("Could not find Product JSON-LD.")

        ga4_script = soup.find('div', class_='js-ga4-product')
        if not ga4_script or not ga4_script.string:
            raise ValueError("Could not find GA4 product data for serial code.")
        
        ga4_data = json.loads(ga4_script.string)
        serial_code = ga4_data.get('base_code')

        scraped_item = {
            "name": product_data.get('name'), "serial_code": serial_code,
            "store": "Koton", "item_url": url,
            "image_url": product_data.get('image', [])[0]
        }
        return save_item_to_db(scraped_item)
    except Exception as e:
        print(f"❌ Failed to scrape product page {url}. Error: {e}")
        return False

def crawl_koton_category(page: Page, category_url: str):
    # This function is unchanged
    print(f"\n{'='*20}\nStarting crawl for category: {category_url}\n{'='*20}")
    unique_urls = set()
    page_number = 1
    try:
        while True:
            page_url = f"{category_url}?page={page_number}"
            print(f"--- Scanning page {page_number}... ---")
            page.goto(page_url, wait_until="domcontentloaded", timeout=60000)
            if page.locator('text="İnsan olduğunuzu doğrulayalım"').is_visible():
                print("❗ BOT DETECTION ACTIVATED. Please solve the CAPTCHA in the browser window.")
                page.wait_for_selector('.list__products', timeout=300000)
                print("✅ CAPTCHA likely solved. Retrying current page...")
                continue
            product_links = page.locator('a.product-link').all()
            if not product_links:
                print("Found 0 product links. Assuming end of category.")
                break
            for link in product_links:
                href = link.get_attribute('href')
                if href:
                    unique_urls.add(f"https://www.koton.com{href}")
            print(f"Scanned {len(product_links)} links. Total unique for category: {len(unique_urls)}")
            if page_number > 500: break
            page_number += 1
            time.sleep(random.uniform(2, 5))
        print(f"Finished category crawl. Found {len(unique_urls)} total unique products.")
        return list(unique_urls)
    except Exception as e:
        print(f"❌ An error occurred during category crawl: {e}")
        return list(unique_urls)

if __name__ == "__main__":
    # --- NEW RESUMABLE LOGIC ---
    
    # 1. Load the list of all URLs if it exists, otherwise crawl for it.
    if ALL_URLS_FILE.exists():
        print("Found existing URL list. Loading from all_urls.json...")
        with open(ALL_URLS_FILE, 'r') as f:
            all_product_urls_to_scrape = json.load(f)
    else:
        print("No URL list found. Starting fresh crawl of all categories...")
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(user_data_dir=USER_DATA_DIR, headless=False)
            page = context.new_page()
            
            temp_urls = set()
            for category_url in CATEGORIES_TO_SCRAPE:
                product_urls = crawl_koton_category(page, category_url)
                temp_urls.update(product_urls)
                time.sleep(random.uniform(5, 10))
            
            all_product_urls_to_scrape = list(temp_urls)
            with open(ALL_URLS_FILE, 'w') as f:
                json.dump(all_product_urls_to_scrape, f, indent=2)
            print(f"Saved {len(all_product_urls_to_scrape)} URLs to all_urls.json.")
            context.close()

    # 2. Load the set of URLs that have already been scraped.
    scraped_urls = set()
    if SCRAPED_URLS_FILE.exists():
        with open(SCRAPED_URLS_FILE, 'r') as f:
            # Read one URL per line
            scraped_urls = set(line.strip() for line in f)
    print(f"Found {len(scraped_urls)} previously scraped URLs. They will be skipped.")

    # 3. Start the main scraping loop.
    print(f"\n{'*'*50}\nTOTAL UNIQUE PRODUCTS TO PROCESS: {len(all_product_urls_to_scrape)}\n{'*'*50}")
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(user_data_dir=USER_DATA_DIR, headless=False)
        page = context.new_page()

        for i, url in enumerate(all_product_urls_to_scrape, 1):
            print(f"--- Processing Master List Item {i}/{len(all_product_urls_to_scrape)} ---")
            
            # --- The RESUME LOGIC ---
            if url in scraped_urls:
                print(f"URL already scraped. Skipping: {url}")
                continue

            success = scrape_koton_product(page, url)
            
            # --- The PROGRESS SAVING LOGIC ---
            if success:
                with open(SCRAPED_URLS_FILE, 'a') as f:
                    f.write(f"{url}\n")
            
            time.sleep(random.uniform(1, 3))

        print("\nFull crawl and scrape process finished.")
        context.close()