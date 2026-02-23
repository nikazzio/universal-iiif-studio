"""Library routes registration."""

from studio_ui.routes import library_handlers


def setup_library_routes(app):
    """Register library/local-assets routes."""
    app.get("/library")(library_handlers.library_page)
    app.post("/api/library/delete")(library_handlers.library_delete)
    app.post("/api/library/cleanup_partial")(library_handlers.library_cleanup_partial)
    app.post("/api/library/start_download")(library_handlers.library_start_download)
    app.post("/api/library/retry_missing")(library_handlers.library_retry_missing)
    app.post("/api/library/retry_range")(library_handlers.library_retry_range)
    app.post("/api/library/set_type")(library_handlers.library_set_type)
