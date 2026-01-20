"""
Main Canvas Module - Refactored
Clean, modular implementation of the Studio page canvas with modern layout.
Separated concerns: UI rendering, state management, and image processing.
"""

import os

import streamlit as st

from iiif_downloader.logger import get_logger
from iiif_downloader.ui.state import get_storage

from .image_viewer import render_image_viewer
from .studio_state import StudioState
from .text_editor import render_history_sidebar, render_transcription_editor

logger = get_logger(__name__)


def render_main_canvas(
    doc_id: str, library: str, paths: dict, stats: dict = None, ocr_engine: str = "openai", current_model: str = "gpt-5"
):
    """
    Main canvas renderer with modern two-column layout.

    Args:
        doc_id: Document ID
        library: Library name
        paths: Dictionary with file paths
        stats: Optional image statistics
        ocr_engine: OCR engine name
        current_model: OCR model name
    """

    # Initialize state
    StudioState.init_defaults()

    storage = get_storage()
    meta = storage.load_metadata(doc_id, library)

    # Calculate total pages
    total_pages = _calculate_total_pages(meta, paths)

    # Get current page with query param handling
    current_page = _handle_page_navigation(doc_id, total_pages)

    # CSS compatto per ridurre spazi
    st.markdown("""
        <style>
        /* Riduzione padding globale - ma non troppo per evitare taglio titolo */
        .block-container { padding-top: 2rem !important; }
        h1, h2 { margin-top: 0.3rem !important; margin-bottom: 0.5rem !important; }
        /* Allineamento colonne */
        [data-testid="column"] { height: 100%; }
        </style>
    """, unsafe_allow_html=True)

    # Page title compatto con margin sufficiente
    st.markdown(f"<h2 style='margin: 0.5rem 0; padding: 0.5rem 0;'>🏛️ {doc_id}</h2>", unsafe_allow_html=True)

    # TWO COLUMN LAYOUT (55% Image - 45% Editor)
    col_img, col_work = st.columns([0.55, 0.55], gap="small")

    # LEFT COLUMN: Image Viewer
    with col_img:
        img_obj, page_stats = render_image_viewer(doc_id, library, paths, current_page, stats, total_pages)

    # RIGHT COLUMN: Work Area with Tabs
    with col_work:
        trans, text_val = render_transcription_editor(doc_id, library, current_page, ocr_engine, current_model, paths, total_pages)


def _calculate_total_pages(meta: dict, paths: dict) -> int:
    """
    Calculate total number of pages from various sources.

    Returns:
        Total page count (minimum 1)
    """
    total_pages = 100  # Default fallback

    if meta and meta.get("pages"):
        total_pages = int(meta.get("pages"))
    else:
        scans_dir = paths.get("scans")
        if scans_dir and os.path.exists(scans_dir):
            files = [f for f in os.listdir(scans_dir) if f.endswith(".jpg")]
            if files:
                total_pages = len(files)

    return max(1, total_pages)


def _handle_page_navigation(doc_id: str, total_pages: int) -> int:
    """
    Handle page navigation with query params and session state.

    Returns:
        Current page number (1-indexed)
    """
    page_key = StudioState.get_page_key(doc_id)

    # Initialize if missing
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    # Handle query param navigation (for direct links)
    q_page = st.query_params.get("page_nav")
    if q_page:
        try:
            target_p = int(q_page)
            if 1 <= target_p <= total_pages:
                StudioState.set_current_page(doc_id, target_p)
                # Clear page_nav query param to prevent sticky behavior
                if "page_nav" in st.query_params:
                    del st.query_params["page_nav"]
        except (TypeError, ValueError):
            logger.debug("Invalid page_nav query param: %r", q_page)

    return StudioState.get_current_page(doc_id)
