from fasthtml.common import Div

from studio_ui.components.layout import base_layout


def test_base_layout_bootstraps_library_filter_navigation():
    """Layout should pre-resolve Library URL from persisted filters to avoid flash."""
    rendered = repr(base_layout("Test", Div("content"), active_page="library"))
    assert "ui.library.filters.v1" in rendered
    assert "window.location.replace('/library?' + query)" in rendered
    assert 'data-nav-key="library"' in rendered
