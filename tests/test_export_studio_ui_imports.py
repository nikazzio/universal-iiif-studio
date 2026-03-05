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


def test_setup_studio_routes_registers_expected_partials_only():
    """Studio routes should keep PR3 partials limited to tabs/history/export."""
    from studio_ui.routes.studio import setup_studio_routes

    class _FakeApp:
        def __init__(self) -> None:
            self.routes: list[tuple[str, str]] = []

        def get(self, path: str):
            def _decorator(_handler):
                self.routes.append(("GET", path))
                return _handler

            return _decorator

        def post(self, path: str):
            def _decorator(_handler):
                self.routes.append(("POST", path))
                return _handler

            return _decorator

        def delete(self, path: str):
            def _decorator(_handler):
                self.routes.append(("DELETE", path))
                return _handler

            return _decorator

    app = _FakeApp()
    setup_studio_routes(app)
    get_paths = {path for method, path in app.routes if method == "GET"}

    assert "/studio/partial/tabs" in get_paths
    assert "/studio/partial/history" in get_paths
    assert "/studio/partial/export" in get_paths
    assert "/studio/partial/viewer" not in get_paths
    assert "/studio/partial/availability" not in get_paths
