import time
from pathlib import Path

import streamlit as st
from PIL import Image as PILImage

from iiif_downloader.config_manager import get_config_manager
from iiif_downloader.jobs import job_manager
from iiif_downloader.logger import get_logger
from iiif_downloader.ocr.processor import OCRProcessor
from iiif_downloader.ui.notifications import toast
from iiif_downloader.ui.state import get_model_manager, get_storage

logger = get_logger(__name__)


def render_ocr_controls(doc_id, library):
    st.sidebar.subheader("Strumenti OCR")

    storage = get_storage()
    manager = get_model_manager()
    cm = get_config_manager()
    default_engine = cm.get_setting("defaults.preferred_ocr_engine", "openai")

    engines = ["openai", "kraken", "anthropic", "google", "huggingface"]
    engine_index = engines.index(default_engine) if default_engine in engines else 0
    ocr_engine = st.sidebar.selectbox("Motore", engines, index=engine_index)

    current_model = None
    if ocr_engine == "kraken":
        installed = manager.list_installed_models()
        if not installed:
            st.sidebar.warning("Nessun modello Kraken installato.")
        else:
            current_model = st.sidebar.selectbox("Modello HTR", installed)
    elif ocr_engine == "openai":
        current_model = st.sidebar.selectbox(
            "Modello",
            ["gpt-5.2", "gpt-5", "o4-mini", "o3"],
            index=0,
        )

    if st.sidebar.button("📚 OCR Intero Manoscritto (Background)", use_container_width=True):
        full_data = storage.load_transcription(doc_id, None, library)
        has_data = full_data and len(full_data.get("pages", [])) > 0

        if has_data:
            st.session_state["confirm_ocr_batch"] = True
        else:
            job_id = job_manager.submit_job(
                task_func=run_ocr_batch_task,
                kwargs={"doc_id": doc_id, "library": library, "engine": ocr_engine, "model": current_model},
                job_type="ocr_batch"
            )
            toast(f"Job avviato! ID: {job_id}", icon="⚙️")

    if st.session_state.get("confirm_ocr_batch"):
        st.sidebar.warning("⚠️ Ci sono trascrizioni esistenti! Sovrascrivere TUTTO?", icon="🔥")
        c1, c2 = st.sidebar.columns(2)
        if c1.button("Sì, Esegui", use_container_width=True, type="primary"):
            job_id = job_manager.submit_job(
                task_func=run_ocr_batch_task,
                kwargs={"doc_id": doc_id, "library": library, "engine": ocr_engine, "model": current_model},
                job_type="ocr_batch"
            )
            toast(f"Job avviato! ID: {job_id}", icon="⚙️")
            st.session_state["confirm_ocr_batch"] = False
        if c2.button("Annulla", use_container_width=True):
            st.session_state["confirm_ocr_batch"] = False
            st.rerun()

    return ocr_engine, current_model


def run_ocr_sync(doc_id, library, page_idx, engine, model):
    storage = get_storage()
    paths = storage.get_document_paths(doc_id, library)
    page_img_path = Path(paths["scans"]) / f"pag_{page_idx-1:04d}.jpg"

    img = None
    if page_img_path.exists():
        img = PILImage.open(str(page_img_path))
    else:
        # Fallback: render directly from PDF (useful if user skipped extraction).
        pdf_path = Path(paths.get("pdf") or "")
        if pdf_path.exists():
            from iiif_downloader.pdf_utils import load_pdf_page

            cm = get_config_manager()
            ocr_dpi = int(cm.get_setting("pdf.ocr_dpi", 300))
            img, pdf_err = load_pdf_page(str(pdf_path), page_idx, dpi=ocr_dpi, return_error=True)
            if pdf_err:
                st.error(pdf_err)
                return
        else:
            st.error("Immagine non trovata, impossibile eseguire OCR.")
            return

    with st.status(f"Elaborazione OCR ({engine})...", expanded=True) as status:
        def update_status(text):
            status.update(label=text)
            logger.debug("UI Status Update: %s", text)

        cm = get_config_manager()
        proc = OCRProcessor(
            model_path=get_model_manager().get_model_path(model) if engine == "kraken" else None,
            openai_api_key=cm.get_api_key("openai", ""),
            anthropic_api_key=cm.get_api_key("anthropic", ""),
            google_api_key=cm.get_api_key("google_vision", ""),
            hf_token=cm.get_api_key("huggingface", ""),
        )
        res = proc.process_page(img, engine=engine, model=model, status_callback=update_status)

        if not res.get("error"):
            status.update(label="OCR Completato!", state="complete", expanded=False)
            storage.save_transcription(doc_id, page_idx, res, library)

            # UI Sync Fix: Use a pending update to ensure the text_area reflects the new text
            # immediately during the next rerun, avoiding the StreamlitAPIException.
            edit_key = f"trans_editor_{doc_id}_{page_idx}"
            st.session_state[f"pending_update_{edit_key}"] = res.get("full_text", "")

            toast("OCR Completato!", icon="✅")
            time.sleep(0.5)
            st.rerun()
        else:
            status.update(label=f"Errore: {res.get('error')}", state="error")
            st.error(f"Errore: {res.get('error')}")


def run_ocr_batch_task(doc_id, library, engine, model, progress_callback=None):
    storage = get_storage()
    paths = storage.get_document_paths(doc_id, library)
    scans_dir = paths["scans"]

    scans_dir_p = Path(scans_dir)
    files = sorted([p.name for p in scans_dir_p.iterdir() if p.suffix.lower() == ".jpg"])
    total = len(files)

    cm = get_config_manager()
    proc = OCRProcessor(
        model_path=get_model_manager().get_model_path(model) if engine == "kraken" else None,
        openai_api_key=cm.get_api_key("openai", ""),
        anthropic_api_key=cm.get_api_key("anthropic", ""),
        google_api_key=cm.get_api_key("google_vision", ""),
        hf_token=cm.get_api_key("huggingface", ""),
    )

    for i, f in enumerate(files):
        try:
            p_idx = int(f.split("_")[1].split(".")[0]) + 1
        except (IndexError, ValueError):
            continue

        img_path = scans_dir_p / f
        img = PILImage.open(str(img_path))

        res = proc.process_page(img, engine=engine, model=model)

        if not res.get("error"):
            storage.save_transcription(doc_id, p_idx, res, library)

        if progress_callback:
            progress_callback(i+1, total)

    return f"Processed {total} pages."
