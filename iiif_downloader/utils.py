import requests
import os
import shutil
import time

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1"
}

def get_json(url, headers=None, retries=3):
    """Fetches JSON from a URL with retry logic."""
    if headers is None:
        headers = DEFAULT_HEADERS
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if attempt == retries - 1:
                print(f"Error fetching JSON from {url}: {e}")
                if 'response' in locals():
                     print(f"HTTP Status: {response.status_code}")
                     # Print first 200 chars of response to see if it's HTML/Error page
                     print(f"Response Text: {response.text[:500]}")
                raise e
            time.sleep(1)

def ensure_dir(path):
    """Ensures a directory exists."""
    if not os.path.exists(path):
        os.makedirs(path)

def clean_dir(path):
    """Safely removes a directory."""
    if os.path.exists(path):
        shutil.rmtree(path)
