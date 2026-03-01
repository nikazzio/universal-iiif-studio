"""Studio route handlers moved out of the routes registration module.

This module contains the logic-heavy request handlers and helpers.
"""

import json
import math
import time
from pathlib import Path
from urllib.parse import quote, unquote

from fasthtml.common import Div, RedirectResponse, Request, Script

from studio_ui.common.htmx import history_refresh_script
from studio_ui.common.title_utils import resolve_preferred_title, truncate_title
from studio_ui.common.toasts import build_toast
from studio_ui.components.layout import base_layout
from studio_ui.components.studio.cropper import render_cropper_modal
from studio_ui.components.studio.export import (
    render_export_thumbnails_panel,
    render_pdf_inventory_panel,
    render_studio_export_tab,
)
from studio_ui.components.studio.history import history_tab_content
from studio_ui.components.studio.tabs import render_studio_tabs
from studio_ui.components.studio.transcription import transcription_tab_content
from studio_ui.config import get_api_key, get_snippets_dir
from studio_ui.ocr_state import OCR_JOBS_STATE, get_ocr_job_state, is_ocr_job_running
from studio_ui.pages.studio import studio_layout
from studio_ui.routes import export_handlers as export_monitor_handlers
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.jobs import job_manager
from universal_iiif_core.logger import get_logger
from universal_iiif_core.services.export import list_item_pdf_files
from universal_iiif_core.services.ocr.processor import OCRProcessor
from universal_iiif_core.services.ocr.storage import OCRStorage
from universal_iiif_core.services.storage.vault_manager import VaultManager
from universal_iiif_core.thumbnail_utils import ensure_thumbnail, guess_available_pages
from universal_iiif_core.utils import load_json

logger = get_logger(__name__)


def _with_toast(fragment, message: str, tone: str = "info"):
    """Append a global toast to a standard fragment response."""
    return [fragment, build_toast(message, tone=tone)]


def _toast_only(message: str, tone: str = "info"):
    """Return a noop target payload plus a global toast for HTMX requests."""
    return _with_toast(Div("", cls="hidden"), message, tone=tone)


def _load_manifest_payload(manifest_path: Path, page: int) -> tuple[dict, str | None]:
    """Load manifest JSON and resolve the initial canvas for a target page."""
    with manifest_path.open(encoding="utf-8") as f:
        manifest_json = json.load(f)
        if "sequences" in manifest_json:
            items = manifest_json["sequences"][0].get("canvases", [])
        else:
            items = manifest_json.get("items", [])

        target_idx = int(page) - 1
        initial_canvas = None
        if 0 <= target_idx < len(items):
            initial_canvas = items[target_idx].get("@id") or items[target_idx].get("id")
    return manifest_json, initial_canvas


def _studio_panel_refresh_script(doc_id: str, library: str, page_idx: int) -> Script:
    """Trigger a targeted refresh of the right Studio panel."""
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    hx_url = f"/studio/partial/tabs?doc_id={encoded_doc}&library={encoded_lib}&page={page_idx}"
    return Script(
        "(function(){"
        "setTimeout(function(){"
        "try{ htmx.ajax('GET', '" + hx_url + "', {target:'#studio-right-panel', swap:'innerHTML'}); }"
        "catch(e){ console.error('refresh-err', e); }"
        "}, 50);"
        "})();"
    )


def _normalized_studio_context(doc_id: str, library: str) -> tuple[str, str]:
    """Normalize doc and library query params from URL-encoded values."""
    return unquote(doc_id) if doc_id else "", unquote(library) if library else ""


def _library_redirect() -> RedirectResponse:
    """Redirect to Library when Studio is requested without document context."""
    return RedirectResponse(url="/library", status_code=303)


def _resolve_studio_title(doc_id: str, meta: dict, ms_row: dict) -> tuple[str, str]:
    """Return `(full_title, truncated_title)` for Studio header/info usage."""
    fallback_title = str(meta.get("title") or meta.get("label") or doc_id).strip()
    full_title = resolve_preferred_title(ms_row, fallback_doc_id=doc_id).strip()
    if not full_title or full_title == doc_id:
        full_title = fallback_title or doc_id
    return full_title, truncate_title(full_title, max_len=70, suffix="[...]")


