import threading
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fasthtml.common import RedirectResponse, fast_app, serve
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

from studio_ui.routes.api import setup_api_routes
from studio_ui.routes.discovery import setup_discovery_routes
from studio_ui.routes.settings import setup_settings_routes
from studio_ui.routes.studio import setup_studio_routes
from universal_iiif_core import __version__
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.logger import get_logger, setup_logging

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Initialize configuration
config = get_config_manager()


# On startup, reset any stale download jobs left as pending/running by previous process.
try:
    from universal_iiif_core.services.storage.vault_manager import VaultManager

    vm = VaultManager()
    reset_count = vm.reset_active_downloads()
    if reset_count:
        logger.info(f"Marked {reset_count} stale download job(s) as errored on startup")
except Exception:
    logger.debug("Failed to reset stale download jobs on startup", exc_info=True)


@asynccontextmanager
async def lifespan(app):
    """Gestione del ciclo di vita dell'app FastHTML."""
    # Startup: reset any stale DB jobs and kick off housekeeping in background
    try:
        from universal_iiif_core.services.storage.vault_manager import VaultManager

        def _housekeeping():
            try:
                vm2 = VaultManager()
                removed = vm2.cleanup_stale_data(retention_hours=24)
                if removed:
                    logger.info(f"Cleaned up {removed} stale download job(s) and temp data")
            except Exception:
                logger.debug("Housekeeping cleanup failed", exc_info=True)

        try:
            t = threading.Thread(target=_housekeeping, daemon=True)
            t.start()
        except Exception:
            logger.debug("Failed to schedule housekeeping thread", exc_info=True)
    except Exception:
        logger.debug("Housekeeping startup skipped (VaultManager unavailable)", exc_info=True)

    yield

    # Shutdown: nothing special to clean up for now
    return


# Create FastHTML app
app, rt = fast_app(
    pico=False,  # Don't use PicoCSS
    hdrs=(
        # Additional headers if needed
    ),
    lifespan=lifespan,
)

# Allow cross-origin requests for static assets (Mirador/OpenSeadragon image loads)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "HEAD"],
    allow_headers=["*"],
)

# Setup static file serving
BASE_DIR = Path(__file__).resolve().parent.parent
static_dir = BASE_DIR / "static"
assets_dir = BASE_DIR / "assets"
downloads_path = config.get_downloads_dir()
snippets_path = config.get_snippets_dir()

for d in [static_dir, assets_dir]:
    if not d.exists():
        d.mkdir(parents=True, exist_ok=True)

app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
# Mount snippets directory under the assets path so user-created snippets
# (stored in runtime `data/local/snippets`) are served at `/assets/snippets/...`.
app.mount("/assets/snippets", StaticFiles(directory=str(snippets_path)), name="assets_snippets")

# Ensure downloads directory exists and mount it
downloads_path.mkdir(parents=True, exist_ok=True)
app.mount("/downloads", StaticFiles(directory=str(downloads_path)), name="downloads")
logger.info(f"📂 Mounted downloads directory: {downloads_path}")


# Request Logging Middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log incoming requests."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Dispatch the request and log the response."""
        # Reduce noise: HTMX polling for download status is frequent; log at DEBUG.
        try:
            path = request.url.path or ""
        except Exception:
            path = ""

        if path.startswith("/api/download_status/") and request.method.upper() == "GET":
            logger.debug(f"Polling: [{request.method}] {path}")
        else:
            logger.info(f"🌐 [{request.method}] {path}")

        return await call_next(request)


app.add_middleware(LoggingMiddleware)

# Mount routes
logger.info("🔧 Setting up routes...")


# API routes (manifest serving) FIRST
setup_api_routes(app)


# Studio page routes
setup_studio_routes(app)

# Discovery page routes
setup_discovery_routes(app)

# Settings page routes
setup_settings_routes(app)


# Root redirect
@rt("/")
def index():
    """Redirect root to Studio."""
    return RedirectResponse(url="/studio")


# Health check
@rt("/health")
def health():
    """Simple health check endpoint."""
    return {"status": "ok", "version": __version__}


def main():
    """Punto di ingresso per il comando iiif-studio."""
    logger.info("🚀 Starting Universal IIIF Studio App (FastHTML + Mirador)")
    logger.info(f"📍 Downloads directory: {config.get_downloads_dir()}")

    # Nota: passiamo "studio_app:app" come stringa a serve() per
    # permettere il corretto funzionamento del reload automatico.
    serve(
        # app="studio_app:app",
        port=8000,
        reload=True,
        reload_includes=["*.py", "*.html"],
        reload_excludes=["downloads/*", "data/*", "logs/*"],
    )


if __name__ == "__main__":
    main()
