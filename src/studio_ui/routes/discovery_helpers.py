"""Helper utilities for discovery route handlers.

These keep the request handlers small and focused so ruff's
complexity checks remain satisfied.
"""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import unquote

from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.jobs import job_manager
from universal_iiif_core.library_catalog import parse_manifest_catalog
from universal_iiif_core.logger import get_logger
from universal_iiif_core.logic.downloader import IIIFDownloader
from universal_iiif_core.resolvers.parsers import IIIFManifestParser
from universal_iiif_core.services.storage.vault_manager import VaultManager
from universal_iiif_core.utils import generate_job_id, get_json

logger = get_logger(__name__)


def analyze_manifest(manifest_url: str) -> dict[str, Any]:
    """Download and extract simple preview data from a manifest URL.

    Returns a dict with keys: label, description, pages.
    Raises exceptions on network / parsing errors so callers can handle them.
    """
    manifest_data = get_json(manifest_url)
    if not manifest_data:
        raise ValueError("Manifest vuoto o irraggiungibile")

    # Usa il parser centralizzato per metadati robusti
    parser = IIIFManifestParser()
    result = parser.parse_manifest(manifest_data, manifest_url=manifest_url)
    catalog = parse_manifest_catalog(
        manifest_data,
        manifest_url=manifest_url,
        doc_id=str(result.get("id") or ""),
        enrich_external_reference=True,
    )

    # Calcolo pagine manuale se il parser non lo espone direttamente
    # (IIIF v2 sequences o IIIF v3 items)
    canvases = []
    if "sequences" in manifest_data:
        seq = manifest_data["sequences"][0] if manifest_data["sequences"] else {}
        canvases = seq.get("canvases", [])
    elif "items" in manifest_data:
        canvases = manifest_data["items"]
    rendering = manifest_data.get("rendering") or []
    if isinstance(rendering, dict):
        rendering = [rendering]
    has_native_pdf = False
    for item in rendering:
        if not isinstance(item, dict):
            continue
        fmt = str(item.get("format") or "").lower()
        url = str(item.get("@id") or item.get("id") or "").lower()
        if fmt == "application/pdf" or url.endswith(".pdf"):
            has_native_pdf = True
            break

    return {
        "label": catalog.get("label") or result.get("title", "Senza Titolo"),
        "description": catalog.get("description") or result.get("description", ""),
        "pages": len(canvases),
        "thumbnail": result.get("thumbnail"),
        "has_native_pdf": has_native_pdf,
        "catalog_title": catalog.get("catalog_title") or result.get("title", "Senza Titolo"),
        "shelfmark": catalog.get("shelfmark") or "",
        "date_label": catalog.get("date_label") or "",
        "language_label": catalog.get("language_label") or "",
        "source_detail_url": catalog.get("source_detail_url") or "",
        "reference_text": catalog.get("reference_text") or "",
        "item_type": catalog.get("item_type") or "non classificato",
        "item_type_confidence": float(catalog.get("item_type_confidence") or 0.0),
        "item_type_reason": catalog.get("item_type_reason") or "",
        "metadata_json": catalog.get("metadata_json") or "{}",
    }