def _to_downloads_url(path: Path) -> str:
    downloads_dir = get_config_manager().get_downloads_dir().resolve()
    try:
        rel = path.resolve().relative_to(downloads_dir)
    except Exception:
        return ""
    encoded = "/".join(quote(part, safe="") for part in rel.parts)
    return f"/downloads/{encoded}"


def _export_tab_defaults() -> dict[str, str | bool | int]:
    cm = get_config_manager()
    cover = cm.get_setting("pdf.cover", {})
    export_cfg = cm.get_setting("pdf.export", {})
    if not isinstance(cover, dict):
        cover = {}
    if not isinstance(export_cfg, dict):
        export_cfg = {}

    return {
        "curator": str(cover.get("curator") or ""),
        "description": str(cover.get("description") or ""),
        "logo_path": str(cover.get("logo_path") or ""),
        "format": str(export_cfg.get("default_format") or "pdf_images"),
        "compression": str(export_cfg.get("default_compression") or "Standard"),
        "include_cover": bool(export_cfg.get("include_cover", True)),
        "include_colophon": bool(export_cfg.get("include_colophon", True)),
        "description_rows": int(export_cfg.get("description_rows", 3) or 3),
    }


def _thumb_page_size(raw_page_size: int | None = None, *, doc_id: str = "") -> int:
    cm = get_config_manager()
    default_size = int(cm.get_setting("thumbnails.page_size", 48) or 48)
    candidate = default_size
    if raw_page_size not in {None, 0}:
        candidate = int(raw_page_size)
    elif doc_id:
        try:
            saved = VaultManager().get_manuscript_ui_pref(doc_id, "studio_export_thumb_page_size", default_size)
            candidate = int(saved or default_size)
        except Exception:
            candidate = default_size
    return max(1, min(candidate, 120))


def _is_export_job_active(job: dict) -> bool:
    return str(job.get("status") or "").lower() in {"queued", "running"}


def _thumb_page_size_options() -> list[int]:
    cm = get_config_manager()
    raw_options = cm.get_setting("thumbnails.page_size_options", [24, 48, 72, 96])
    options: list[int] = []
    if isinstance(raw_options, list):
        for raw in raw_options:
            try:
                value = int(raw)
            except (TypeError, ValueError):
                continue
            if 1 <= value <= 120 and value not in options:
                options.append(value)
    default_size = _thumb_page_size()
    if default_size not in options:
        options.append(default_size)
    return sorted(options)


def _build_export_thumbnail_slice(
    doc_id: str,
    library: str,
    *,
    thumb_page: int = 1,
    page_size: int | None = None,
) -> dict[str, object]:
    storage = OCRStorage()
    paths = storage.get_document_paths(doc_id, library)
    scans_dir = Path(paths["scans"])
    thumbnails_dir = Path(paths["thumbnails"])
    cm = get_config_manager()
    max_px = int(cm.get_setting("thumbnails.max_long_edge_px", 320) or 320)
    quality = int(cm.get_setting("thumbnails.jpeg_quality", 70) or 70)
    safe_page_size = _thumb_page_size(page_size, doc_id=doc_id)
    if page_size not in {None, 0}:
        try:
            VaultManager().set_manuscript_ui_pref(doc_id, "studio_export_thumb_page_size", safe_page_size)
        except Exception:
            logger.debug("Unable to persist thumbnail page size preference for %s", doc_id, exc_info=True)
    available_pages = guess_available_pages(scans_dir)
    total_pages = len(available_pages)

    if total_pages <= 0:
        return {
            "items": [],
            "available_pages": [],
            "thumb_page": 1,
            "thumb_page_count": 1,
            "total_pages": 0,
            "page_size": safe_page_size,
        }

    thumb_page_count = max(1, math.ceil(total_pages / safe_page_size))
    safe_thumb_page = max(1, min(int(thumb_page or 1), thumb_page_count))
    start = (safe_thumb_page - 1) * safe_page_size
    stop = start + safe_page_size
    page_slice = available_pages[start:stop]

    items: list[dict] = []
    for page_num in page_slice:
        thumb_path = ensure_thumbnail(
            scans_dir=scans_dir,
            thumbnails_dir=thumbnails_dir,
            page_num_1_based=page_num,
            max_long_edge_px=max_px,
            jpeg_quality=quality,
        )
        thumb_url = _to_downloads_url(thumb_path) if thumb_path else ""
        items.append({"page": page_num, "thumb_url": thumb_url})
    return {
        "items": items,
        "available_pages": available_pages,
        "thumb_page": safe_thumb_page,
        "thumb_page_count": thumb_page_count,
        "total_pages": total_pages,
        "page_size": safe_page_size,
    }


