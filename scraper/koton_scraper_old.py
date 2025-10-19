# scraper/koton_scraper.py

import json
import re
import requests
import time
import random
import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

API_URL = "http://127.0.0.1:8000"
USER_DATA_DIR = Path(__file__).parent / "browser_data"
ALL_URLS_FILE = Path(__file__).parent / "all_urls.json"
SCRAPED_URLS_FILE = Path(__file__).parent / "scraped_urls.json"
PERMANENTLY_FAILED_URLS_FILE = Path(__file__).parent / "permanently_failed_urls.txt"
WORKING_PROXIES_LIST_FILE = Path(__file__).parent / "working_proxies_list.txt"

CATEGORIES_TO_SCRAPE = [
    "https://www.koton.com/kadin-giyim/", "https://www.koton.com/kadin-koton-jeans/",
    "https://www.koton.com/sezon-trendleri", "https://www.koton.com/kadin-abiye-davet/",
    "https://www.koton.com/kadin-ic-giyim/", "https://www.koton.com/sportclub/",
    "https://www.koton.com/kadin-ofis-stili/", "https://www.koton.com/kadin-aksesuar/",
    "https://www.koton.com/genc-kadin-yeni-gelenler/", "https://www.koton.com/genc-kadin-cok-satanlar/",
    "https://www.koton.com/genc-kadin-giyim/", "https://www.koton.com/coklu-paket-urunler-kadin/",
    "https://www.koton.com/erkek-yeni-gelenler/", "https://www.koton.com/erkek-giyim/",
    "https://www.koton.com/erkek-koton-jeans/", "https://www.koton.com/erkek-anasayfa",
    "https://www.koton.com/erkek-pijama-ev-ve-ic-giyim/", "https://www.koton.com/erkek-spor-giyim/",
    "https://www.koton.com/erkek-aksesuar/", "https://www.koton.com/indirim-anasayfa",
    "https://www.koton.com/yuzde50-indirimli-urunler/",
]

def save_item_to_db(item_data: dict) -> bool:
    try:
        serial_code = item_data.get("serial_code")
        if not serial_code:
            print("❌ No serial code found, cannot save.")
            return False
        response = requests.get(f"{API_URL}/items/by_serial_code/{serial_code}")
        if response.status_code == 200:
            print(f"-> Item '{serial_code}' already exists. Skipping.")
            return True
        if response.status_code == 404:
            print(f"-> New item '{serial_code}'. Saving...")
            create_response = requests.post(f"{API_URL}/items/", json=item_data)
            if create_response.status_code == 200:
                print(f"✅ Successfully saved item '{serial_code}'.")
                return True
            else:
                print(f"❌ Failed to save item. API Status: {create_response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Error saving to DB: {e}")
    return False

def find_first_json_object(text: str):
    open_braces, start_index = 0, -1
    for i, char in enumerate(text):
        if char == '{':
            if start_index == -1: start_index = i
            open_braces += 1
        elif char == '}':
            open_braces -= 1
            if open_braces == 0 and start_index != -1:
                return text[start_index:i+1]
    return None

def scrape_koton_product(page: Page, url: str) -> bool:
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        html_content = page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        product_data = None
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            if script.string and '"@type": "Product"' in script.string:
                json_string = find_first_json_object(script.string)
                if json_string:
                    product_data = json.loads(json_string)
                    break
        if not product_data: raise ValueError("Could not find/parse Product JSON-LD.")

        ga4_script = soup.find('div', class_='js-ga4-product')
        if not ga4_script or not ga4_script.string: raise ValueError("Could not find GA4 data.")
        
        ga4_data = json.loads(ga4_script.string)
        serial_code = ga4_data.get('base_code')

        scraped_item = {
            "name": product_data.get('name'), "serial_code": serial_code, "store": "Koton", "item_url": url,
            "image_url": product_data.get('image', [None])[0]
        }
        return save_item_to_db(scraped_item)
    except Exception as e:
        print(f"❌ Scrape failed for {url}. Error: {e.__class__.__name__}")
        return False

