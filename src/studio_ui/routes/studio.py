"""Studio routes registration.

This module only registers routes and delegates logic to
`studio_ui.routes.studio_handlers` to keep routing thin and
reduce cyclomatic complexity in this file.
"""

import studio_ui.routes.studio_handlers as handlers


def setup_studio_routes(app):
    """Register studio-related routes on `app`.

    This function binds path decorators to handler callables from
    `studio_ui.routes.studio_handlers`.
    """
    app.get("/studio")(handlers.studio_page)
    app.get("/studio/partial/tabs")(handlers.get_studio_tabs)
    app.get("/studio/partial/history")(handlers.get_history_tab)
    app.get("/studio/partial/export")(handlers.get_export_tab)

    # Async OCR API
    app.post("/api/run_ocr_async")(handlers.run_ocr_async)
    app.get("/api/check_ocr_status")(handlers.check_ocr_status)
    app.post("/api/restore_transcription")(handlers.restore_transcription)

    # Cropper & snippets
    app.get("/studio/cropper")(handlers.get_cropper)
    app.post("/api/save_snippet")(handlers.save_snippet_api)
    app.post("/api/save_transcription")(handlers.save_transcription)
    app.post("/api/studio/export/start")(handlers.start_studio_export)
    app.get("/api/studio/export/jobs")(handlers.get_studio_export_jobs)
    app.get("/api/studio/export/pdf_list")(handlers.get_studio_export_pdf_list)
    app.get("/api/studio/export/thumbs")(handlers.get_studio_export_thumbs)

    # Deletions
    app.delete("/api/delete_snippet/{snippet_id}")(handlers.delete_snippet)
