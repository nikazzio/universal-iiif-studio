"""Route handlers for the Statistics page and sidebar widget."""

from __future__ import annotations

import time as _time

from fasthtml.common import Request

from studio_ui.components.layout import base_layout
from studio_ui.components.library_stats import (
    render_library_stats,
    render_sidebar_stats_widget,
    render_stats_page_content,
)
from universal_iiif_core.services.storage.vault_manager import VaultManager

_detail_cache: tuple[float, object] | None = None
_DETAIL_TTL = 300.0  # seconds


def stats_page(request: Request):
    """Render the full Statistics page."""
    manuscripts = VaultManager().get_all_manuscripts()
    content = render_stats_page_content(manuscripts)
    if request.headers.get("HX-Request") == "true":
        return content
    return base_layout("Statistiche", content, active_page="stats")


def stats_sidebar_widget():
    """Return the compact nerd-stats widget for the sidebar footer (DB-only)."""
    manuscripts = VaultManager().get_all_manuscripts()
    return render_sidebar_stats_widget(manuscripts)


def stats_detail_content():
    """Return the lazy-loaded detail metrics panel (disk + transcription scan).

    Result is cached for 5 minutes to avoid repeated full-disk scans on reload.
    """
    global _detail_cache
    now = _time.monotonic()
    if _detail_cache is not None and now - _detail_cache[0] < _DETAIL_TTL:
        return _detail_cache[1]
    manuscripts = VaultManager().get_all_manuscripts()
    result = render_library_stats(manuscripts)
    _detail_cache = (now, result)
    return result
