def test_studio_routes_importable():
    """Ensure the new FastHTML studio routes module imports."""
    from studio_ui.routes.studio import setup_studio_routes

    assert callable(setup_studio_routes)


def test_studio_tabs_importable():
    """Ensure the studio tabs component imports."""
    from studio_ui.components.studio.tabs import render_studio_tabs

    assert callable(render_studio_tabs)


def test_export_routes_importable():
    """Ensure export routes module imports correctly."""
    from studio_ui.routes.export import setup_export_routes

    assert callable(setup_export_routes)


def test_export_components_importable():
    """Ensure export component module imports correctly."""
    from studio_ui.components.export import render_export_page

    assert callable(render_export_page)
