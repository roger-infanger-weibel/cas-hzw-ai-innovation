import requests
import time
import json
import os
import argparse
from datetime import datetime

API_URL = "https://info.pls-luzern.ch/TeqParkingWS/GetFreeParks"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def fetch_data():
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[{datetime.now()}] Error fetching data: {e}")
        return None

def save_data(data):
    if not data:
        return

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")

    # Create directory for today if it doesn't exist
    day_dir = os.path.join(DATA_DIR, date_str)
    os.makedirs(day_dir, exist_ok=True)

    filename = f"{time_str}.json"
    filepath = os.path.join(day_dir, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[{now}] Data saved to {filepath}")
    except IOError as e:
        print(f"[{now}] Error saving data: {e}")

def main():
    parser = argparse.ArgumentParser(description="Monitor parking data from pls-luzern.ch")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=900, help="Interval in seconds (default: 900 aka 15 mins)")
    args = parser.parse_args()

    print(f"Starting parking monitor. Saving to {DATA_DIR}")
    
    if args.once:
        data = fetch_data()
        save_data(data)
        return

    while True:
        data = fetch_data()
        save_data(data)
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
