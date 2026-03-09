"""Common utility helpers (HTTP, JSON, filesystem)."""

import hashlib
import json
import os
import re
import shutil
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .logger import get_logger

logger = get_logger(__name__)

# Headers mimetici (Firefox) - kept for backward compatibility
# New code should use HTTPClient which has these headers built-in
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
}


def get_json(url: str, headers: dict | None = None, retries: int = 3) -> Any | None:
    """
    Fetch JSON from a URL with retry logic (LEGACY).
    
    DEPRECATED: New code should use HTTPClient.get_json() instead.
    This function is kept for backward compatibility and creates a temporary
    HTTPClient instance for each call.
    
    Args:
        url: URL to fetch
        headers: Optional additional headers (merged with defaults)
        retries: Ignored (HTTPClient uses policy-based retries)
    
    Returns:
        Parsed JSON data or None on error
    """
    from .http_client import HTTPClient
    from .config_manager import cm
    
    # Create temporary HTTPClient with current config
    http_client = HTTPClient(network_policy=cm.data.get("settings", {}))
    
    try:
        # HTTPClient.get_json() handles all retry logic, backoff, rate limiting
        return http_client.get_json(url, library_name=None, timeout=20)
    except Exception as e:
        logger.debug(f"get_json failed for {url}: {e}")
        return None


def save_json(path, data):
    """Saves data to a local JSON file."""
    p = Path(path)
    ensure_dir(p.parent)
    try:
        # Atomic write: write to temp then rename
        temp_p = p.with_suffix(".tmp")
        with temp_p.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if p.exists():
            p.unlink()
        temp_p.rename(p)
    except OSError as e:
        logger.error(f"Failed to save JSON to {path}: {e}")


def load_json(path):
    """Loads a JSON file, returns None if not found."""
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
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Could not create directory {path}: {e}")


def clean_dir(path: str | os.PathLike):
    """Safely removes a directory."""
    p = Path(path)
    if p.exists():
        try:
            shutil.rmtree(p)
        except OSError as e:
            logger.error(f"Error cleaning directory {path}: {e}")


def cleanup_old_files(path: str | os.PathLike, *, older_than_days: int = 7) -> dict:
    """Delete files/dirs under `path` older than `older_than_days`."""
    stats = {"deleted": 0, "errors": 0, "skipped": 0}
    base_dir = Path(path)

    try:
        if not base_dir.exists() or not base_dir.is_dir():
            return stats
    except OSError:
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
        except OSError:
            stats["errors"] += 1

    return stats


def compute_text_diff_stats(old_text: str | None, new_text: str | None) -> dict[str, int]:
    """Return character-level additions/deletions between two versions."""
    if old_text is None:
        old_text = ""
    if new_text is None:
        new_text = ""
    matcher = SequenceMatcher(None, old_text, new_text)
    added = deleted = 0
    for tag, alo, ahi, blo, bhi in matcher.get_opcodes():
        if tag in ("insert", "replace"):
            added += max(0, bhi - blo)
        if tag in ("delete", "replace"):
            deleted += max(0, ahi - alo)
    return {"added": added, "deleted": deleted}


def generate_job_id(library: str, manifest_url: str) -> str:
    """Crea un ID sicuro e URL-friendly (alfanumerico).

    Es: Gallica_a1b2c3d4...
    """
    # Crea un hash SHA-256 dell'URL (più sicuro di MD5)
    url_hash = hashlib.sha256(manifest_url.encode("utf-8")).hexdigest()
    # Ritorna un ID pulito
    return f"{library}_{url_hash}"


def generate_folder_name(library: str, doc_id: str, title: str | None = None) -> str:
    """Genera un nome cartella pulito per l'utente. Output es: "GALLICA - bpt6k12345 - Les Miserables"."""
    # 1. Pulizia ID (rimuove slashes, due punti, ecc)
    clean_id = sanitize_filename(doc_id)
    # 2. Pulizia Titolo (opzionale, ma utile per l'utente)
    clean_title = ""
    if title:
        # Prendi solo i primi 30 caratteri del titolo per non fare percorsi infiniti
        clean_title = sanitize_filename(title)[:30].strip()
        if clean_title:
            clean_title = f" - {clean_title}"

    # 3. Formato Standard: "LIBRERIA - ID - Titolo(opz)"
    folder_name = f"{library.upper()} - {clean_id}{clean_title}"
    return folder_name


def sanitize_filename(name: str) -> str:
    """Rende una stringa sicura per il filesystem (Windows/Linux/Mac)."""
    # Rimuove caratteri vietati: / \ : * ? " < > |
    # Sostituisce con underscore o trattino
    s = re.sub(r'[\\/*?:"<>|]', "_", str(name))
    # Rimuove caratteri di controllo
    s = re.sub(r"[\x00-\x1f]", "", s)
    # Rimuove spazi multipli
    s = re.sub(r"\s+", " ", s).strip()
    return s