def _build_studio_export_fragment(
    doc_id: str,
    library: str,
    *,
    thumb_page: int = 1,
    page_size: int | None = None,
    selected_pages_raw: str = "",
):
    thumb_state = _build_export_thumbnail_slice(doc_id, library, thumb_page=thumb_page, page_size=page_size)
    pdf_files = list_item_pdf_files(doc_id, library)
    for row in pdf_files:
        row["download_url"] = _to_downloads_url(Path(str(row.get("path") or "")))
    jobs = export_monitor_handlers.list_jobs_for_item(doc_id, library, limit=50)
    has_active_jobs = any(_is_export_job_active(job) for job in jobs)
    return render_studio_export_tab(
        doc_id=doc_id,
        library=library,
        thumbnails=list(thumb_state.get("items") or []),
        thumb_page=int(thumb_state.get("thumb_page") or 1),
        thumb_page_count=int(thumb_state.get("thumb_page_count") or 1),
        thumb_total_pages=int(thumb_state.get("total_pages") or 0),
        thumb_page_size=int(thumb_state.get("page_size") or _thumb_page_size(doc_id=doc_id)),
        thumb_page_size_options=_thumb_page_size_options(),
        available_pages=list(thumb_state.get("available_pages") or []),
        selected_pages_raw=(selected_pages_raw or "").strip(),
        pdf_files=pdf_files,
        jobs=jobs,
        has_active_jobs=has_active_jobs,
        export_defaults=_export_tab_defaults(),
    )


def build_studio_tab_content(
    doc_id: str,
    library: str,
    page_idx: int,
    *,
    is_ocr_loading: bool = False,
    ocr_error: str | None = None,
    history_message: str | None = None,
):
    """Build Studio Tab Content."""
    storage = OCRStorage()
    meta = storage.load_metadata(doc_id, library) or {}
    ms_row = VaultManager().get_manuscript(doc_id) or {}
    full_title, _truncated_title = _resolve_studio_title(doc_id, meta, ms_row)
    meta = {**meta, "full_display_title": full_title}
    paths = storage.get_document_paths(doc_id, library)
    scans_dir = Path(paths["scans"])
    total_pages = len(list(scans_dir.glob("pag_*.jpg"))) if scans_dir.exists() else 0
    manifest_json = load_json(paths["manifest"]) or {}
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    export_url = f"/studio/partial/export?doc_id={encoded_doc}&library={encoded_lib}&page={page_idx}"
    return render_studio_tabs(
        doc_id,
        library,
        page_idx,
        meta,
        total_pages,
        manifest_json=manifest_json,
        is_ocr_loading=is_ocr_loading,
        ocr_error=ocr_error,
        history_message=history_message,
        export_fragment=None,
        export_url=export_url,
    )


