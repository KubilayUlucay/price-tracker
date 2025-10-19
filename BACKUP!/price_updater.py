# scraper/price_updater.py

import requests
import time
import random
import re
from playwright.sync_api import sync_playwright, Page

API_URL = "http://127.0.0.1:8000"

def get_all_items_from_db():
    """Fetches all items from our API."""
    try:
        response = requests.get(f"{API_URL}/items/")
        if response.status_code == 200:
            print(f"Successfully fetched {len(response.json())} items from the database.")
            return response.json()
        else:
            print("Failed to fetch items from API.")
            return []
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the backend API. Is the uvicorn server running?")
        return None

def scrape_and_update_price(page: Page, item: dict):
    """Visits an item's URL, scrapes its current price, and saves it to the DB."""
    item_id = item['id']
    url = item['item_url']
    
    try:
        print(f"-> Checking price for: {item['name'][:50]}...")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Scrape just the price
        price_container_selector = "div.price__price"
        price_text = page.locator(price_container_selector).inner_text()
        price_clean = re.sub(r'[^\d,]', '', price_text).replace(',', '.')
        current_price = float(price_clean)

        # Prepare data for the API
        price_payload = {"price": current_price}

        # Post the new price to the API
        response = requests.post(f"{API_URL}/items/{item_id}/prices/", json=price_payload)
        if response.status_code == 200:
            print(f"✅ Logged new price: {current_price} TL")
        else:
            print(f"❌ Failed to log price. API Status: {response.status_code}, Response: {response.json()}")

    except Exception as e:
        print(f"❌ Could not scrape price for {url}. Error: {e}")

if __name__ == "__main__":
    items_to_track = get_all_items_from_db()

    if items_to_track:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            print(f"\nStarting price update for {len(items_to_track)} items...")
            for i, item in enumerate(items_to_track, 1):
                print(f"--- Processing {i}/{len(items_to_track)} ---")
                scrape_and_update_price(page, item)
                time.sleep(random.uniform(3, 7)) # Be respectful and slow down

            browser.close()
            print("\nPrice update process finished.")