"""Shared state helpers for in-flight OCR jobs."""

from typing import Any

# Keep track of background OCR jobs keyed by (doc_id, page).
OCR_JOBS_STATE: dict[tuple[str, int], dict[str, Any]] = {}


def is_ocr_job_running(doc_id: str, page: int) -> bool:
    """Return True while an OCR job is still marked as running."""
    state = OCR_JOBS_STATE.get((doc_id, page))
    return bool(state and state.get("status") == "running")


def get_ocr_job_state(doc_id: str, page: int) -> dict[str, Any] | None:
    """Return the stored OCR job state if available."""
    return OCR_JOBS_STATE.get((doc_id, page))
