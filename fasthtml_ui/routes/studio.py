"""Studio Page - Route Definitions.

This file handles HTTP requests and orchestrates components and pages.
UI logic moved to:
- fasthtml_ui.pages.studio
- fasthtml_ui.components.studio.*
"""

import json
import threading
import time
from pathlib import Path
from urllib.parse import quote, unquote

from fasthtml.common import (
    Div,
    Request,
    Script,
    Span,
)

from fasthtml_ui.components.layout import base_layout
from fasthtml_ui.components.studio.cropper import render_cropper_modal
from fasthtml_ui.components.studio.history import history_tab_content
from fasthtml_ui.components.studio.tabs import render_studio_tabs
from fasthtml_ui.components.studio.transcription import transcription_tab_content
from fasthtml_ui.ocr_state import OCR_JOBS_STATE, get_ocr_job_state, is_ocr_job_running
from fasthtml_ui.pages.studio import document_picker, studio_layout
from iiif_downloader.logger import get_logger
from iiif_downloader.ocr.processor import OCRProcessor
from iiif_downloader.ocr.storage import OCRStorage

logger = get_logger(__name__)


def _build_toast(message: str, tone: str = "success"):
    """Prepare a floating toast that exchanges via hx-swap-oob."""
    tone_map = {
        "success": "bg-emerald-900/95 border border-emerald-500/70 text-emerald-50 shadow-emerald-500/40",
        "info": "bg-slate-900/90 border border-slate-600/80 text-slate-50 shadow-slate-700/50",
        "danger": "bg-rose-900/90 border border-rose-500/70 text-rose-50 shadow-rose-500/40",
    }
    icons = {"success": "✅", "info": "ℹ️", "danger": "⚠️"}
    tone_classes = tone_map.get(tone, tone_map["info"])
    toast_entry = Div(
        Span(icons.get(tone, "ℹ️"), cls="text-lg leading-none"),
        Span(message, cls="text-sm font-semibold text-current"),
        cls=(
            f"studio-toast-entry flex items-center gap-3 rounded-2xl border px-4 py-3 shadow-2xl "
            f"backdrop-blur-sm opacity-0 -translate-y-3 scale-95 transition-all duration-300 {tone_classes}"
        ),
        role="status",
        aria_live="polite",
    )
    toast_container = Div(
        toast_entry,
        id="studio-toast-stack",
        hx_swap_oob="true",
        cls="w-full flex flex-col gap-2",
    )
    toast_script = Script(
        """
        (function () {
            const stack = document.getElementById('studio-toast-stack');
            if (!stack) return;
            const toast = stack.querySelector('.studio-toast-entry');
            if (!toast) return;
            requestAnimationFrame(() => {
                toast.classList.remove('opacity-0', '-translate-y-3', 'scale-95');
                toast.classList.add('opacity-100', 'translate-y-0', 'scale-100');
            });
            const dismiss = () => {
                toast.classList.add('opacity-0', 'translate-y-3');
                toast.classList.remove('opacity-100', 'translate-y-0');
            };
            setTimeout(() => {
                dismiss();
            }, 4800);
            setTimeout(() => {
                if (stack.contains(toast)) {
                    toast.remove();
                }
            }, 5600);
        })();
        """
    )
    return toast_container, toast_script


