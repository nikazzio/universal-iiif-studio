"""Helper utilities for discovery route handlers.

These keep the request handlers small and focused so ruff's
complexity checks remain satisfied.
"""

from typing import Any

from universal_iiif_core.jobs import job_manager
from universal_iiif_core.logger import get_logger
from universal_iiif_core.logic import IIIFDownloader
from universal_iiif_core.services.storage.vault_manager import VaultManager
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
    workers: int = 4,
) -> str:
    """Start a background IIIF download and persist progress into the DB.

    The function returns a stable download_id which can be used by the UI
    to poll the `download_jobs` table.
    """
    download_id = f"{library}_{doc_id}"

    def _download_task(progress_callback=None, should_cancel=None, **kwargs):
        # Thread-local DB manager for safety
        vault = VaultManager()
        # Register the job in DB
        try:
            vault.create_download_job(download_id, doc_id, library, manifest_url)
        except Exception:
            logger.debug("Failed to create download job record", exc_info=True)

        # Track last seen values for more informative error reporting
        last = {"current": 0, "total": 0}

        def db_progress_hook(current: int, total: int):
            last["current"] = current
            last["total"] = total
            try:
                vault.update_download_job(download_id, current=current, total=total, status="running")
            except Exception:
                logger.debug("Failed to update download job in DB", exc_info=True)

        try:
            # Explicitly use configured downloads dir
            from universal_iiif_core.config_manager import get_config_manager

            cm = get_config_manager()
            downloads_dir = cm.get_downloads_dir()

            downloader = IIIFDownloader(
                manifest_url=manifest_url,
                output_dir=downloads_dir,
                output_name=doc_id,
                library=library,
                workers=int(workers),
            )
            # Pass DB hook and cancellation checker to the runtime `run` call
            downloader.run(progress_callback=db_progress_hook, should_cancel=should_cancel)
            vault.update_download_job(
                download_id, current=last.get("current", 0), total=last.get("total", 0), status="completed"
            )
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.exception("Download thread error")
            try:
                vault.update_download_job(
                    download_id,
                    current=last.get("current", 0),
                    total=last.get("total", 0),
                    status="error",
                    error=str(exc),
                )
            except Exception:
                logger.debug("Failed to update error status in DB", exc_info=True)

        return None

    job_manager.submit_job(_download_task, job_type="download", kwargs={"db_job_id": download_id})
    return download_id
