"""API Routes - Simple Manifest Serving.

Serves IIIF manifests with image URLs rewritten to point at the local
`/downloads/` static directory. The heavy lifting for manifest parsing and
rewriting is delegated to small helpers in `api_helpers.py` so the route stays
concise and easy to lint.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote, unquote

from fasthtml.common import Request, Response
from starlette.responses import FileResponse

from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.logger import get_logger
from universal_iiif_core.services.ocr.storage import OCRStorage

from .api_helpers import load_manifest, rewrite_image_urls, total_canvases

logger = get_logger(__name__)


def serve_download_file(path: str) -> Response:
    """Serve files from the downloads directory."""
    logger.info("serve_download_file called with path: %s", path)
    config = get_config_manager()
    downloads_dir = config.get_downloads_dir()

    # Security: Resolve to absolute path and validate it's within downloads_dir
    try:
        requested_path = (downloads_dir / path).resolve()
        requested_path.relative_to(downloads_dir.resolve())
    except (ValueError, RuntimeError):
        logger.warning("Path traversal attempt blocked: %s", path)
        return Response("403 Forbidden", status_code=403)

    logger.info("Looking for file: %s (exists: %s)", requested_path, requested_path.exists())

    if not requested_path.exists():
        logger.warning("Download file not found: %s", requested_path)
        return Response("404 Not Found", status_code=404)

    # Determine content type
    suffix = requested_path.suffix.lower()
    content_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".json": "application/json",
        ".pdf": "application/pdf",
    }
    media_type = content_types.get(suffix, "application/octet-stream")

    logger.info("Serving file: %s as %s", requested_path, media_type)
    return FileResponse(
        str(requested_path),
        media_type=media_type,
        headers={"Access-Control-Allow-Origin": "*"},
    )


def get_manifest(request: Request, library: str, doc_id: str) -> Response:
    """Serve an on-disk manifest with image URLs rewritten to static files.

    The function is intentionally small: it validates the manifest path,
    loads the manifest via `load_manifest`, applies URL rewrites and returns
    a JSON response.
    """
    lib_raw = unquote(library)
    doc_raw = unquote(doc_id)
    base_url = f"{request.url.scheme}://{request.url.netloc}"

    logger.info("📖 Serving manifest: %s/%s", lib_raw, doc_raw)

    try:
        storage = OCRStorage()
        paths = storage.get_document_paths(doc_raw, lib_raw)
        manifest_path = Path(paths["manifest"])

        if not manifest_path.exists():
            logger.error("Manifest not found: %s", manifest_path)
            return Response('{"error": "Manifest not found"}', status_code=404, media_type="application/json")

        manifest = load_manifest(manifest_path)

        lib_q = quote(lib_raw, safe="")
        doc_q = quote(doc_raw, safe="")

        rewrite_image_urls(manifest, base_url, lib_q, doc_q)
        pages = total_canvases(manifest)

        logger.info("✅ Served manifest for %s (%d pages)", doc_raw, pages)

        return Response(
            content=__import__("json").dumps(manifest),
            media_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"},
        )

    except Exception as exc:  # pragma: no cover - route-level safety
        logger.exception("❌ Error serving manifest: %s", exc)
        return Response(
            content=__import__("json").dumps({"error": str(exc)}),
            status_code=500,
            media_type="application/json",
        )


def setup_api_routes(app) -> None:
    """Register API routes for manifest serving."""
    app.get("/downloads/{path:path}")(serve_download_file)
    app.get("/iiif/manifest/{library}/{doc_id}")(get_manifest)
