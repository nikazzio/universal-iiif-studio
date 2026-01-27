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
    Span,
)

from fasthtml_ui.components.layout import base_layout
from fasthtml_ui.components.studio.cropper import render_cropper_modal
from fasthtml_ui.components.studio.tabs import render_studio_tabs
from fasthtml_ui.components.studio.transcription import transcription_tab_content
from fasthtml_ui.pages.studio import document_picker, studio_layout
from iiif_downloader.logger import get_logger
from iiif_downloader.ocr.processor import OCRProcessor
from iiif_downloader.ocr.storage import OCRStorage

logger = get_logger(__name__)

# Transient state for async jobs (tracking errors)
OCR_JOBS_STATE = {} # Key: (doc_id, page), Value: {"status": "error", "message": "...", "timestamp": ...}


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
        storage = OCRStorage()
        meta = storage.load_metadata(doc_id, library)
        paths = storage.get_document_paths(doc_id, library)
        scans_dir = Path(paths["scans"])
        total_pages = len(list(scans_dir.glob("pag_*.jpg"))) if scans_dir.exists() else 0
        return render_studio_tabs(doc_id, library, int(page), meta, total_pages)

    # --- ASYNC OCR ROUTES ---

    @app.post("/api/run_ocr_async")
    def run_ocr_async(doc_id: str, library: str, page: int, engine: str, model: str = None):
        logger.info("🔥 [API] run_ocr_async RECEIVED: doc=%s lib=%s pag=%s eng=%s mod=%s", 
                    doc_id, library, page, engine, model)
        doc_id, library = unquote(doc_id), unquote(library)
        logger.debug("🔓 [API] Unquoted: doc=%s lib=%s", doc_id, library)


        def _ocr_worker():
            try:
                storage = OCRStorage()
                paths = storage.get_document_paths(doc_id, library)
                image_path = Path(paths["scans"]) / f"pag_{int(page) - 1:04d}.jpg"

                logger.info("🧵 OCR Worker started for %s [Page %s] using %s", doc_id, page, engine)

                from PIL import Image
                if not image_path.exists():
                    logger.error("❌ Image not found for OCR: %s", image_path)
                    OCR_JOBS_STATE[(doc_id, int(page))] = {
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
                    logger.error("❌ OCR Error for %s p%s: %s", doc_id, page, res["error"])
                    OCR_JOBS_STATE[(doc_id, int(page))] = {
                        "status": "error",
                        "message": str(res["error"]),
                        "timestamp": time.time()
                    }
                else:
                    storage.save_transcription(doc_id, int(page), res, library)
                    logger.info("✅ Async OCR success & auto-saved: %s p%s", doc_id, page)
                    # Clear any previous error state
                    OCR_JOBS_STATE.pop((doc_id, int(page)), None)

            except Exception as e:
                err_msg = str(e)
                logger.exception("💥 Critical Failure in Async OCR worker for %s p%s", doc_id, page)
                OCR_JOBS_STATE[(doc_id, int(page))] = {
                    "status": "error",
                    "message": f"Critical Error: {err_msg}",
                    "timestamp": time.time()
                }


        threading.Thread(target=_ocr_worker, daemon=True).start()

        # Return the tab in loading state
        return transcription_tab_content(doc_id, library, page, is_loading=True)

    @app.get("/api/check_ocr_status")
    def check_ocr_status(doc_id: str, library: str, page: int):
        doc_id, library = unquote(doc_id), unquote(library)
        storage = OCRStorage()
        trans = storage.load_transcription(doc_id, page, library)

        # 1. Success: Return the fully updated transcription tab content
        if trans and trans.get("full_text") and (doc_id, int(page)) not in OCR_JOBS_STATE:
             return Div(
                 *transcription_tab_content(doc_id, library, page, is_loading=False),
                 id="transcription-container",
                 cls="relative h-full"
             )

        # 2. Check for documented failure in worker
        job_state = OCR_JOBS_STATE.get((doc_id, int(page)))
        if job_state and job_state["status"] == "error":
            logger.warning("📍 Polling detected error for %s p%s: %s", doc_id, page, job_state["message"])
            msg = job_state["message"]
            OCR_JOBS_STATE.pop((doc_id, int(page)), None) # Clear after reporting
            return Div(
                *transcription_tab_content(doc_id, library, page, error_msg=msg, is_loading=False),
                id="transcription-container",
                cls="relative h-full"
            )

        # 3. Still processing: Return loading state again (which continues polling)
        return Div(
            *transcription_tab_content(doc_id, library, page, is_loading=True),
            id="transcription-container",
            cls="relative h-full"
        )

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
            OCRStorage().save_transcription(
                doc_id, int(page), {"full_text": text, "is_manual": True}, library
            )
            # Return a beautiful toast feedback
            return Div(
                Span(
                    "✅ Modifiche salvate con successo nello storico",
                    cls="text-xs font-bold text-indigo-600 dark:text-indigo-400",
                ),
                cls="mt-2 p-3 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800 rounded-lg animate-in fade-in slide-in-from-top-1 duration-300",
                id="save-feedback",
                hx_swap_oob="true",  # Ensure it updates even if target is slightly off
            )
        except Exception as e:
            return Div(
                Span(f"❌ Errore durante il salvataggio: {e}", cls="text-xs font-bold text-red-600"),
                cls="mt-2 p-3 bg-red-50 border border-red-100 rounded-lg",
                id="save-feedback",
                hx_swap_oob="true"
            )

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
