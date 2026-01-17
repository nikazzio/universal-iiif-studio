import streamlit as st
import os
from PIL import Image as PILImage
from iiif_downloader.config import config
from iiif_downloader.ui.state import get_storage, get_model_manager
from iiif_downloader.ocr.processor import OCRProcessor
from iiif_downloader.jobs import job_manager

def render_ocr_controls(doc_id, library):
    st.sidebar.subheader("Strumenti OCR")
    
    storage = get_storage()
    manager = get_model_manager()
    default_engine = config.get("defaults", "preferred_ocr_engine", "openai")
    
    ocr_engine = st.sidebar.selectbox("Motore", ["openai", "kraken", "anthropic", "google", "huggingface"], index=["openai", "kraken", "anthropic", "google", "huggingface"].index(default_engine) if default_engine in ["openai", "kraken", "anthropic", "google", "huggingface"] else 0)
    
    current_model = None
    if ocr_engine == "kraken":
        installed = manager.list_installed_models()
        if not installed:
            st.sidebar.warning("Nessun modello Kraken installato.")
        else:
            current_model = st.sidebar.selectbox("Modello HTR", installed)
    elif ocr_engine == "openai":
        current_model = st.sidebar.selectbox("Modello", ["gpt-5", "gpt-5.2", "o3", "o4-mini", "gpt-5,-mini"], index=0)
    
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
            st.toast(f"Job avviato! ID: {job_id}", icon="⚙️")

    if st.session_state.get("confirm_ocr_batch"):
        st.sidebar.warning("⚠️ Ci sono trascrizioni esistenti! Sovrascrivere TUTTO?", icon="🔥")
        c1, c2 = st.sidebar.columns(2)
        if c1.button("Sì, Esegui", use_container_width=True, type="primary"):
             job_id = job_manager.submit_job(
                task_func=run_ocr_batch_task,
                kwargs={"doc_id": doc_id, "library": library, "engine": ocr_engine, "model": current_model},
                job_type="ocr_batch"
            )
             st.toast(f"Job avviato! ID: {job_id}", icon="⚙️")
             st.session_state["confirm_ocr_batch"] = False
        if c2.button("Annulla", use_container_width=True):
            st.session_state["confirm_ocr_batch"] = False
            st.rerun()

    return ocr_engine, current_model

def run_ocr_sync(doc_id, library, page_idx, engine, model):
    storage = get_storage()
    paths = storage.get_document_paths(doc_id, library)
    page_img_path = os.path.join(paths["root"], "pages", f"pag_{page_idx-1:04d}.jpg")
    
    if not os.path.exists(page_img_path):
        st.error("Immagine non trovata, impossibile eseguire OCR.")
        return

    img = PILImage.open(page_img_path)
    
    with st.spinner(f"Elaborazione OCR ({engine})..."):
        proc = OCRProcessor(
            model_path=get_model_manager().get_model_path(model) if engine == "kraken" else None,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        res = proc.process_page(img, engine=engine, model=model)
        
        if not res.get("error"):
            storage.save_transcription(doc_id, page_idx, res, library)
            st.toast("OCR Completato!", icon="✅")
            st.rerun()
        else:
            st.error(f"Errore: {res.get('error')}")

def run_ocr_batch_task(doc_id, library, engine, model, progress_callback=None):
    storage = get_storage()
    paths = storage.get_document_paths(doc_id, library)
    pages_dir = os.path.join(paths["root"], "pages")
    
    files = sorted([f for f in os.listdir(pages_dir) if f.endswith(".jpg")])
    total = len(files)
    
    proc = OCRProcessor(
        model_path=get_model_manager().get_model_path(model) if engine == "kraken" else None,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    
    for i, f in enumerate(files):
        try:
            p_idx = int(f.split("_")[1].split(".")[0]) + 1
        except:
            continue
            
        img_path = os.path.join(pages_dir, f)
        img = PILImage.open(img_path)
        
        res = proc.process_page(img, engine=engine, model=model)
        
        if not res.get("error"):
            storage.save_transcription(doc_id, p_idx, res, library)
        
        if progress_callback:
            progress_callback(i+1, total)
            
    return f"Processed {total} pages."