def studio_page(request: Request, doc_id: str = "", library: str = "", page: int = 1):
    """Render Main Studio Layout."""
    doc_id, library = _normalized_studio_context(doc_id, library)
    is_hx = request.headers.get("HX-Request") == "true"

    if not doc_id or not library:
        return _library_redirect()

    try:
        storage = OCRStorage()
        paths = storage.get_document_paths(doc_id, library)
        meta = storage.load_metadata(doc_id, library) or {}
        ms_row = VaultManager().get_manuscript(doc_id) or {}
        full_title, title = _resolve_studio_title(doc_id, meta, ms_row)
        meta = {**meta, "full_display_title": full_title}

        scans_dir = Path(paths["scans"])
        total_pages = len(list(scans_dir.glob("pag_*.jpg"))) if scans_dir.exists() else 0

        # Base URLs
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        lib_q = quote(library, safe="")
        doc_q = quote(doc_id, safe="")
        manifest_url = f"{base_url}/iiif/manifest/{lib_q}/{doc_q}"

        manifest_path = Path(paths["manifest"])

        if not manifest_path.exists():
            message = "Manifesto non trovato."
            panel = Div(message, cls="p-10")
            if is_hx:
                return _with_toast(panel, message, tone="danger")
            return panel

        manifest_json, initial_canvas = _load_manifest_payload(manifest_path, page)

        content = studio_layout(
            title,
            library,
            doc_id,
            page,
            manifest_url,
            initial_canvas,
            manifest_json,
            total_pages,
            meta,
            export_url=f"/studio/partial/export?doc_id={doc_q}&library={lib_q}&page={page}",
            asset_status=str(ms_row.get("asset_state") or ms_row.get("status") or "unknown"),
            has_native_pdf=bool(ms_row.get("has_native_pdf")) if ms_row.get("has_native_pdf") is not None else None,
            pdf_local_available=bool(ms_row.get("pdf_local_available")),
        )
        if is_hx:
            return content
        return base_layout(f"Studio - {title}", content, active_page="library")

    except Exception as e:
        logger.exception("Studio Error")
        message = "Errore caricamento Studio."
        if is_hx:
            return _with_toast(Div(message, cls="p-10"), f"{message} {e}", tone="danger")
        return base_layout("Errore", Div(f"Errore caricamento: {e}", cls="p-10"))


def get_studio_tabs(doc_id: str, library: str, page: int):
    """Get Studio Tabs Content."""
    doc_id, library = unquote(doc_id), unquote(library)
    page_idx = int(page)
    is_loading = is_ocr_job_running(doc_id, page_idx)
    return build_studio_tab_content(
        doc_id,
        library,
        page_idx,
        is_ocr_loading=is_loading,
    )


def get_history_tab(doc_id: str, library: str, page: int, info_message: str | None = None):
    """Get History Tab Content."""
    doc_id, library = unquote(doc_id), unquote(library)
    page_idx = int(page)
    return Div(
        *history_tab_content(doc_id, page_idx, library, info_message=info_message),
        cls="p-4",
    )


def get_export_tab(
    doc_id: str,
    library: str,
    page: int,
    thumb_page: int = 1,
    page_size: int = 0,
    selected_pages: str = "",
):
    """Get Studio Export tab content."""
    _ = int(page)
    doc_id, library = unquote(doc_id), unquote(library)
    return _build_studio_export_fragment(
        doc_id,
        library,
        thumb_page=int(thumb_page or 1),
        page_size=int(page_size or 0),
        selected_pages_raw=selected_pages,
    )


def get_studio_export_jobs(doc_id: str, library: str):
    """Return per-item export jobs panel for polling."""
    doc_id, library = unquote(doc_id), unquote(library)
    return export_monitor_handlers.jobs_fragment_for_item(doc_id, library, panel_id="studio-export-jobs")


def get_studio_export_pdf_list(doc_id: str, library: str):
    """Return per-item PDF inventory panel for polling."""
    doc_id, library = unquote(doc_id), unquote(library)
    pdf_files = list_item_pdf_files(doc_id, library)
    for row in pdf_files:
        row["download_url"] = _to_downloads_url(Path(str(row.get("path") or "")))
    jobs = export_monitor_handlers.list_jobs_for_item(doc_id, library, limit=50)
    has_active_jobs = any(_is_export_job_active(job) for job in jobs)
    return render_pdf_inventory_panel(
        pdf_files,
        doc_id=doc_id,
        library=library,
        polling=has_active_jobs,
    )


