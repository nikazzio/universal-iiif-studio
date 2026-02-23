"""Route handlers for Local Library page."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote

from fasthtml.common import Request

from studio_ui.common.toasts import build_toast
from studio_ui.components.layout import base_layout
from studio_ui.components.library import render_library_list, render_library_page
from studio_ui.routes.discovery_helpers import start_downloader_thread
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.logger import get_logger
from universal_iiif_core.services.ocr.storage import OCRStorage
from universal_iiif_core.services.storage.vault_manager import VaultManager

logger = get_logger(__name__)


def _normalized_docs(q: str = "", state: str = "") -> list[dict]:
    ql = (q or "").strip().lower()
    state_filter = (state or "").strip().lower()
    rows = VaultManager().get_all_manuscripts()
    docs: list[dict] = []
    for row in rows:
        current_state = str(row.get("asset_state") or row.get("status") or "saved").lower()
        title = str(row.get("display_title") or row.get("title") or row.get("id") or "")
        lib = str(row.get("library") or "Unknown")
        identifier = str(row.get("id") or "")
        if state_filter and current_state != state_filter:
            continue
        haystack = f"{title} {identifier} {lib}".lower()
        if ql and ql not in haystack:
            continue
        docs.append(
            {
                **row,
                "asset_state": current_state,
                "display_title": title,
                "item_type": row.get("item_type") or "altro",
                "downloaded_canvases": int(row.get("downloaded_canvases") or 0),
                "total_canvases": int(row.get("total_canvases") or 0),
            }
        )
    docs.sort(key=lambda d: (str(d.get("library") or ""), str(d.get("item_type") or "")))
    return docs


def _with_toast(fragment, message: str, tone: str = "info"):
    return [fragment, build_toast(message, tone=tone)]


def _render_list_fragment(view: str = "grid", q: str = "", state: str = ""):
    return render_library_list(_normalized_docs(q=q, state=state), view=view)


def library_page(request: Request, view: str = "grid", q: str = "", state: str = ""):
    """Render the Local Library page (full page or HTMX fragment)."""
    docs = _normalized_docs(q=q, state=state)
    content = render_library_page(docs, view=view or "grid", q=q or "", state=state or "")
    if request.headers.get("HX-Request") == "true":
        return content
    return base_layout("Libreria", content, active_page="library")


def library_delete(doc_id: str, library: str):
    """Delete one local manuscript and refresh library list."""
    doc_id = unquote(doc_id)
    library = unquote(library)
    if OCRStorage().delete_document(doc_id, library):
        return _with_toast(_render_list_fragment(), f"Documento '{doc_id}' eliminato.", tone="success")
    return _with_toast(_render_list_fragment(), f"Errore eliminando '{doc_id}'.", tone="danger")


def library_cleanup_partial(doc_id: str, library: str):
    """Remove partial scans/temp data while keeping manuscript metadata."""
    doc_id = unquote(doc_id)
    library = unquote(library)
    try:
        storage = OCRStorage()
        paths = storage.get_document_paths(doc_id, library)
        scans_dir = Path(paths["scans"])
        removed = 0
        if scans_dir.exists():
            for img in scans_dir.glob("pag_*.jpg"):
                img.unlink(missing_ok=True)
                removed += 1
        temp_dir = get_config_manager().get_temp_dir() / doc_id
        if temp_dir.exists() and temp_dir.is_dir():
            import shutil

            shutil.rmtree(temp_dir)
        VaultManager().upsert_manuscript(
            doc_id,
            status="saved",
            asset_state="saved",
            downloaded_canvases=0,
            missing_pages_json="[]",
            error_log=None,
        )
        return _with_toast(
            _render_list_fragment(),
            f"Pulizia parziale completata ({removed} pagine rimosse).",
            tone="success",
        )
    except Exception:
        logger.exception("Partial cleanup failed for %s/%s", library, doc_id)
        return _with_toast(_render_list_fragment(), "Errore durante cleanup parziale.", tone="danger")


def library_start_download(doc_id: str, library: str):
    """Queue a full download for an existing library entry."""
    doc_id = unquote(doc_id)
    library = unquote(library)
    ms = VaultManager().get_manuscript(doc_id) or {}
    manifest_url = str(ms.get("manifest_url") or "")
    if not manifest_url:
        return _with_toast(_render_list_fragment(), "Manifest URL non disponibile per questo documento.", tone="danger")
    try:
        start_downloader_thread(manifest_url, doc_id, library)
        return _with_toast(_render_list_fragment(), f"Download accodato per {doc_id}.", tone="info")
    except Exception:
        logger.exception("Start download failed for %s/%s", library, doc_id)
        return _with_toast(_render_list_fragment(), "Impossibile accodare il download.", tone="danger")


def library_retry_missing(doc_id: str, library: str):
    """Retry missing pages by re-running downloader with resume logic."""
    return library_start_download(doc_id, library)


def _parse_ranges(raw: str) -> set[int]:
    values: set[int] = set()
    text = (raw or "").strip()
    if not text:
        return values
    chunks = [c.strip() for c in text.split(",") if c.strip()]
    for chunk in chunks:
        if "-" in chunk:
            a, b = chunk.split("-", 1)
            start = int(a.strip())
            end = int(b.strip())
            if start > end:
                start, end = end, start
            for p in range(start, end + 1):
                values.add(p)
        else:
            values.add(int(chunk))
    return {v for v in values if v > 0}


def library_retry_range(doc_id: str, library: str, ranges: str = ""):
    """Retry a specific set/range of pages."""
    doc_id = unquote(doc_id)
    library = unquote(library)
    pages = _parse_ranges(ranges)
    if not pages:
        return _with_toast(_render_list_fragment(), "Range non valido. Usa formato: 1-10,15,18-20", tone="danger")

    ms = VaultManager().get_manuscript(doc_id) or {}
    manifest_url = str(ms.get("manifest_url") or "")
    if not manifest_url:
        return _with_toast(_render_list_fragment(), "Manifest URL non disponibile per retry range.", tone="danger")

    try:
        start_downloader_thread(manifest_url, doc_id, library, target_pages=pages)
        return _with_toast(
            _render_list_fragment(),
            f"Retry range accodato per {doc_id} ({len(pages)} pagine).",
            tone="info",
        )
    except Exception:
        logger.exception("Retry range failed for %s/%s", library, doc_id)
        return _with_toast(_render_list_fragment(), "Errore durante retry range.", tone="danger")


def library_set_type(doc_id: str, library: str, item_type: str):
    """Override automatic type classification for a manuscript."""
    doc_id = unquote(doc_id)
    _ = unquote(library)
    item_type = (item_type or "altro").strip().lower()
    allowed = {"manoscritto", "libro a stampa", "incunabolo", "periodico", "altro"}
    if item_type not in allowed:
        item_type = "altro"
    VaultManager().upsert_manuscript(doc_id, item_type=item_type, item_type_source="manual")
    return _with_toast(_render_list_fragment(), f"Tipologia aggiornata: {item_type}", tone="success")
