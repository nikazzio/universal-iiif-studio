from iiif_downloader.ui.pages.export_studio.thumbnail_grid import _selection_key


def test_selection_key_stable():
    assert _selection_key("DOC", 2) == "export_page_DOC_2"