def get_studio_export_thumbs(
    doc_id: str,
    library: str,
    thumb_page: int = 1,
    page_size: int = 0,
):
    """Return one thumbnails page slice for Studio Export tab."""
    doc_id, library = unquote(doc_id), unquote(library)
    thumb_state = _build_export_thumbnail_slice(
        doc_id,
        library,
        thumb_page=int(thumb_page or 1),
        page_size=int(page_size or 0),
    )
    return render_export_thumbnails_panel(
        doc_id=doc_id,
        library=library,
        thumbnails=list(thumb_state.get("items") or []),
        thumb_page=int(thumb_state.get("thumb_page") or 1),
        thumb_page_count=int(thumb_state.get("thumb_page_count") or 1),
        total_pages=int(thumb_state.get("total_pages") or 0),
        page_size=int(thumb_state.get("page_size") or _thumb_page_size(doc_id=doc_id)),
        page_size_options=_thumb_page_size_options(),
    )


def _is_truthy_flag(raw: str | None) -> bool:
    value = str(raw or "").strip().lower()
    return value in {"1", "true", "on", "yes"}


def start_studio_export(
    doc_id: str,
    library: str,
    selection_mode: str = "all",
    selected_pages: str = "",
    thumb_page: int = 1,
    page_size: int = 0,
    export_format: str = "pdf_images",
    compression: str = "Standard",
    include_cover: str = "",
    include_colophon: str = "",
    cover_curator: str = "",
    cover_description: str = "",
    cover_logo_path: str = "",
):
    """Start one export job from Studio for the current item."""
    doc_id, library = unquote(doc_id), unquote(library)
    include_cover_bool = _is_truthy_flag(include_cover)
    include_colophon_bool = _is_truthy_flag(include_colophon)
    if include_cover == "":
        include_cover_bool = True
    if include_colophon == "":
        include_colophon_bool = True

    try:
        export_monitor_handlers.start_export_job(
            items=[{"doc_id": doc_id, "library": library}],
            export_format=export_format,
            selection_mode=selection_mode,
            selected_pages_raw=selected_pages,
            destination="local_filesystem",
            compression=compression,
            include_cover=include_cover_bool,
            include_colophon=include_colophon_bool,
            cover_curator=cover_curator or None,
            cover_description=cover_description or None,
            cover_logo_path=cover_logo_path or None,
            capability_flags={"source": "studio-tab"},
        )
    except Exception as exc:
        return _with_toast(
            _build_studio_export_fragment(
                doc_id,
                library,
                thumb_page=int(thumb_page or 1),
                page_size=int(page_size or 0),
                selected_pages_raw=selected_pages,
            ),
            f"Errore avvio export: {exc}",
            tone="danger",
        )

    return _with_toast(
        _build_studio_export_fragment(
            doc_id,
            library,
            thumb_page=int(thumb_page or 1),
            page_size=int(page_size or 0),
            selected_pages_raw=selected_pages,
        ),
        "Export PDF avviato per l'item corrente.",
        tone="success",
    )


