"""Compatibility aggregator for Discovery UI components."""

from .discovery_download_panel import (
    render_download_job_card,
    render_download_manager,
    render_download_status,
    render_studio_export_job_row,
)
from .discovery_form import discovery_form
from .discovery_page import discovery_content
from .discovery_results import (
    render_error_message,
    render_feedback_message,
    render_pdf_capability_badge,
    render_preview,
    render_search_results_list,
)

__all__ = [
    "discovery_content",
    "discovery_form",
    "render_download_job_card",
    "render_download_manager",
    "render_download_status",
    "render_error_message",
    "render_feedback_message",
    "render_pdf_capability_badge",
    "render_preview",
    "render_search_results_list",
    "render_studio_export_job_row",
]

