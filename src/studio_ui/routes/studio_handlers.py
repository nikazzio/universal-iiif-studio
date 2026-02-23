"""Studio route handlers moved out of the routes registration module.

This module contains the logic-heavy request handlers and helpers.
"""

import json
import time
from pathlib import Path
from urllib.parse import quote, unquote

from fasthtml.common import Div, Request, Script

from studio_ui.common.htmx import history_refresh_script
from studio_ui.common.toasts import build_toast
from studio_ui.components.layout import base_layout
from studio_ui.components.studio.cropper import render_cropper_modal
from studio_ui.components.studio.history import history_tab_content
from studio_ui.components.studio.tabs import render_studio_tabs
from studio_ui.components.studio.transcription import transcription_tab_content
from studio_ui.config import get_api_key, get_snippets_dir
from studio_ui.ocr_state import OCR_JOBS_STATE, get_ocr_job_state, is_ocr_job_running
from studio_ui.pages.studio import document_picker, studio_layout
from universal_iiif_core.jobs import job_manager
from universal_iiif_core.logger import get_logger
from universal_iiif_core.services.ocr.processor import OCRProcessor
from universal_iiif_core.services.ocr.storage import OCRStorage
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
    paths = storage.get_document_paths(doc_id, library)
    scans_dir = Path(paths["scans"])
    total_pages = len(list(scans_dir.glob("pag_*.jpg"))) if scans_dir.exists() else 0
    manifest_json = load_json(paths["manifest"]) or {}
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
    )


def studio_page(request: Request, doc_id: str = "", library: str = "", page: int = 1):
    """Render Main Studio Layout."""
    doc_id = unquote(doc_id) if doc_id else ""
    library = unquote(library) if library else ""
    is_hx = request.headers.get("HX-Request") == "true"

    if not doc_id or not library:
        content = document_picker()
        if is_hx:
            return content
        return base_layout("Studio - Seleziona Documento", content, active_page="studio")

    try:
        storage = OCRStorage()
        paths = storage.get_document_paths(doc_id, library)
        meta = storage.load_metadata(doc_id, library)
        title = meta.get("label", doc_id) if meta else doc_id

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
            meta or {},
        )
        if is_hx:
            return content
        return base_layout(f"Studio - {title}", content, active_page="studio")

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


def delete_document(doc_id: str, library: str):
    """Delete an entire document and its data."""
    doc_id, library = unquote(doc_id), unquote(library)
    if OCRStorage().delete_document(doc_id, library):
        return [document_picker(), build_toast(f"Documento '{doc_id}' eliminato.", tone="success")]
    return [
        document_picker(),
        build_toast(f"Errore durante la rimozione di '{doc_id}'.", tone="danger"),
    ]
