# scraper/proxy_tester.py

import requests
from datetime import datetime
from pathlib import Path

# --- File Definitions ---
WORKING_PROXIES_REPORT_FILE = Path(__file__).parent / "working_proxies_report.txt"
WORKING_PROXIES_LIST_FILE = Path(__file__).parent / "working_proxies_list.txt"
TESTED_PROXIES_LOG_FILE = Path(__file__).parent / "tested_proxies.txt"

# --- NEW: URL for the Proxifly list ---
# This points to their list of all proxy types (http, https, socks4, socks5)
PROXIFLY_URL = "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt"

TEST_URL = "http://httpbin.org/ip"
SUCCESS_COUNT = 0
FAIL_COUNT = 0
SKIPPED_COUNT = 0

def load_tested_proxies(filepath: Path) -> set:
    """Loads a set of proxies we have already tested."""
    if not filepath.exists():
        return set()
    with open(filepath, 'r', encoding='utf-8') as f:
        return {line.strip() for line in f if line.strip()}

def fetch_proxifly_list(url: str) -> set:
    """Fetches the latest proxy list from the Proxifly GitHub URL."""
    print(f"Fetching latest proxy list from {url}...")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status() # Raise an exception for bad status codes (like 404)
        # Split the text content by lines and filter out any empty lines
        proxies = {line.strip() for line in response.text.splitlines() if line.strip()}
        print(f"Successfully fetched {len(proxies)} proxies from Proxifly.")
        return proxies
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED to fetch proxy list from URL. Error: {e}")
        return set()

if __name__ == "__main__":
    tested_proxies = load_tested_proxies(TESTED_PROXIES_LOG_FILE)
    print(f"Loaded {len(tested_proxies)} previously tested proxies to avoid re-testing.")

    proxies_to_test = fetch_proxifly_list(PROXIFLY_URL)
    if not proxies_to_test:
        print("Could not retrieve any proxies to test. Exiting.")
        exit()

    print(f"--- Starting test for {len(proxies_to_test)} proxies from Proxifly ---")

    new_proxies_to_test = [p for p in proxies_to_test if p not in tested_proxies]
    SKIPPED_COUNT = len(proxies_to_test) - len(new_proxies_to_test)
    if SKIPPED_COUNT > 0:
        print(f"Skipping {SKIPPED_COUNT} already tested proxies.")

    for proxy in new_proxies_to_test:
        print(f"\n[*] Testing new proxy: {proxy}")
        # Note: We assume http for the protocol, which works for most proxy types with the requests library.
        proxies_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"}

        try:
            start_time = datetime.now()
            response = requests.get(TEST_URL, proxies=proxies_dict, timeout=10)
            end_time = datetime.now()
            
            if response.status_code == 200:
                time_taken = (end_time - start_time).total_seconds()
                report_line = f"{proxy} - SUCCESS in {time_taken:.2f} seconds. Site sees IP: {response.json().get('origin')}"
                print(f"✅ {report_line}")
                
                with open(WORKING_PROXIES_REPORT_FILE, 'a', encoding='utf-8') as f:
                    f.write(report_line + "\n")
                with open(WORKING_PROXIES_LIST_FILE, 'a', encoding='utf-8') as f:
                    f.write(proxy + "\n")
                
                SUCCESS_COUNT += 1
            else:
                print(f"❌ FAILED with status code: {response.status_code}")
                FAIL_COUNT += 1

        except Exception as e:
            print(f"❌ FAILED with error: {e.__class__.__name__}")
            FAIL_COUNT += 1
        
        with open(TESTED_PROXIES_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(proxy + "\n")

    print("\n" + "="*30)
    print("--- TEST COMPLETE ---")
    print(f"New Proxies Tested:     {SUCCESS_COUNT + FAIL_COUNT}")
    print(f"Successful Connections: {SUCCESS_COUNT}")
    print(f"Failed Connections:     {FAIL_COUNT}")
    print(f"Skipped (already tested): {SKIPPED_COUNT}")
    if (SUCCESS_COUNT + FAIL_COUNT) > 0:
        success_rate = (SUCCESS_COUNT / (SUCCESS_COUNT + FAIL_COUNT)) * 100
        print(f"Success Rate on New Proxies: {success_rate:.1f}%")
    print("="*30)
    print(f"Working proxies have been saved to '{WORKING_PROXIES_LIST_FILE.name}'")