def run_ocr_async(doc_id: str, library: str, page: int, engine: str, model: str | None = None):
    """Run OCR asynchronously on a document page."""
    logger.info(
        "🔥 [API] run_ocr_async RECEIVED: doc=%s lib=%s pag=%s eng=%s mod=%s", doc_id, library, page, engine, model
    )
    doc_id, library = unquote(doc_id), unquote(library)
    logger.debug("🔓 [API] Unquoted: doc=%s lib=%s", doc_id, library)
    page_idx = int(page)
    OCR_JOBS_STATE[(doc_id, page_idx)] = {
        "status": "running",
        "timestamp": time.time(),
    }

    def _ocr_worker():
        try:
            storage = OCRStorage()
            paths = storage.get_document_paths(doc_id, library)
            image_path = Path(paths["scans"]) / f"pag_{page_idx - 1:04d}.jpg"

            logger.info("🧵 OCR Worker started for %s [Page %s] using %s", doc_id, page_idx, engine)

            from PIL import Image

            if not image_path.exists():
                logger.error("❌ Image not found for OCR: %s", image_path)
                OCR_JOBS_STATE[(doc_id, page_idx)] = {
                    "status": "error",
                    "message": f"Immagine non trovata: {image_path.name}",
                    "timestamp": time.time(),
                }
                return

            img = Image.open(str(image_path))
            logger.debug("📸 Image loaded successfully: %s (%s)", image_path, img.size)

            # Instantiate processor with all keys
            processor = OCRProcessor(
                openai_api_key=get_api_key("openai"),
                anthropic_api_key=get_api_key("anthropic"),
                google_api_key=get_api_key("google_vision"),
                hf_token=get_api_key("huggingface"),
            )

            logger.debug("🚀 Dispatching OCR request to processor...")

            # Use unified entry point
            res = processor.process_page(img, engine=engine, model=model)

            if res.get("error"):
                logger.error("❌ OCR Error for %s p%s: %s", doc_id, page_idx, res["error"])
                OCR_JOBS_STATE[(doc_id, page_idx)] = {
                    "status": "error",
                    "message": str(res["error"]),
                    "timestamp": time.time(),
                }
            else:
                storage.save_transcription(doc_id, page_idx, res, library)
                logger.info("✅ Async OCR success & auto-saved: %s p%s", doc_id, page_idx)
                OCR_JOBS_STATE[(doc_id, page_idx)] = {
                    "status": "completed",
                    "message": f"OCR completato e salvato (pag. {page_idx}).",
                    "timestamp": time.time(),
                }

        except Exception as e:
            err_msg = str(e)
            logger.exception("💥 Critical Failure in Async OCR worker for %s p%s", doc_id, page_idx)
            OCR_JOBS_STATE[(doc_id, page_idx)] = {
                "status": "error",
                "message": f"Critical Error: {err_msg}",
                "timestamp": time.time(),
            }

    def _ocr_task(progress_callback=None):
        _ocr_worker()
        return None

    job_manager.submit_job(_ocr_task, job_type="ocr")

    # Return the tab in loading state
    return transcription_tab_content(doc_id, library, page_idx, is_loading=True)


def check_ocr_status(doc_id: str, library: str, page: int):
    """Check OCR job status for a document page."""
    doc_id, library = unquote(doc_id), unquote(library)
    page_idx = int(page)
    logger.debug("🔎 Checking OCR poll status for %s doc=%s lib=%s", page_idx, doc_id, library)

    job_state = get_ocr_job_state(doc_id, page_idx)
    error_msg = None
    toast = None
    if job_state and job_state.get("status") == "error":
        logger.warning("📍 Polling detected error for %s p%s: %s", doc_id, page_idx, job_state["message"])
        error_msg = job_state.get("message")
        toast = build_toast(f"OCR fallito (pag. {page_idx}): {error_msg}", tone="danger")

    is_loading = is_ocr_job_running(doc_id, page_idx)
    if is_loading:
        logger.debug("⌛ OCR still processing for %s p%s; continuing spinner", doc_id, page_idx)
    else:
        logger.info("📡 Polling resolved or idle for %s p%s; refreshing panel", doc_id, page_idx)
        if job_state and job_state.get("status") == "completed":
            completion_message = job_state.get("message") or f"OCR completato (pag. {page_idx})."
            toast = build_toast(completion_message, tone="success")

    if job_state and not is_loading and job_state.get("status") in {"completed", "error"}:
        OCR_JOBS_STATE.pop((doc_id, page_idx), None)

    panel = Div(
        build_studio_tab_content(
            doc_id,
            library,
            page_idx,
            is_ocr_loading=is_loading,
            ocr_error=error_msg,
            history_message=error_msg,
        ),
        id="studio-right-panel",
        cls="flex-1 overflow-hidden h-full",
    )
    return [panel, toast] if toast else panel


def restore_transcription(doc_id: str, library: str, page: int, timestamp: str):
    """Restore a previous transcription version from history."""
    doc_id, library = unquote(doc_id), unquote(library)
    page_idx = int(page)
    storage = OCRStorage()
    history_items = storage.load_history(doc_id, page_idx, library)
    entry = next((e for e in history_items if e.get("timestamp") == timestamp), None)
    message = "Versione non trovata."

    if entry:
        restored_entry = {
            "full_text": entry.get("full_text", ""),
            "rich_text": entry.get("rich_text"),
            "lines": entry.get("lines"),
            "engine": "history",
            "status": "restored",
            "average_confidence": entry.get("average_confidence", 0.0),
            "is_manual": True,
            "restored_from": timestamp,
        }
        storage.save_transcription(doc_id, page_idx, restored_entry, library)
        logger.info("🔄 Restored transcription for %s p%s from %s", doc_id, page_idx, timestamp)
        message = f"Versione del {timestamp} ripristinata."

    return [
        Div(
            build_studio_tab_content(
                doc_id,
                library,
                page_idx,
                history_message=message,
            ),
            id="studio-right-panel",
            cls="flex-1 overflow-hidden h-full",
        ),
        build_toast(message, tone="success" if entry else "danger"),
        history_refresh_script(doc_id, library, page_idx, info_message=message),
    ]


