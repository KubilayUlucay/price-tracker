# scraper/dispatcher.py

import json
from pathlib import Path
import math

# --- CONFIGURATION ---
# Set how many parallel workers you want to run.
TOTAL_WORKERS = 6

# --- FILE DEFINITIONS ---
ALL_URLS_FILE = Path(__file__).parent / "all_urls.json"
MASTER_PROXY_LIST_FILE = Path(__file__).parent / "master_proxy_list.txt" # Your big list of 1000+ proxies

def run_dispatcher():
    print("--- Starting Dispatcher ---")

    # 1. Load master URL list
    if not ALL_URLS_FILE.exists():
        print(f"❌ ERROR: Master URL list '{ALL_URLS_FILE.name}' not found. Please run the old scraper once to generate it.")
        return
    with open(ALL_URLS_FILE, 'r') as f:
        all_urls = json.load(f)
    print(f"Loaded {len(all_urls)} total URLs.")

    # 2. Load master proxy list
    if not MASTER_PROXY_LIST_FILE.exists():
        print(f"❌ ERROR: Master proxy list '{MASTER_PROXY_LIST_FILE.name}' not found.")
        return
    with open(MASTER_PROXY_LIST_FILE, 'r') as f:
        all_proxies = [line.strip() for line in f if line.strip()]
    print(f"Loaded {len(all_proxies)} total proxies.")

    # 3. Calculate chunk sizes
    url_chunk_size = math.ceil(len(all_urls) / TOTAL_WORKERS)
    proxy_chunk_size = math.ceil(len(all_proxies) / TOTAL_WORKERS)

    # 4. Create and save the work files for each worker
    for i in range(TOTAL_WORKERS):
        print(f"\nProcessing files for Worker {i}...")
        
        # Slice the URL list for this worker
        start_url_index = i * url_chunk_size
        end_url_index = start_url_index + url_chunk_size
        worker_urls = all_urls[start_url_index:end_url_index]
        worker_url_file = Path(__file__).parent / f"urls_worker_{i}.json"
        with open(worker_url_file, 'w') as f:
            json.dump(worker_urls, f, indent=2)
        print(f" -> Saved {len(worker_urls)} URLs to {worker_url_file.name}")

        # Slice the proxy list for this worker
        start_proxy_index = i * proxy_chunk_size
        end_proxy_index = start_proxy_index + proxy_chunk_size
        worker_proxies = all_proxies[start_proxy_index:end_proxy_index]
        worker_proxy_file = Path(__file__).parent / f"proxies_worker_{i}.txt"
        with open(worker_proxy_file, 'w') as f:
            for proxy in worker_proxies:
                f.write(proxy + "\n")
        print(f" -> Saved {len(worker_proxies)} proxies to {worker_proxy_file.name}")

    print("\n--- Dispatcher finished. Work files created. ---")

if __name__ == "__main__":
    run_dispatcher()