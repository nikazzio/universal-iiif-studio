"""
Studio Page - Refactored
Modern interface with image adjustments and cropping.
"""

import streamlit as st

from iiif_downloader.ui.state import get_storage

from .canvas import render_main_canvas
from .sidebar import render_studio_sidebar


def render_studio_page():
    """Main entry point for Studio page."""

    storage = get_storage()
    docs = storage.list_documents()

    if not docs:
        st.title("🏛️ Studio")
        st.info("📚 Nessun documento scaricato. Vai alla sezione 'Discovery' per iniziare.")
        return

    # Get current document
    current_stored_id = st.session_state.get("studio_doc_id")

    if not current_stored_id or not any(d["id"] == current_stored_id for d in docs):
        current_stored_id = docs[0]["id"]
        st.session_state["studio_doc_id"] = current_stored_id

    selected_doc = next(d for d in docs if d["id"] == current_stored_id)
    doc_id, library = selected_doc["id"], selected_doc["library"]
    paths = storage.get_document_paths(doc_id, library)
    stats = storage.load_image_stats(doc_id, library)

    # Render sidebar and canvas
    ocr_engine, current_model = render_studio_sidebar(docs, doc_id, library, paths)
    render_main_canvas(doc_id, library, paths, stats, ocr_engine, current_model)
