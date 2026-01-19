def test_export_studio_page_importable():
    from iiif_downloader.ui.pages.export_studio import render_export_studio_page

    assert callable(render_export_studio_page)


def test_export_studio_thumbnail_grid_importable():
    from iiif_downloader.ui.pages.export_studio.thumbnail_grid import render_thumbnail_grid

    assert callable(render_thumbnail_grid)
