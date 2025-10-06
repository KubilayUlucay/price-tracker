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

CATEGORIES_TO_SCRAPE = [
    # A smaller list for faster testing. Uncomment the rest when ready.
    "https://www.koton.com/kadin-aksesuar/"
    # "https://www.koton.com/tr/kadin-elbise/",
    # "https://www.koton.com/tr/erkek-gomlek/",
    # "https://www.koton.com/kadin-giyim/",
    # "https://www.koton.com/kadin-koton-jeans/",
    # ... etc.
]


def save_item_to_db(item_data: dict):
    # ... this function is unchanged ...
    try:
        serial_code = item_data.get("serial_code")
        if not serial_code:
            print("❌ No serial code found, cannot save to DB.")
            return

        response = requests.get(f"{API_URL}/items/by_serial_code/{serial_code}")
        
        if response.status_code == 200:
            print(f"-> Item '{serial_code}' already exists. Skipping.")
            return
            
        if response.status_code == 404:
            print(f"-> New item '{serial_code}'. Saving to database...")
            create_response = requests.post(f"{API_URL}/items/", json=item_data)
            
            if create_response.status_code == 200:
                print(f"✅ Successfully saved item '{serial_code}'.")
            else:
                print(f"❌ Failed to save item. API Status: {create_response.status_code}, Response: {create_response.json()}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the backend API. Is the uvicorn server running?")
    except Exception as e:
        print(f"❌ An error occurred while saving to DB: {e}")


def scrape_koton_product(page: Page, url: str):
    # ... this function is unchanged ...
    try:
        print(f"\nScraping product: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        html_content = page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        product_data = None
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            if script.string:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'Product':
                    product_data = data
                    break

        if not product_data:
            raise ValueError("Could not find Product JSON-LD.")

        ga4_script = soup.find('div', class_='js-ga4-product')
        if not ga4_script or not ga4_script.string:
            raise ValueError("Could not find GA4 product data for serial code.")
        
        ga4_data = json.loads(ga4_script.string)
        serial_code = ga4_data.get('base_code')

        scraped_item = {
            "name": product_data.get('name'),
            "serial_code": serial_code,
            "store": "Koton",
            "item_url": url,
            "image_url": product_data.get('image', [])[0]
        }

        save_item_to_db(scraped_item)
        
    except Exception as e:
        print(f"❌ Failed to scrape product page {url}. Error: {e}")


def crawl_koton_category(page: Page, category_url: str):
    """Visits a category, handles pagination, collects all product links."""
    print(f"\n{'='*20}\nStarting crawl for category: {category_url}\n{'='*20}")
    unique_urls = set()

    try:
        page.goto(category_url, wait_until="networkidle", timeout=60000)

        # We must solve the CAPTCHA on the first run manually.
        if page.locator('text="İnsan olduğunuzu doğrulayalım"').is_visible():
            print("❗ BOT DETECTION ACTIVATED. Please solve the CAPTCHA in the browser window.")
            print("   The script will wait for you to solve it...")
            # Wait until the user solves the captcha and the main product grid appears.
            page.wait_for_selector('.list__products', timeout=300000) # 5 minute timeout
            print("✅ CAPTCHA solved. Continuing...")

        last_page_number = 30
        pagination_links = page.locator('.pagination__item a').all()
        if pagination_links:
            last_page_text = pagination_links[-2].inner_text()
            if last_page_text.isdigit():
                last_page_number = int(last_page_text)
        print(f"Found {last_page_number} pages for this category.")

        for i in range(1, last_page_number + 1):
            page_url = f"{category_url}?page={i}"
            print(f"--- Scanning page {i}/{last_page_number} ---")
            page.goto(page_url, wait_until="domcontentloaded", timeout=60000)

            product_links = page.locator('a.product-link').all()
            for link in product_links:
                href = link.get_attribute('href')
                if href:
                    full_url = f"https://www.koton.com{href}"
                    unique_urls.add(full_url)
            
            sleep_time = random.uniform(2, 5)
            print(f"Scanned {len(product_links)} links. Waiting for {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
        
        print(f"Found {len(unique_urls)} total unique product links in this category.")
        return list(unique_urls)

    except Exception as e:
        print(f"❌ An error occurred during category crawl: {e}")
        return []


if __name__ == "__main__":
    with sync_playwright() as p:
        # Launch a persistent browser context that saves cookies and session data
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False, # We MUST run in headed mode to solve the initial CAPTCHA
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        all_product_urls_to_scrape = set()
        for category_url in CATEGORIES_TO_SCRAPE:
            product_urls = crawl_koton_category(page, category_url)
            all_product_urls_to_scrape.update(product_urls)
            time.sleep(random.uniform(5, 10))

        print(f"\n{'*'*50}\nTOTAL UNIQUE PRODUCTS: {len(all_product_urls_to_scrape)}\n{'*'*50}")
        
        if all_product_urls_to_scrape:
            for i, url in enumerate(list(all_product_urls_to_scrape), 1):
                print(f"--- Scraping Master List Item {i}/{len(all_product_urls_to_scrape)} ---")
                scrape_koton_product(page, url)
                time.sleep(random.uniform(1, 3))

        print("\nFull crawl and scrape process finished. You can close the browser.")
        context.close()