def _history_refresh_trigger(doc_id: str, library: str, page_idx: int, info_message: str | None = None):
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    hx_url = f"/studio/partial/history?doc_id={encoded_doc}&library={encoded_lib}&page={page_idx}"
    if info_message:
        hx_url += f"&info_message={quote(info_message, safe='')}"
    return Div(
        "",
        cls="hidden",
        hx_get=hx_url,
        hx_target="#tab-content-history",
        hx_swap="innerHTML",
        hx_trigger="load once",
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
    storage = OCRStorage()
    meta = storage.load_metadata(doc_id, library) or {}
    paths = storage.get_document_paths(doc_id, library)
    scans_dir = Path(paths["scans"])
    total_pages = len(list(scans_dir.glob("pag_*.jpg"))) if scans_dir.exists() else 0
    return render_studio_tabs(
        doc_id,
        library,
        page_idx,
        meta,
        total_pages,
        is_ocr_loading=is_ocr_loading,
        ocr_error=ocr_error,
        history_message=history_message,
    )


def setup_studio_routes(app):
    """Register all Studio routes."""

    @app.get("/studio")
    def studio_page(request: Request, doc_id: str = "", library: str = "", page: int = 1):
        """Render Main Studio Layout."""
        doc_id = unquote(doc_id) if doc_id else ""
        library = unquote(library) if library else ""

        if not doc_id or not library:
            return base_layout("Studio - Seleziona Documento", document_picker(), active_page="studio")

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
                title, library, doc_id, page, manifest_url, initial_canvas, manifest_json, total_pages
            )
            return base_layout(f"Studio - {title}", content, active_page="studio")

        except Exception as e:
            logger.exception("Studio Error")
            return base_layout("Errore", Div(f"Errore caricamento: {e}", cls="p-10"))

    @app.get("/studio/partial/tabs")
    def get_studio_tabs(doc_id: str, library: str, page: int):
        doc_id, library = unquote(doc_id), unquote(library)
        page_idx = int(page)
        is_loading = is_ocr_job_running(doc_id, page_idx)
        return build_studio_tab_content(
            doc_id,
            library,
            page_idx,
            is_ocr_loading=is_loading,
        )

    @app.get("/studio/partial/history")
    def get_history_tab(doc_id: str, library: str, page: int, info_message: str | None = None):
        doc_id, library = unquote(doc_id), unquote(library)
        page_idx = int(page)
        return Div(
            *history_tab_content(doc_id, page_idx, library, info_message=info_message),
            cls="p-4",
        )

    # --- ASYNC OCR ROUTES ---

    @app.post("/api/run_ocr_async")
    def run_ocr_async(doc_id: str, library: str, page: int, engine: str, model: str = None):
        logger.info("🔥 [API] run_ocr_async RECEIVED: doc=%s lib=%s pag=%s eng=%s mod=%s",
                    doc_id, library, page, engine, model)
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
                        "timestamp": time.time()
                    }
                    return

                img = Image.open(str(image_path))
                logger.debug("📸 Image loaded successfully: %s (%s)", image_path, img.size)

                from iiif_downloader.config_manager import get_config_manager
                cfg = get_config_manager()

                # Instantiate processor with all keys
                processor = OCRProcessor(
                    openai_api_key=cfg.get_api_key("openai"),
                    anthropic_api_key=cfg.get_api_key("anthropic"),
                    google_api_key=cfg.get_api_key("google_vision"),
                    hf_token=cfg.get_api_key("huggingface")
                )

                logger.debug("🚀 Dispatching OCR request to processor...")

                # Use unified entry point
                res = processor.process_page(img, engine=engine, model=model)

                if res.get("error"):
                    logger.error("❌ OCR Error for %s p%s: %s", doc_id, page_idx, res["error"])
                    OCR_JOBS_STATE[(doc_id, page_idx)] = {
                        "status": "error",
                        "message": str(res["error"]),
                        "timestamp": time.time()
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
                    "timestamp": time.time()
                }


        threading.Thread(target=_ocr_worker, daemon=True).start()

        # Return the tab in loading state
        return transcription_tab_content(doc_id, library, page_idx, is_loading=True)

    @app.get("/api/check_ocr_status")
    def check_ocr_status(doc_id: str, library: str, page: int):
        doc_id, library = unquote(doc_id), unquote(library)
        page_idx = int(page)
        logger.debug("🔎 Checking OCR poll status for %s doc=%s lib=%s", page_idx, doc_id, library)

        job_state = get_ocr_job_state(doc_id, page_idx)
        error_msg = None
        if job_state and job_state.get("status") == "error":
            logger.warning("📍 Polling detected error for %s p%s: %s", doc_id, page_idx, job_state["message"])
            error_msg = job_state["message"]
            OCR_JOBS_STATE.pop((doc_id, page_idx), None)

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
            cls="flex-1 overflow-hidden h-full"
        )

    @app.post("/api/restore_transcription")
    def restore_transcription(doc_id: str, library: str, page: int, timestamp: str):
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

        toast_div, toast_script = _build_toast(
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
                cls="flex-1 overflow-hidden h-full"
            ),
            toast_div,
            toast_script,
        ]

    # --- CROPPER IMPLEMENTATION ---

    @app.get("/studio/cropper")
    def get_cropper(doc_id: str, library: str, page: int):
        doc_id, library = unquote(doc_id), unquote(library)
        lib_q, doc_q = quote(library, safe=""), quote(doc_id, safe="")
        img_url = f"/iiif/image/{lib_q}/{doc_q}/{page}/full/max/0/default.jpg"
        return render_cropper_modal(doc_id, library, int(page), img_url)

    @app.post("/api/save_snippet")
    def save_snippet_api(doc_id: str, library: str, page: int, crop_data: str, transcription: str = ""):
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
            snippet_dir = Path("assets/snippets")
            snippet_dir.mkdir(parents=True, exist_ok=True)
            snippet_path = snippet_dir / filename

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

    @app.post("/api/save_transcription")
    def save_transcription(doc_id: str, library: str, page: int, text: str):
        try:
            doc_id, library = unquote(doc_id), unquote(library)
            storage = OCRStorage()
            page_idx = int(page)
            existing = storage.load_transcription(doc_id, page_idx, library)
            normalized_existing = (existing.get("full_text") if existing else "") or ""
            normalized_new = text or ""

            if normalized_existing == normalized_new:
                message = "Nessuna modifica rilevata; il testo è identico all'ultima versione."
                toast_div, toast_script = _build_toast(message, tone="info")
                refresh_trigger = _history_refresh_trigger(doc_id, library, page_idx, info_message=message)
                return [
                    Div(
                        Span(
                            "ℹ️ Nessuna modifica rilevata; il testo è identico all'ultima versione.",
                            cls="text-xs font-bold text-indigo-600 dark:text-indigo-400",
                        ),
                        cls="mt-2 p-3 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800 rounded-lg animate-in fade-in duration-300",
                        id="save-feedback",
                        hx_swap_oob="true",
                    ),
                    toast_div,
                    toast_script,
                    refresh_trigger,
                ]

            storage.save_transcription(
                doc_id,
                page_idx,
                {"full_text": text, "is_manual": True},
                library,
            )
            toast_div, toast_script = _build_toast("Modifiche salvate con successo nello storico")
            return [
                Div(
                    Span(
                        "✅ Modifiche salvate con successo nello storico",
                        cls="text-xs font-bold text-indigo-600 dark:text-indigo-400",
                    ),
                    cls="mt-2 p-3 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800 rounded-lg animate-in fade-in slide-in-from-top-1 duration-300",
                    id="save-feedback",
                    hx_swap_oob="true",  # Ensure it updates even if target is slightly off
                ),
                toast_div,
                toast_script,
                _history_refresh_trigger(doc_id, library, page_idx),
            ]
        except Exception as e:
            toast_div, toast_script = _build_toast(
                f"Errore durante il salvataggio: {e}",
                tone="danger",
            )
            return [
                Div(
                    Span(f"❌ Errore durante il salvataggio: {e}", cls="text-xs font-bold text-red-600"),
                    cls="mt-2 p-3 bg-red-50 border border-red-100 rounded-lg",
                    id="save-feedback",
                    hx_swap_oob="true"
                ),
                toast_div,
                toast_script,
            ]

    @app.delete("/api/delete_snippet/{snippet_id}")
    def delete_snippet(snippet_id: int):
        OCRStorage().vault.delete_snippet(snippet_id)
        return ""

    @app.delete("/studio/delete")
    def delete_document(doc_id: str, library: str):
        doc_id, library = unquote(doc_id), unquote(library)
        if OCRStorage().delete_document(doc_id, library):
            # After deletion, we return the updated document list (partial)
            # or just trigger a reload of the picker.
            # FastHTML can return the whole picker again.
            return document_picker()
        return Div("Errore durante la rimozione", cls="text-red-500")
