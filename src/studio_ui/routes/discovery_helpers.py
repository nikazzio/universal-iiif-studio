"""Helper utilities for discovery route handlers.

These keep the request handlers small and focused so ruff's
complexity checks remain satisfied.
"""

import threading
from typing import Any

from universal_iiif_core.logger import get_logger
from universal_iiif_core.logic import IIIFDownloader
from universal_iiif_core.utils import get_json

logger = get_logger(__name__)


def analyze_manifest(manifest_url: str) -> dict[str, Any]:
    """Download and extract simple preview data from a manifest URL.

    Returns a dict with keys: label, description, pages.
    Raises exceptions on network / parsing errors so callers can handle them.
    """
    m = get_json(manifest_url)
    if not isinstance(m, dict):
        raise ValueError("Invalid manifest data")

    label = m.get("label", "Senza Titolo")
    if isinstance(label, list):
        label = label[0]
    if isinstance(label, dict):
        label = label.get("it", label.get("en", list(label.values())[0]))

    desc = m.get("description", "")
    if isinstance(desc, list):
        desc = desc[0]

    canvases = []
    sequences = m.get("sequences")
    if isinstance(sequences, list) and sequences:
        canvases = sequences[0].get("canvases", []) or []
    else:
        items = m.get("items")
        if isinstance(items, list):
            canvases = items

    return {
        "label": str(label),
        "description": str(desc),
        "pages": len(canvases),
    }


def start_downloader_thread(
    manifest_url: str,
    doc_id: str,
    library: str,
    progress_store: dict[str, Any],
    workers: int = 4,
) -> str:
    """Start background IIIF download and track progress in `progress_store`.

    Returns the generated `download_id` used by the handlers to poll progress.
    """
    download_id = f"{library}_{doc_id}"
    progress_store[download_id] = {"current": 0, "total": 0, "status": "initializing"}

    def progress_hook(curr: int, total: int) -> None:
        progress_store[download_id] = {"current": curr, "total": total, "status": "downloading"}

    def run_downloader() -> None:
        try:
            downloader = IIIFDownloader(
                manifest_url=manifest_url,
                output_name=doc_id,
                library=library,
                progress_callback=progress_hook,
                workers=int(workers),
            )
            downloader.run()
            progress_store[download_id]["status"] = "complete"
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.error("Download thread error: %s", exc)
            progress_store[download_id]["status"] = f"error: {str(exc)}"

    thread = threading.Thread(target=run_downloader, daemon=True)
    thread.start()
    return download_id
