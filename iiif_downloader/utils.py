import os
import shutil
import time

import requests
from requests import RequestException

from .logger import get_logger

logger = get_logger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/json,"
        "text/html,"
        "application/xhtml+xml,"
        "application/xml;q=0.9,"
        "image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def get_json(url, headers=None, retries=3):
    """Fetches JSON from a URL with retry logic."""
    if headers is None:
        headers = DEFAULT_HEADERS

    logger.debug(f"Fetching JSON from {url}")
    
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            
            # If rate limited, wait longer
            if resp.status_code == 429:
                wait_time = (2 ** attempt) * 2
                logger.warning(f"Rate limited (429) on {url}, waiting {wait_time}s")
                time.sleep(wait_time)
                continue
                
            resp.raise_for_status()
            return resp.json()
        except RequestException as e:
            if attempt == retries - 1:
                logger.error(f"Failed to fetch JSON from {url}: {e}")
                
                response = getattr(e, "response", None)
                if response is not None:
                    status_code = getattr(response, "status_code", None)
                    if status_code is not None:
                        logger.error(f"HTTP Status: {status_code}")
                    response_text = getattr(response, "text", None)
                    if response_text:
                        logger.debug(f"Response preview: {response_text[:200]}")
                        print(f"Response Text (first 200 chars): {response_text[:200]}")
                raise
            
            logger.warning(f"Attempt {attempt + 1}/{retries} failed for {url}, retrying...")
            wait_time = (2 ** attempt)
            time.sleep(wait_time)
        except ValueError as e:
            # This happens if resp.json() fails
            logger.error(f"JSON parsing error from {url}: {e}")
            try:
                preview = resp.text[:200]
                logger.debug(f"Response preview: {preview}")
                print(f"Response preview (first 200 chars): {preview}")
            except:
                pass
            raise


def save_json(path, data):
    """Saves data to a local JSON file."""
    import json
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(path):
    """Loads a JSON file, returns None if not found."""
    import json
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def ensure_dir(path):
    """Ensures a directory exists."""
    if not path:
        return
    os.makedirs(path, exist_ok=True)


def clean_dir(path):
    """Safely removes a directory."""
    if os.path.exists(path):
        shutil.rmtree(path)