def crawl_koton_category(page: Page, category_url: str):
    print(f"\n{'='*20}\nCrawling: {category_url}\n{'='*20}")
    unique_urls, page_number = set(), 1
    try:
        while True:
            page.goto(f"{category_url}?page={page_number}", wait_until="domcontentloaded", timeout=60000)
            if page.locator('text="İnsan olduğunuzu doğrulayalım"').is_visible():
                print("❗ CAPTCHA Detected during crawl. Skipping category.")
                break
            
            product_links = page.locator('a.product-link').all()
            if not product_links:
                print("Found 0 product links. Assuming end of category.")
                break
                
            for link in product_links:
                if href := link.get_attribute('href'): unique_urls.add(f"https://www.koton.com{href}")
            
            print(f"Page {page_number}: Found {len(product_links)} links. Total unique: {len(unique_urls)}")
            if page_number > 500: break
            page_number += 1
            time.sleep(random.uniform(2, 5))
        return list(unique_urls)
    except Exception as e:
        print(f"❌ Error during category crawl: {e}")
        return list(unique_urls)

if __name__ == "__main__":
    if not WORKING_PROXIES_LIST_FILE.exists():
        print(f"ERROR: '{WORKING_PROXIES_LIST_FILE.name}' not found. Please run proxy_tester.py first.")
        exit()
    
    # --- NEW: LOGIC TO HANDLE DIFFERENT PROXY FORMATS ---
    raw_proxies = []
    with open(WORKING_PROXIES_LIST_FILE, 'r') as f:
        raw_proxies = [line.strip() for line in f if line.strip()]
    
    working_proxies = []
    for proxy in raw_proxies:
        if '://' not in proxy:
            working_proxies.append(f"http://{proxy}")
        else:
            working_proxies.append(proxy)
    # --- END OF NEW LOGIC ---

    if not working_proxies:
        print("ERROR: working_proxies_list.txt is empty.")
        exit()
    print(f"Loaded and formatted {len(working_proxies)} proxies to use for scraping.")
    
    all_product_urls_to_scrape = []
    if Path(ALL_URLS_FILE).exists():
        print("Loading URLs from all_urls.json...")
        with open(ALL_URLS_FILE, 'r') as f: all_product_urls_to_scrape = json.load(f)
    else:
        print("No URL list found. Starting fresh crawl...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            temp_urls = set()
            for category_url in CATEGORIES_TO_SCRAPE:
                temp_urls.update(crawl_koton_category(page, category_url))
            all_product_urls_to_scrape = list(temp_urls)
            with open(ALL_URLS_FILE, 'w') as f: json.dump(all_product_urls_to_scrape, f, indent=2)
            browser.close()
            print(f"Saved {len(all_product_urls_to_scrape)} URLs to all_urls.json.")
    
    scraped_urls = set()
    if SCRAPED_URLS_FILE.exists():
        with open(SCRAPED_URLS_FILE, 'r') as f: scraped_urls = {line.strip() for line in f}
    
    urls_to_process = [url for url in all_product_urls_to_scrape if url not in scraped_urls]
    print(f"Found {len(scraped_urls)} previously scraped URLs. {len(urls_to_process)} items remaining.")

    with sync_playwright() as p:
        browser, context, page = None, None, None
        
        for i, url in enumerate(urls_to_process, 1):
            print(f"\n--- Processing Master List Item {i}/{len(urls_to_process)} ---")
            scraped_successfully = False
            
            for attempt in range(len(working_proxies) + 1):
                if not browser or not browser.is_connected():
                    if not working_proxies:
                        print("🚫 Ran out of working proxies. Exiting.")
                        break
                    
                    current_proxy = random.choice(working_proxies)
                    proxy_settings = {"server": current_proxy}
                    
                    print(f"🔄 Starting new browser with proxy: {current_proxy} ({len(working_proxies)} left)")
                    
                    try:
                        browser = p.chromium.launch(headless=True, proxy=proxy_settings)
                        context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36')
                        page = context.new_page()
                    except Exception as e:
                        print(f"❌ Failed to launch browser with {current_proxy}. Removing it from list.")
                        working_proxies.remove(current_proxy)
                        if browser: browser.close()
                        continue

                success = scrape_koton_product(page, url)

                if success:
                    scraped_successfully = True
                    with open(SCRAPED_URLS_FILE, 'a') as f: f.write(f"{url}\n")
                    break
                else:
                    print("...Current proxy may be bad. Closing browser to try a new one.")
                    browser.close()
                    if current_proxy in working_proxies:
                        working_proxies.remove(current_proxy)

            if not scraped_successfully:
                print(f"❌ All available proxies failed for URL: {url}. Logging to permanently_failed_urls.txt")
                with open(PERMANENTLY_FAILED_URLS_FILE, 'a') as f: f.write(f"{url}\n")
            
            time.sleep(random.uniform(1, 2))

        if browser and browser.is_connected(): browser.close()
    print("\nFull scrape process finished.")