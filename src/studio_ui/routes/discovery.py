"""Discovery route registration.

This module keeps a single responsibility: register the discovery routes using
top-level handlers defined in `studio_ui.routes.discovery_handlers`.
"""

from studio_ui.routes import discovery_handlers
from universal_iiif_core.logger import get_logger

logger = get_logger(__name__)


def setup_discovery_routes(app):
    """Register Discovery page routes.

    Args:
        app: FastHTML app instance
    """
    app.get("/discovery")(discovery_handlers.discovery_page)
    app.post("/api/resolve_manifest")(discovery_handlers.resolve_manifest)
    app.post("/api/start_download")(discovery_handlers.start_download)
    app.get("/api/download_status/{download_id}")(discovery_handlers.get_download_status)
    app.post("/api/cancel_download/{download_id}")(discovery_handlers.cancel_download)
