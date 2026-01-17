import streamlit as st
from iiif_downloader.ui.state import get_storage
from .sidebar import render_sidebar_metadata, render_sidebar_jobs, render_sidebar_export
from .ocr_utils import render_ocr_controls
from .canvas import render_main_canvas

def render_studio_page():
    storage = get_storage()
    docs = storage.list_documents()
    
    if not docs:
        st.title("🏛️ Studio")
        st.info("Nessun documento scaricato. Vai alla sezione 'Discovery' per iniziare.")
        return

    # --- SIDEBAR: SELECTION ---
    st.sidebar.subheader("Selezione Documento")
    
    default_idx = 0
    if "studio_doc_id" in st.session_state and st.session_state["studio_doc_id"]:
        for i, d in enumerate(docs):
            if d["id"] == st.session_state["studio_doc_id"]:
                default_idx = i
                break
        st.session_state["studio_doc_id"] = None
        
    doc_labels = [f"{d['library']} / {d['id']}" for d in docs]
    selected_label = st.sidebar.selectbox("Manoscritto", doc_labels, index=default_idx)
    selected_doc = next(d for d in docs if f"{d['library']} / {d['id']}" == selected_label)
    
    doc_id, library = selected_doc["id"], selected_doc["library"]
    paths = storage.get_document_paths(doc_id, library)
    
    # --- METADATA PANEL ---
    stats = storage.load_image_stats(doc_id, library)
    meta = storage.load_metadata(doc_id, library)
    
    render_sidebar_metadata(meta, stats)
    render_sidebar_jobs()
    render_sidebar_export(doc_id, paths)

    # --- OCR CONTROLS ---
    st.sidebar.markdown("---")
    ocr_engine, current_model = render_ocr_controls(doc_id, library)
    
    # --- MAIN CANVAS ---
    render_main_canvas(doc_id, library, paths, stats, ocr_engine, current_model)
