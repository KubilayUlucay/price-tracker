# scraper/proxy_tester.py

import requests
from datetime import datetime
from pathlib import Path

# --- File Definitions ---
# Input file where you will paste proxy lists
PROXY_INPUT_FILE = Path(__file__).parent / "working_proxies_list.txt"
# Output file for detailed report of working proxies
WORKING_PROXIES_REPORT_FILE = Path(__file__).parent / "working_proxies_report.txt"
# Output file for a clean list of working proxies
WORKING_PROXIES_LIST_FILE = Path(__file__).parent / "working_proxies_list.txt"
# Log file to keep track of all proxies we've ever tested
TESTED_PROXIES_LOG_FILE = Path(__file__).parent / "tested_proxies.txt"

TEST_URL = "http://httpbin.org/ip"
SUCCESS_COUNT = 0
FAIL_COUNT = 0
SKIPPED_COUNT = 0

def load_proxies_from_file(filepath: Path) -> set:
    """Loads a set of proxies from a given file, one per line."""
    if not filepath.exists():
        return set()
    with open(filepath, 'r') as f:
        return {line.strip() for line in f if line.strip()}

# --- Main Script ---
if __name__ == "__main__":
    # 1. Load the proxies we've already tested in previous runs
    tested_proxies = load_proxies_from_file(TESTED_PROXIES_LOG_FILE)
    print(f"Loaded {len(tested_proxies)} previously tested proxies to avoid re-testing.")

    # 2. Load the new list of proxies to test
    proxies_to_test = load_proxies_from_file(PROXY_INPUT_FILE)
    if not proxies_to_test:
        print(f"Error: The input file '{PROXY_INPUT_FILE.name}' is empty or does not exist.")
        print("Please paste a list of proxies (one per line) into that file and run again.")
        exit()

    print(f"--- Starting test for {len(proxies_to_test)} proxies from {PROXY_INPUT_FILE.name} ---")

    # 3. Loop through and test each proxy
    for proxy in proxies_to_test:
        if proxy in tested_proxies:
            print(f"\n[*] Skipping already tested proxy: {proxy}")
            SKIPPED_COUNT += 1
            continue

        print(f"\n[*] Testing new proxy: {proxy}")
        
        proxies_dict = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}",
        }

        try:
            start_time = datetime.now()
            # Set a 10-second timeout. If it's slower, it's not useful.
            response = requests.get(TEST_URL, proxies=proxies_dict, timeout=10)
            end_time = datetime.now()
            
            if response.status_code == 200:
                time_taken = (end_time - start_time).total_seconds()
                report_line = f"{proxy} - SUCCESS in {time_taken:.2f} seconds. Site sees IP: {response.json().get('origin')}"
                print(f"✅ {report_line}")
                
                # Append to the detailed report
                with open(WORKING_PROXIES_REPORT_FILE, 'a') as f:
                    f.write(report_line + "\n")
                
                # Append to the simple list
                with open(WORKING_PROXIES_LIST_FILE, 'a') as f:
                    f.write(proxy + "\n")
                
                SUCCESS_COUNT += 1
            else:
                print(f"❌ FAILED with status code: {response.status_code}")
                FAIL_COUNT += 1

        except Exception as e:
            print(f"❌ FAILED with error: {e.__class__.__name__}")
            FAIL_COUNT += 1
        
        # Log that we've now tested this proxy, regardless of outcome
        with open(TESTED_PROXIES_LOG_FILE, 'a') as f:
            f.write(proxy + "\n")

    # --- FINAL REPORT ---
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