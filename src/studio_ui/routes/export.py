"""Export routes registration."""

from studio_ui.routes import export_handlers


def setup_export_routes(app):
    """Register export routes and APIs."""
    app.get("/export")(export_handlers.export_page)
    app.get("/api/export/jobs")(export_handlers.export_jobs)
    app.get("/api/export/capabilities")(export_handlers.export_capabilities)
    app.post("/api/export/start")(export_handlers.start_export)
    app.post("/api/export/cancel/{job_id}")(export_handlers.cancel_export)
    app.post("/api/export/remove/{job_id}")(export_handlers.remove_export)
    app.get("/api/export/download/{job_id}")(export_handlers.download_export)
