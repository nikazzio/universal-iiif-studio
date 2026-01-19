import streamlit as st

from iiif_downloader.ocr.model_manager import ModelManager
from iiif_downloader.ocr.storage import OCRStorage


def init_session_state():
    """Initializes all session state variables."""

    # Core Services
    if "ocr_storage" not in st.session_state:
        st.session_state["ocr_storage"] = OCRStorage()

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
        "active_job_id": None,  # For async jobs
        "job_status": {},  # job_id -> {status, progress, message}
    }

    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def get_storage() -> OCRStorage:
    # Handle stale instances in session state after code updates
    refresh = False
    if "ocr_storage" in st.session_state:
        # Check if the instance has the required version
        last_version = getattr(st.session_state["ocr_storage"], "STORAGE_VERSION", 0)
        if last_version < OCRStorage.STORAGE_VERSION:
            refresh = True
    else:
        refresh = True

    if refresh:
        st.session_state["ocr_storage"] = OCRStorage()

    return st.session_state["ocr_storage"]


def get_model_manager() -> ModelManager:
    return st.session_state["model_manager"]
