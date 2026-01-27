from pathlib import Path
from fasthtml.common import fast_app, serve
from starlette.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from fasthtml_ui.routes.api import setup_api_routes
from fasthtml_ui.routes.discovery import setup_discovery_routes
from fasthtml_ui.routes.studio import setup_studio_routes
from iiif_downloader.config_manager import get_config_manager
from iiif_downloader.logger import get_logger, setup_logging

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Initialize configuration
config = get_config_manager()

# Create FastHTML app
app, rt = fast_app(
    pico=False,  # Don't use PicoCSS
    hdrs=(
        # Additional headers if needed
    ),
)

# Setup static file serving
static_dir = Path(__file__).parent / "static"
assets_dir = Path(__file__).parent / "assets"
downloads_path = Path(__file__).parent / "downloads"

for d in [static_dir, assets_dir]:
    if not d.exists():
        d.mkdir(parents=True, exist_ok=True)

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/static", StaticFiles(directory="static"), name="static")

if downloads_path.exists():
    app.mount("/downloads", StaticFiles(directory=str(downloads_path)), name="downloads")
    logger.info(f"📂 Mounted downloads directory: {downloads_path}")


# Request Logging Middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log incoming requests."""
    async def dispatch(self, request, call_next):
        """Dispatch the request and log the response."""
        logger.info(f"🌐 [{request.method}] {request.url.path}")
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


# Root redirect
@app.get("/")
def index():
    """Redirect root to Studio."""
    from fasthtml.common import RedirectResponse

    return RedirectResponse(url="/studio")


# Health check
@app.get("/health")
def health():
    """Simple health check endpoint."""
    return {"status": "ok", "version": "0.6.0-fasthtml"}


if __name__ == "__main__":
    logger.info("🚀 Starting Universal IIIF Downloader - FastHTML Edition")
    logger.info(f"📍 Downloads directory: {config.get_downloads_dir()}")

    serve(
        port=8000, reload=True, reload_includes=["*.py", "*.html"], reload_excludes=["downloads/*", "data/*", "logs/*"]
    )
