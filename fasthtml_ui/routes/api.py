"""API Routes - Simple Manifest Serving.

Serves IIIF manifests with image URLs pointing to static /downloads/ directory.
No complex IIIF Image API - just plain static files.
"""

import json
from pathlib import Path
from urllib.parse import quote, unquote

from fasthtml.common import Request, Response

from iiif_downloader.logger import get_logger
from iiif_downloader.ocr.storage import OCRStorage

logger = get_logger(__name__)


def setup_api_routes(app):
    """Register API routes for manifest serving."""

    @app.get("/iiif/manifest/{library}/{doc_id}")
    def get_manifest(request: Request, library: str, doc_id: str):
        """Serve IIIF manifest with images pointing to /downloads/ static directory."""
        lib_raw = unquote(library)
        doc_raw = unquote(doc_id)
        base_url = f"{request.url.scheme}://{request.url.netloc}"

        logger.info(f"📖 Serving manifest: {lib_raw}/{doc_raw}")

        try:
            storage = OCRStorage()
            paths = storage.get_document_paths(doc_raw, lib_raw)
            manifest_path = Path(paths["manifest"])

            if not manifest_path.exists():
                logger.error(f"Manifest not found: {manifest_path}")
                return Response(
                    json.dumps({"error": "Manifest not found"}), status_code=404, media_type="application/json"
                )

            with manifest_path.open(encoding="utf-8") as f:
                manifest = json.load(f)

            # Rewrite image URLs to point to /downloads/
            lib_q = quote(lib_raw, safe="")
            doc_q = quote(doc_raw, safe="")

            # IIIF v2 (sequences)
            if "sequences" in manifest:
                for sequence in manifest["sequences"]:
                    for idx, canvas in enumerate(sequence.get("canvases", [])):
                        for image in canvas.get("images", []):
                            resource = image.get("resource", {})
                            if resource:
                                # Direct path to static file
                                img_url = f"{base_url}/downloads/{lib_q}/{doc_q}/scans/pag_{idx:04d}.jpg"
                                resource["@id"] = img_url
                                resource.pop("service", None)  # Remove IIIF service

            # IV v3 (items)
            if "items" in manifest:
                for idx, canvas in enumerate(manifest["items"]):
                    for annot_page in canvas.get("items", []):
                        for annot in annot_page.get("items", []):
                            body = annot.get("body", {})
                            if body:
                                img_url = f"{base_url}/downloads/{lib_q}/{doc_q}/scans/pag_{idx:04d}.jpg"
                                body["id"] = img_url
                                body.pop("service", None)

            total_canvases = len(manifest.get("sequences", [{}])[0].get("canvases", [])) if "sequences" in manifest else len(manifest.get("items", []))
            logger.info(f"✅ Served manifest for {doc_raw} ({total_canvases} pages)")

            return Response(
                json.dumps(manifest), media_type="application/json", headers={"Access-Control-Allow-Origin": "*"}
            )

        except Exception as e:
            logger.exception(f"❌ Error serving manifest: {e}")
            return Response(json.dumps({"error": str(e)}), status_code=500, media_type="application/json")
