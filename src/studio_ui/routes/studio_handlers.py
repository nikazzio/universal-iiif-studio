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

        # Initial Canvas Selection
        initial_canvas = None
        manifest_path = Path(paths["manifest"])

        if not manifest_path.exists():
            return Div("Manifesto non trovato", cls="p-10")

        with manifest_path.open(encoding="utf-8") as f:
            manifest_json = json.load(f)
            items = []
            if "sequences" in manifest_json:
                items = manifest_json["sequences"][0].get("canvases", [])
            elif "items" in manifest_json:
                items = manifest_json["items"]

            target_idx = int(page) - 1
            if 0 <= target_idx < len(items):
                initial_canvas = items[target_idx].get("@id") or items[target_idx].get("id")

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
                # Clear any previous error state
                OCR_JOBS_STATE.pop((doc_id, page_idx), None)

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
    if job_state and job_state.get("status") == "error":
        logger.warning("📍 Polling detected error for %s p%s: %s", doc_id, page_idx, job_state["message"])
        error_msg = job_state.get("message")

    is_loading = is_ocr_job_running(doc_id, page_idx)
    if is_loading:
        logger.debug("⌛ OCR still processing for %s p%s; continuing spinner", doc_id, page_idx)
    else:
        logger.info("📡 Polling resolved or idle for %s p%s; refreshing panel", doc_id, page_idx)

    return Div(
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

    toast_div, toast_script = build_toast(
        message,
        tone="success" if entry else "danger",
    )
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
        toast_div,
        toast_script,
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
            return Div("Errore: Impossibile creare ritaglio", cls="text-red-500")

        filename = f"{doc_id}_p{int(page):04d}_{int(time.time())}.png"
        snippet_path = get_snippets_dir() / filename

        with snippet_path.open("wb") as f:
            f.write(crop_bytes)

        vault.save_snippet(
            doc_id, int(page), str(snippet_path), category="Manual", transcription=transcription, coords=data
        )

        from fasthtml.common import Script

        return Script(
            "document.getElementById('cropper-modal-container').innerHTML = ''; htmx.trigger('#tab-snippets', 'click');"
        )

    except Exception as e:
        logger.exception("Snippet Save Error")
        return Div(f"Errore salvataggio: {e}", cls="text-red-500")


def save_transcription(doc_id: str, library: str, page: int, text: str):
    """Save manual transcription edits from the Studio."""
    try:
        doc_id, library = unquote(doc_id), unquote(library)
        storage = OCRStorage()
        page_idx = int(page)
        existing = storage.load_transcription(doc_id, page_idx, library)
        normalized_existing = (existing.get("full_text") if existing else "") or ""
        normalized_new = text or ""

        encoded_doc = quote(doc_id, safe="")
        encoded_lib = quote(library, safe="")
        hx_url = f"/studio/partial/tabs?doc_id={encoded_doc}&library={encoded_lib}&page={page_idx}"
        hx_js_url = json.dumps(hx_url)

        if normalized_existing == normalized_new:
            js_icon = json.dumps("ℹ️")
            js_msg = json.dumps("Nessuna modifica rilevata; il testo è identico all'ultima versione.")
            js_tone = json.dumps("bg-slate-900/90 border border-slate-600/80 text-slate-50 shadow-slate-700/50")
            parts = [
                "(function(){",
                "try{",
                " const stack = document.getElementById('studio-toast-stack');",
                " if(stack){",
                "  const toast = document.createElement('div');",
                "  toast.className = 'studio-toast-entry flex items-center gap-3 rounded-2xl border px-4 py-3 ' + ",
                "  'shadow-2xl backdrop-blur-sm opacity-0 -translate-y-3 scale-95 ' + ",
                js_tone,
                ";",
                "  toast.setAttribute('role','status'); toast.setAttribute('aria-live','polite');",
                "  toast.innerHTML = '<span class=\\'text-lg leading-none\\>' + ",
                js_icon,
                " + '</span><span class=\\'text-sm font-semibold text-current\\>' + ",
                js_msg,
                " + '</span>';",
                "  stack.appendChild(toast);",
                "  requestAnimationFrame(()=>{ toast.classList.remove('opacity-0','-translate-y-3','scale-95'); ",
                " toast.classList.add('opacity-100','translate-y-0','scale-100'); });",
                "  setTimeout(()=>{ toast.classList.add('opacity-0','translate-y-3'); ",
                " toast.classList.remove('opacity-100','translate-y-0'); },4800);",
                "  setTimeout(()=>{ if(stack.contains(toast)) toast.remove(); },5600);",
                " }",
                "}catch(e){console.error('toast-err',e);}",
                " setTimeout(function(){ try{ htmx.ajax('GET', ",
                hx_js_url,
                " , {target:'#studio-right-panel', swap:'innerHTML'}); ",
                " }catch(e){console.error('refresh-err',e);} }, 50);",
                "})();",
            ]
            js = "".join(parts)
            return Script(js)

        # Save the transcription
        storage.save_transcription(
            doc_id,
            page_idx,
            {"full_text": text, "is_manual": True},
            library,
        )

        js_icon = json.dumps("✅")
        js_msg = json.dumps("Modifiche salvate con successo nello storico")
        js_tone = json.dumps("bg-emerald-900/95 border border-emerald-500/70 text-emerald-50 shadow-emerald-500/40")
        parts = [
            "(function(){",
            "try{",
            " const stack = document.getElementById('studio-toast-stack');",
            " if(stack){",
            "  const toast = document.createElement('div');",
            "  toast.className = 'studio-toast-entry flex items-center gap-3 rounded-2xl border px-4 py-3 ' + ",
            "  'shadow-2xl backdrop-blur-sm opacity-0 -translate-y-3 scale-95 ' + ",
            js_tone,
            ";",
            "  toast.setAttribute('role','status'); toast.setAttribute('aria-live','polite');",
            "  toast.innerHTML = '<span class=\\'text-lg leading-none\\>' + ",
            js_icon,
            " + '</span><span class=\\'text-sm font-semibold text-current\\>' + ",
            js_msg,
            " + '</span>';",
            "  stack.appendChild(toast);",
            "  requestAnimationFrame(()=>{ toast.classList.remove('opacity-0','-translate-y-3','scale-95'); ",
            " toast.classList.add('opacity-100','translate-y-0','scale-100'); });",
            "  setTimeout(()=>{ toast.classList.add('opacity-0','translate-y-3'); ",
            " toast.classList.remove('opacity-100','translate-y-0'); },4800);",
            "  setTimeout(()=>{ if(stack.contains(toast)) toast.remove(); },5600);",
            " }",
            "}catch(e){console.error('toast-err',e);}",
            " setTimeout(function(){ try{ htmx.ajax('GET', ",
            hx_js_url,
            " , {target:'#studio-right-panel', swap:'innerHTML'}); ",
            " }catch(e){console.error('refresh-err',e);} }, 50);",
            "})();",
        ]
        js = "".join(parts)
        return Script(js)
    except Exception as e:
        js_icon = json.dumps("⚠️")
        js_msg = json.dumps(f"Errore durante il salvataggio: {e}")
        js_tone = json.dumps("bg-rose-900/90 border border-rose-500/70 text-rose-50 shadow-rose-500/40")
        parts = [
            "(function(){",
            "try{",
            " const stack = document.getElementById('studio-toast-stack');",
            " if(stack){",
            "  const toast = document.createElement('div');",
            "  toast.className = 'studio-toast-entry flex items-center gap-3 rounded-2xl border px-4 py-3 ' + ",
            "  'shadow-2xl backdrop-blur-sm opacity-0 -translate-y-3 scale-95 ' + ",
            js_tone,
            ";",
            "  toast.setAttribute('role','status'); toast.setAttribute('aria-live','polite');",
            "  toast.innerHTML = '<span class=\\'text-lg leading-none\\>' + ",
            js_icon,
            " + '</span><span class=\\'text-sm font-semibold text-current\\>' + ",
            js_msg,
            " + '</span>';",
            "  stack.appendChild(toast);",
            "  requestAnimationFrame(()=>{ toast.classList.remove('opacity-0','-translate-y-3','scale-95'); ",
            " toast.classList.add('opacity-100','translate-y-0','scale-100'); });",
            "  setTimeout(()=>{ toast.classList.add('opacity-0','translate-y-3'); ",
            " toast.classList.remove('opacity-100','translate-y-0'); },4800);",
            "  setTimeout(()=>{ if(stack.contains(toast)) toast.remove(); },5600);",
            " }",
            "}catch(e){console.error('toast-err',e);}",
            "})();",
        ]
        js = "".join(parts)
        return Script(js)


def delete_snippet(snippet_id: int):
    """Delete a snippet by ID."""
    OCRStorage().vault.delete_snippet(snippet_id)
    return ""


def delete_document(doc_id: str, library: str):
    """Delete an entire document and its data."""
    doc_id, library = unquote(doc_id), unquote(library)
    if OCRStorage().delete_document(doc_id, library):
        return document_picker()
    return Div("Errore durante la rimozione", cls="text-red-500")
