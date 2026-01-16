import streamlit as st
from iiif_downloader.ocr.model_manager import ModelManager
from iiif_downloader.ocr.storage import OCRStorage

def init_session_state():
    """Initializes all session state variables."""
    
    # Core Services
    if "ocr_storage" not in st.session_state:
        st.session_state["ocr_storage"] = OCRStorage()
        st.session_state["ocr_storage"].migrate_legacy()
        
    if "model_manager" not in st.session_state:
        st.session_state["model_manager"] = ModelManager()

    # Navigation & State
    defaults = {
        "migrated": True,
        "ocr_result": None,
        "last_ocr_page": None,
        "discovery_preview": None,
        "search_results": [],
        "current_page": 1,
        "active_job_id": None, # For async jobs
        "job_status": {},      # job_id -> {status, progress, message}
    }

    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def get_storage() -> OCRStorage:
    return st.session_state["ocr_storage"]

def get_model_manager() -> ModelManager:
    return st.session_state["model_manager"]