def start_downloader_thread(manifest_url: str, doc_id: str, library: str, target_pages: set[int] | None = None) -> str:
    """Start a background IIIF download and persist progress into the DB.

    The function returns a stable download_id (HASH) which can be used by the UI
    to poll the `download_jobs` table without encoding issues.
    """
    manifest_url = unquote(manifest_url)
    doc_id = unquote(doc_id)
    library = unquote(library)

    # Prevent duplicate concurrent jobs for the same manuscript/library pair.
    try:
        for active in VaultManager().get_active_downloads():
            if str(active.get("doc_id") or "") == doc_id and str(active.get("library") or "") == library:
                existing_job_id = str(active.get("job_id") or "").strip()
                if existing_job_id:
                    logger.info("Download already active for %s (%s): reusing job %s", doc_id, library, existing_job_id)
                    return existing_job_id
    except Exception:
        logger.debug("Failed to check active downloads before enqueue", exc_info=True)

    # 1. GENERA ID ROBUSTO + univoco per consentire retry multipli in parallelo.
    #    Manteniamo il prefisso hash per traceability e aggiungiamo un suffisso corto random.
    base_job_id = generate_job_id(library, manifest_url)
    job_id = f"{base_job_id}_{uuid.uuid4().hex[:8]}"

    # 2. Usa doc_id direttamente come nome cartella (senza abbellimenti)
    # Il doc_id dovrebbe già essere l'ID tecnico pulito dal resolver
    # (es. btv1b10033406t per Gallica, MSS_Urb.lat.1775 per Vaticana)

    logger.info(f"Starting Download: JobID={job_id} | DocID='{doc_id}'")

    job_manager.submit_job(
        _download_task,
        kwargs={
            "manifest_url": manifest_url,
            "doc_id": doc_id,
            "library": library,
            "db_job_id": job_id,  # Chiave per API/DB
            "folder_name": doc_id,  # Usa doc_id direttamente come nome cartella
            "target_pages": set(target_pages or set()),
        },
        job_type="download",
    )

    return job_id


def _download_task(progress_callback=None, should_cancel=None, **kwargs):
    """Worker function executed in thread."""
    manifest_url = str(kwargs.get("manifest_url") or "")
    doc_id = str(kwargs.get("doc_id") or "")
    library = str(kwargs.get("library") or "")
    db_job_id = str(kwargs.get("db_job_id") or "")
    folder_name = kwargs.get("folder_name")
    target_pages = kwargs.get("target_pages")

    # Thread-local DB manager for safety
    vault = VaultManager()

    # Register the job in DB only when no external job manager callback exists.
    if progress_callback is None:
        vault.create_download_job(db_job_id, doc_id, library, manifest_url)

    # Track last seen values for more informative error reporting
    last = {"current": 0, "total": 0}

    def db_progress_hook(current: int, total: int):
        """Update DB only when values change to reduce write load."""
        if current != last["current"] or total != last["total"]:
            last["current"] = current
            last["total"] = total

            # If no external callback is provided, persist progress directly.
            if progress_callback is None:
                vault.update_download_job(job_id=db_job_id, current=current, total=total, status="running")

        # Call the memory-based job manager callback if provided
        if progress_callback:
            progress_callback(current, total)

    try:
        # Explicitly use configured downloads dir
        cm = get_config_manager()
        downloads_dir = cm.get_downloads_dir()

        downloader = IIIFDownloader(
            manifest_url,
            output_dir=downloads_dir,
            library=library,
            output_folder_name=folder_name,
            progress_callback=db_progress_hook,
            job_id=db_job_id,
            show_progress=False,
        )

        # Pass DB hook and cancellation checker to the runtime `run` call
        downloader.run(should_cancel=should_cancel, target_pages=target_pages)

        # Mark completed only when no external callback tracks finalization.
        if progress_callback is None:
            vault.update_download_job(
                job_id=db_job_id,
                current=last["current"],
                total=last["total"],
                status="completed",
            )

        # Register manuscript in the main table
        existing = vault.get_manuscript(doc_id) or {}
        preferred_title = (
            str(existing.get("catalog_title") or "").strip()
            or str(existing.get("display_title") or "").strip()
            or str(downloader.label)
        )
        vault.upsert_manuscript(
            doc_id,
            library=library,
            title=downloader.label,
            local_path=str(downloader.doc_dir),
            display_title=preferred_title,
            catalog_title=preferred_title,
            has_native_pdf=1 if downloader.get_pdf_url() else 0,
            pdf_local_available=1 if any(downloader.pdf_dir.glob("*.pdf")) else 0,
        )

    except Exception as exc:  # pragma: no cover - runtime safety
        logger.error(f"Download failed for {doc_id}: {exc}", exc_info=True)
        if progress_callback is None:
            vault.update_download_job(
                job_id=db_job_id,
                current=last["current"],
                total=last["total"],
                status="error",
                error=str(exc),
            )
