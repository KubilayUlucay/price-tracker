# scraper/run_parallel_scrape.py

import subprocess
import os
import sys # Import the sys module to check the operating system

# This must match the TOTAL_WORKERS in dispatcher.py
TOTAL_WORKERS = 6

# --- NEW: Cross-platform path to Python executable ---
# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

if sys.platform == "win32":
    # If on Windows, the path is in the 'Scripts' folder
    python_executable = os.path.join(script_dir, "venv", "Scripts", "python.exe")
else:
    # If on Linux/macOS, the path is in the 'bin' folder
    python_executable = os.path.join(script_dir, "venv", "bin", "python")
    
script_path = os.path.join(script_dir, "koton_scraper.py")
# --- END OF NEW LOGIC ---


processes = []
for i in range(TOTAL_WORKERS):
    print(f"--- Launching Worker #{i} ---")
    command = [python_executable, script_path, str(i)]
    
    # Check if the python executable exists before trying to run it
    if not os.path.exists(python_executable):
        print(f"❌ ERROR: Could not find Python executable at: {python_executable}")
        print("Please ensure your virtual environment is set up correctly in the 'scraper' folder.")
        break
        
    process = subprocess.Popen(command)
    processes.append(process)

if processes:
    print(f"\n🚀 Launched {len(processes)} workers in the background.")
    print("Monitor their progress in this terminal.")

    for p in processes:
        p.wait()

    print("\n\n🎉 All workers have completed their tasks. 🎉")