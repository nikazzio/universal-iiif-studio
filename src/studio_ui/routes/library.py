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
    app.post("/api/library/update_notes")(library_handlers.library_update_notes)
    app.post("/api/library/refresh_metadata")(library_handlers.library_refresh_metadata)
    app.post("/api/library/reclassify")(library_handlers.library_reclassify)
    app.post("/api/library/reclassify_all")(library_handlers.library_reclassify_all)
    app.post("/api/library/normalize_states")(library_handlers.library_normalize_states)
