def test_export_studio_selection_is_session_state_based():
    # Export Studio selection is intentionally implemented with Streamlit widgets
    # (session_state keys), not URL query params.
    from iiif_downloader.ui.pages.export_studio.thumbnail_grid import _selection_key

    assert _selection_key("DOC", 1) == "export_page_DOC_1"