def get_cropper(doc_id: str, library: str, page: int):
    """Render Cropper Modal Content."""
    doc_id, library = unquote(doc_id), unquote(library)
    lib_q, doc_q = quote(library, safe=""), quote(doc_id, safe="")
    img_url = f"/iiif/image/{lib_q}/{doc_q}/{page}/full/max/0/default.jpg"
    return render_cropper_modal(doc_id, library, int(page), img_url)


def save_snippet_api(doc_id: str, library: str, page: int, crop_data: str, transcription: str = ""):
    """Save a cropped snippet from the cropper tool."""
    doc_id, library = unquote(doc_id), unquote(library)
    try:
        data = json.loads(crop_data)
        storage = OCRStorage()
        vault = storage.vault
        paths = storage.get_document_paths(doc_id, library)
        image_path = Path(paths["scans"]) / f"pag_{int(page) - 1:04d}.jpg"

        coords = (data["x"], data["y"], data["x"] + data["width"], data["y"] + data["height"])
        crop_bytes = vault.extract_image_snippet(str(image_path), coords)

        if not crop_bytes:
            return build_toast("Impossibile creare il ritaglio richiesto.", tone="danger")

        filename = f"{doc_id}_p{int(page):04d}_{int(time.time())}.png"
        snippet_path = get_snippets_dir() / filename

        with snippet_path.open("wb") as f:
            f.write(crop_bytes)

        vault.save_snippet(
            doc_id, int(page), str(snippet_path), category="Manual", transcription=transcription, coords=data
        )

        return [
            Script(
                "document.getElementById('cropper-modal-container').innerHTML = ''; "
                "htmx.trigger('#tab-snippets', 'click');"
            ),
            build_toast("Snippet salvato correttamente.", tone="success"),
        ]

    except Exception as e:
        logger.exception("Snippet Save Error")
        return build_toast(f"Errore salvataggio snippet: {e}", tone="danger")


def save_transcription(doc_id: str, library: str, page: int, text: str):
    """Save manual transcription edits from the Studio."""
    try:
        doc_id, library = unquote(doc_id), unquote(library)
        storage = OCRStorage()
        page_idx = int(page)
        existing = storage.load_transcription(doc_id, page_idx, library)
        normalized_existing = (existing.get("full_text") if existing else "") or ""
        normalized_new = text or ""

        if normalized_existing == normalized_new:
            return [
                Div("", cls="hidden"),
                build_toast("Nessuna modifica rilevata; il testo è identico all'ultima versione.", tone="info"),
                _studio_panel_refresh_script(doc_id, library, page_idx),
            ]

        # Save the transcription
        storage.save_transcription(
            doc_id,
            page_idx,
            {"full_text": text, "is_manual": True},
            library,
        )

        return [
            Div("", cls="hidden"),
            build_toast("Modifiche salvate con successo nello storico.", tone="success"),
            _studio_panel_refresh_script(doc_id, library, page_idx),
        ]
    except Exception as e:
        return [
            Div("", cls="hidden"),
            build_toast(f"Errore durante il salvataggio: {e}", tone="danger"),
        ]


def delete_snippet(snippet_id: int):
    """Delete a snippet by ID."""
    try:
        OCRStorage().vault.delete_snippet(snippet_id)
        return _toast_only("Snippet eliminato correttamente.", tone="success")
    except Exception as exc:
        logger.exception("Snippet delete error for id=%s", snippet_id)
        return _toast_only(f"Errore durante l'eliminazione dello snippet: {exc}", tone="danger")
