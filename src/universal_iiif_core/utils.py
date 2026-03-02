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

import requests
from requests import RequestException, Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .logger import get_logger

logger = get_logger(__name__)

# Headers mimetici (Firefox)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
}


def get_request_session() -> Session:
    """Restituisce una sessione requests configurata per resilienza e performance."""
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    # Configura una strategia di retry robusta a livello di socket
    retry_strategy = Retry(
        total=3,  # Numero massimo di tentativi totali
        backoff_factor=5,  # Attesa esponenziale (1s, 2s, 4s...)
        status_forcelist=[429, 500, 502, 503, 504],  # Retry su errori server o rate limit
        allowed_methods=["HEAD", "GET", "OPTIONS"],  # Metodi sicuri da riprovare
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get_json(url: str, headers: dict | None = None, retries: int = 3) -> Any | None:
    """Fetches JSON from a URL with robust retry logic and session reuse."""
    final_headers = DEFAULT_HEADERS.copy()
    if headers:
        final_headers.update(headers)

    # Usa una sessione per riutilizzare la connessione TCP (più veloce e meno sospetto)
    session = get_request_session()

    logger.debug("Fetching JSON from %s", url)

    for attempt in range(retries):
        try:
            # Timeout esplicito per evitare hang infiniti
            resp = session.get(url, headers=final_headers, timeout=20)

            # Gestione specifica Rate Limit (se il Retry automatico dell'adapter fallisce)
            if resp.status_code == 429:
                wait_time = (attempt + 1) * 10
                logger.warning(f"Rate limited (429) on {url}, waiting {wait_time}s")
                time.sleep(wait_time)
                continue

            resp.raise_for_status()

            # Gestione contenuti vuoti
            if not resp.content:
                logger.warning(f"Empty response from {url}")
                return None

            try:
                return resp.json()
            except ValueError:
                # Fallback: gestione Brotli manuale o encoding errati
                logger.debug("Direct JSON parse failed for %s, trying fallbacks...", url)
                return _handle_json_fallback(resp)

        except RequestException as e:
            # Se siamo all'ultimo tentativo, logghiamo e usciamo
            if attempt == retries - 1:
                _log_request_exception(url, e)
                return None

            # Altrimenti attendiamo un po' (backoff manuale sopra quello dell'adapter)
            wait = (2**attempt) * 0.5
            logger.debug(f"Attempt {attempt + 1} failed for {url}: {e}. Retrying in {wait}s...")
            time.sleep(wait)

    return None


def _handle_json_fallback(resp: requests.Response) -> Any | None:
    """Gestisce casi limite di decompressione o parsing JSON."""
    # 1. Prova Brotli manuale se presente header ma non gestito
    ce = resp.headers.get("content-encoding", "").lower()
    if "br" in ce:
        try:
            import brotli

            decoded = brotli.decompress(resp.content)
            return json.loads(decoded.decode("utf-8"))
        except ImportError:
            logger.debug("Brotli compression detected but 'brotli' package not installed.")
        except (json.JSONDecodeError, ValueError) as exc:
            logger.exception(
                "Brotli decompression failed for response from %s: %s",
                getattr(resp, "url", "unknown"),
                exc,
            )

    # 2. Prova a pulire il testo (a volte i server mandano BOM o caratteri sporchi)
    try:
        text = resp.text.strip()
        # Rimuovi BOM se presente
        if text.startswith("\ufeff"):
            text = text[1:]
        return json.loads(text)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"JSON fallback parsing failed: {e}")
        # Log anteprima per debug
        logger.debug(f"Response preview: {resp.text[:200]}")
        return None


def _log_request_exception(url: str, exc: RequestException) -> None:
    logger.error("Failed to fetch JSON from %s: %s", url, exc)
    response = getattr(exc, "response", None)
    if response is not None:
        status_code = getattr(response, "status_code", None)
        if status_code is not None:
            logger.error("HTTP Status: %s", status_code)


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
