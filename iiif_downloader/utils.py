"""Common utility helpers (HTTP, JSON, filesystem)."""

import os
import shutil
import time
from pathlib import Path

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
        "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
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


def _sleep_backoff(attempt: int) -> None:
    time.sleep(2**attempt)


def _fetch_json_once(url: str, headers: dict) -> tuple[dict | None, requests.Response | None]:
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code == 429:
        return None, resp
    resp.raise_for_status()
    return resp.json(), resp


def _log_request_exception(url: str, exc: RequestException) -> None:
    logger.error("Failed to fetch JSON from %s: %s", url, exc)
    response = getattr(exc, "response", None)
    if response is not None:
        status_code = getattr(response, "status_code", None)
        if status_code is not None:
            logger.error("HTTP Status: %s", status_code)
        response_text = getattr(response, "text", None)
        if response_text:
            logger.debug("Response preview: %s", response_text[:200])


def _log_json_error(url: str, resp: requests.Response | None, exc: ValueError) -> None:
    logger.error("JSON parsing error from %s: %s", url, exc)
    if resp is None:
        return
    try:
        preview = resp.text[:200]
        logger.debug("Response preview: %s", preview)
    except Exception:  # pylint: disable=broad-exception-caught
        logger.debug("Failed to read response preview", exc_info=True)


def get_json(url, headers=None, retries=3):
    """Fetches JSON from a URL with retry logic."""
    if headers is None:
        headers = DEFAULT_HEADERS

    logger.debug("Fetching JSON from %s", url)

    for attempt in range(retries):
        try:
            data, resp = _fetch_json_once(url, headers)
            if data is not None:
                return data
            wait_time = (2**attempt) * 2
            logger.warning("Rate limited (429) on %s, waiting %ss", url, wait_time)
            time.sleep(wait_time)
        except RequestException as e:
            if attempt == retries - 1:
                _log_request_exception(url, e)
                raise
            logger.warning("Attempt %s/%s failed for %s, retrying...", attempt + 1, retries, url)
            _sleep_backoff(attempt)
        except ValueError as e:
            _log_json_error(url, resp if "resp" in locals() else None, e)
            raise

    return None


def save_json(path, data):
    """Saves data to a local JSON file."""
    import json

    p = Path(path)
    ensure_dir(p.parent)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(path):
    """Loads a JSON file, returns None if not found."""
    import json

    p = Path(path)
    if not p.exists():
        return None
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def ensure_dir(path: str | os.PathLike | None):
    """Ensures a directory exists."""
    if not path:
        return
    Path(path).mkdir(parents=True, exist_ok=True)


def clean_dir(path: str | os.PathLike):
    """Safely removes a directory."""
    p = Path(path)
    if p.exists():
        shutil.rmtree(p)


def cleanup_old_files(
    path: str | os.PathLike, *, older_than_days: int = 7
) -> dict:
    """Delete files/dirs under `path` older than `older_than_days`.

    Returns stats like {"deleted": X, "errors": Y, "skipped": Z}.
    """
    stats = {"deleted": 0, "errors": 0, "skipped": 0}
    base_dir = Path(path)

    try:
        if not base_dir.exists() or not base_dir.is_dir():
            return stats
    except Exception:  # pylint: disable=broad-exception-caught
        return stats

    cutoff = time.time() - (older_than_days * 24 * 60 * 60)

    for entry in base_dir.iterdir():
        try:
            if entry.stat().st_mtime >= cutoff:
                stats["skipped"] += 1
                continue

            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink(missing_ok=True)
            stats["deleted"] += 1
        except Exception:  # pylint: disable=broad-exception-caught
            stats["errors"] += 1

    return stats
