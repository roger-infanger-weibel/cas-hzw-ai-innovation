"""
Base parking collector class for all city-specific collectors.
"""

import requests
import json
import os
import time
import glob
from datetime import datetime
from abc import ABC, abstractmethod


class BaseParkingCollector(ABC):
    """Abstract base class for parking data collectors."""

    def __init__(self, city_id, city_name, api_url, data_dir="data",
                 timeout=20, max_retries=3, retry_backoff=2):
        """
        Initialize the collector.

        Args:
            city_id: City identifier (e.g., 'luzern', 'basel')
            city_name: Display name of the city
            api_url: API endpoint URL
            data_dir: Base directory for data storage
            timeout: Per-request timeout in seconds
            max_retries: Number of attempts before giving up on a fetch
            retry_backoff: Base seconds for exponential backoff between retries
        """
        self.city_id = city_id
        self.city_name = city_name
        self.api_url = api_url
        self.data_dir = data_dir
        self.city_data_dir = os.path.join(data_dir, city_id)
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    def _request_with_retry(self):
        """
        Perform the HTTP GET with retries and exponential backoff.

        Returns:
            requests.Response: The successful response object.

        Raises:
            requests.RequestException: If all attempts fail.
        """
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(self.api_url, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                last_error = e
                print(f"[{datetime.now()}] {self.city_name}: Attempt {attempt}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff * (2 ** (attempt - 1)))
        raise last_error

    def fetch_raw_data(self):
        """
        Fetch raw data from the API, retrying on timeout/connection errors.

        Returns:
            dict: Raw API response as JSON

        Raises:
            requests.RequestException: If the API request fails after all retries
        """
        response = self._request_with_retry()
        return response.json()

    def _load_last_snapshot(self):
        """
        Load the most recently saved JSON snapshot for this city, if any.

        Used as a fallback so a single failed fetch doesn't drop the city
        from the current run entirely.

        Returns:
            dict or None: Previously normalized data, or None if unavailable.
        """
        pattern = os.path.join(self.city_data_dir, "*.json")
        files = sorted(glob.glob(pattern))
        if not files:
            return None

        try:
            with open(files[-1], "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"[{datetime.now()}] {self.city_name}: Could not read fallback snapshot {files[-1]}: {e}")
            return None
    
    @abstractmethod
    def normalize_data(self, raw_data):
        """
        Convert raw API data to unified format.
        
        Args:
            raw_data: Raw data from API
        
        Returns:
            dict: Normalized data in unified format:
            {
                "status": "success",
                "city": "city_id",
                "data": {
                    "parkings": {
                        "PARKING_ID": {
                            "id": "PARKING_ID",
                            "name": "Parking Name",
                            "free": 150,
                            "total": 200,
                            "status": "open",
                            "timestamp": "2026-01-06T07:30:00+01:00"
                        }
                    }
                },
                "timestamp": "2026-01-06T07:30:00+01:00"
            }
        """
        pass
    
    def save_data(self, data):
        """
        Save normalized data to JSON file and MariaDB.
        
        Args:
            data: Normalized parking data
            
        Returns:
            dict: Statistics of the save operation
        """
        if not data:
            return {'success': False, 'inserted': 0, 'duplicates': 0, 'failed': 0, 'error': 'No data'}
        
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        
        # 1. Save to JSON file (for GitHub history/Pages)
        try:
            os.makedirs(self.city_data_dir, exist_ok=True)
            timestamp_fn = now.strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(self.city_data_dir, f"{timestamp_fn}.json")
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[{now}] {self.city_name}: Warning - Failed to save JSON: {e}")

        # 2. Save to MariaDB
        try:
            from db_utils import get_connection, insert_measurement
            import mysql.connector
            from mysql.connector import errorcode
            
            conn = get_connection()
            cursor = conn.cursor()
            
            parkings = data.get("data", {}).get("parkings", {})
            fetch_ts = data.get("timestamp")
            if fetch_ts:
                try:
                    # Handle ISO format with potential timezone offsets
                    # MariaDB DATETIME expects YYYY-MM-DD HH:MM:SS
                    dt = datetime.fromisoformat(fetch_ts.replace('Z', '+00:00'))
                    fetch_ts = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    fetch_ts = now.strftime("%Y-%m-%d %H:%M:%S")
            else:
                fetch_ts = now.strftime("%Y-%m-%d %H:%M:%S")
            
            success_count = 0
            fail_count = 0
            duplicate_count = 0
            
            for pid, pdata in parkings.items():
                db_data = {
                    'day': date_str,
                    'fetch_ts': fetch_ts,
                    'city': self.city_id,
                    'id': pid,
                    'name': pdata.get('name', pid),
                    'free': pdata.get('free', 0),
                    'total': pdata.get('total', 0)
                }
                try:
                    insert_measurement(cursor, db_data)
                    success_count += 1
                except mysql.connector.Error as err:
                    if err.errno == errorcode.ER_DUP_ENTRY:
                        duplicate_count += 1
                    else:
                        fail_count += 1
                        print(f"[{now}] {self.city_name}: Failed to insert parking {pid}: {err}")
                except Exception as e:
                    fail_count += 1
                    print(f"[{now}] {self.city_name}: Failed to insert parking {pid}: {e}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"[{now}] {self.city_name}: Data saved (Inserted: {success_count}, Duplicates: {duplicate_count}, Failed: {fail_count})")
            
            return {
                'success': True,
                'inserted': success_count,
                'duplicates': duplicate_count,
                'failed': fail_count,
                'error': None
            }
            
        except Exception as e:
            print(f"[{now}] {self.city_name}: Error saving to MariaDB: {e}")
            return {
                'success': False, 
                'inserted': 0, 
                'duplicates': 0, 
                'failed': 0, 
                'error': str(e)
            }
    
    def collect(self):
        """
        Main collection method: fetch, normalize, and save data.

        If fetching/normalizing fails after all retries, falls back to the
        last successfully saved snapshot so a transient outage doesn't create
        a gap in the data (the current timestamp is used, since it reflects
        the last known occupancy at the time of this run).

        Returns:
            dict: Statistics of the collection result
        """
        normalized_data = None
        fetch_error = None

        try:
            print(f"[{datetime.now()}] {self.city_name}: Fetching data...")
            raw_data = self.fetch_raw_data()

            print(f"[{datetime.now()}] {self.city_name}: Normalizing data...")
            normalized_data = self.normalize_data(raw_data)
            if not normalized_data:
                raise ValueError("Normalization returned no data")

        except Exception as e:
            fetch_error = e
            print(f"[{datetime.now()}] {self.city_name}: Fetch failed after {self.max_retries} attempts ({e}). "
                  f"Falling back to last known occupancy...")

            fallback = self._load_last_snapshot()
            if fallback and fallback.get("data", {}).get("parkings"):
                normalized_data = fallback
                normalized_data["status"] = "fallback"
                normalized_data["timestamp"] = datetime.now().isoformat()
                print(f"[{datetime.now()}] {self.city_name}: Using last known occupancy from previous snapshot.")

        if not normalized_data:
            print(f"[{datetime.now()}] {self.city_name}: Collection failed, no fallback available: {fetch_error}")
            return {
                'success': False,
                'inserted': 0,
                'duplicates': 0,
                'failed': 0,
                'error': str(fetch_error) if fetch_error else 'No data'
            }

        print(f"[{datetime.now()}] {self.city_name}: Saving data...")
        stats = self.save_data(normalized_data)
        if fetch_error:
            stats['error'] = f"Used fallback data after fetch error: {fetch_error}"
        return stats
