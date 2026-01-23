"""
State Management Module for Studio Page
Centralized session state management to prevent data loss and ensure consistency.
"""

from typing import Any, Optional

import streamlit as st


class StudioState:
    """Manages session state for the Studio page."""

    # State keys
    CURRENT_DOC_ID = "studio_doc_id"
    SHOW_HISTORY = "show_history"
    IMAGE_BRIGHTNESS = "img_brightness"
    IMAGE_CONTRAST = "img_contrast"
    CROP_MODE = "crop_mode"
    CONFIRM_OCR_SYNC = "confirm_ocr_sync"
    TRIGGER_OCR_SYNC = "trigger_ocr_sync"
    CONFIRM_OCR_BATCH = "confirm_ocr_batch"

    @staticmethod
    def init_defaults():
        """Initialize default values for all studio state variables."""
        defaults = {
            StudioState.SHOW_HISTORY: False,
            StudioState.CROP_MODE: False,
            StudioState.CONFIRM_OCR_BATCH: False,
        }

        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    @staticmethod
    def get_page_key(doc_id: str) -> str:
        """Get the session state key for the current page of a document."""
        return f"page_{doc_id}"

    @staticmethod
    def get_current_page(doc_id: str) -> int:
        """Get the current page number for a document."""
        page_key = StudioState.get_page_key(doc_id)
        return st.session_state.get(page_key, 1)

    @staticmethod
    def set_current_page(doc_id: str, page_num: int):
        """Set the current page number for a document."""
        page_key = StudioState.get_page_key(doc_id)
        st.session_state[page_key] = page_num
        # Sincronizza il widget dello slider per mantenere UI coerente
        st.session_state[f"timeline_{doc_id}"] = page_num

    @staticmethod
    def get_image_adjustments(doc_id: str, page_num: int) -> dict:
        """
        Get image adjustments for a specific page.
        Returns default values if not set.
        """
        brightness_key = f"{doc_id}_p{page_num}_brightness"
        contrast_key = f"{doc_id}_p{page_num}_contrast"

        return {
            "brightness": st.session_state.get(brightness_key, 1.0),
            "contrast": st.session_state.get(contrast_key, 1.0),
        }

    @staticmethod
    def set_image_adjustments(doc_id: str, page_num: int, brightness: float, contrast: float):
        """Save image adjustments for a specific page."""
        brightness_key = f"{doc_id}_p{page_num}_brightness"
        contrast_key = f"{doc_id}_p{page_num}_contrast"

        st.session_state[brightness_key] = brightness
        st.session_state[contrast_key] = contrast

    @staticmethod
    def reset_image_adjustments(doc_id: str, page_num: int):
        """Reset image adjustments to default values."""
        StudioState.set_image_adjustments(doc_id, page_num, 1.0, 1.0)

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """Get a value from session state."""
        return st.session_state.get(key, default)

    @staticmethod
    def set(key: str, value: Any):
        """Set a value in session state."""
        st.session_state[key] = value

    @staticmethod
    def toggle(key: str) -> bool:
        """Toggle a boolean value in session state."""
        current = st.session_state.get(key, False)
        st.session_state[key] = not current
        return st.session_state[key]

    @staticmethod
    def get_editor_key(doc_id: str, page_num: int) -> str:
        """Get the unique key for the text editor widget."""
        return f"trans_editor_{doc_id}_{page_num}"

    @staticmethod
    def has_pending_update(doc_id: str, page_num: int) -> bool:
        """Check if there's a pending update for the editor."""
        editor_key = StudioState.get_editor_key(doc_id, page_num)
        return f"pending_update_{editor_key}" in st.session_state

    @staticmethod
    def get_pending_update(doc_id: str, page_num: int) -> Optional[str]:
        """Get pending update text and clear it from state."""
        editor_key = StudioState.get_editor_key(doc_id, page_num)
        pending_key = f"pending_update_{editor_key}"

        if pending_key in st.session_state:
            text = st.session_state[pending_key]
            del st.session_state[pending_key]
            return text
        return None

    @staticmethod
    def set_pending_update(doc_id: str, page_num: int, text: str):
        """Set a pending update for the editor."""
        editor_key = StudioState.get_editor_key(doc_id, page_num)
        st.session_state[f"pending_update_{editor_key}"] = text

    @staticmethod
    def clear_editor_state(doc_id: str, page_num: int):
        """Clear the editor widget state (useful for forcing refresh)."""
        editor_key = StudioState.get_editor_key(doc_id, page_num)
        if editor_key in st.session_state:
            del st.session_state[editor_key]
