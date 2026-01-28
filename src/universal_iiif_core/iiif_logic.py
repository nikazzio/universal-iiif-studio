"""IIIF manifest manipulation logic for core domain use.

Pure functions for rewriting embedded image URLs and counting canvases.
This module contains no UI or HTTP dependencies and may be imported by
the UI layer.
"""

from __future__ import annotations

from typing import Any


def _rewrite_v2_images(manifest: dict[str, Any], base_url: str, lib_q: str, doc_q: str) -> None:
    """Rewrite image `@id` values for IIIF v2-style manifests (sequences).

    Modifies `manifest` in-place.
    """
    if "sequences" not in manifest:
        return

    for sequence in manifest.get("sequences", []):
        canvases = sequence.get("canvases", [])
        for idx, canvas in enumerate(canvases):
            for image in canvas.get("images", []):
                resource = image.get("resource") or {}
                if not resource:
                    continue
                img_url = f"{base_url}/downloads/{lib_q}/{doc_q}/scans/pag_{idx:04d}.jpg"
                resource["@id"] = img_url
                resource.pop("service", None)


def _rewrite_v3_bodies(manifest: dict[str, Any], base_url: str, lib_q: str, doc_q: str) -> None:
    """Rewrite image `id` values for IIIF v3-style manifests (items).

    Modifies `manifest` in-place.
    """
    if "items" not in manifest:
        return

    for idx, canvas in enumerate(manifest.get("items", [])):
        for page in canvas.get("items", []):
            for annot in page.get("items", []):
                body = annot.get("body") or {}
                if not body:
                    continue
                img_url = f"{base_url}/downloads/{lib_q}/{doc_q}/scans/pag_{idx:04d}.jpg"
                body["id"] = img_url
                body.pop("service", None)


def rewrite_image_urls(manifest: dict[str, Any], base_url: str, lib_q: str, doc_q: str) -> None:
    """Rewrite any embedded image references to point to the local `downloads/`.

    This is a small wrapper that applies both v2 and v3 rewriting strategies.
    """
    _rewrite_v2_images(manifest, base_url, lib_q, doc_q)
    _rewrite_v3_bodies(manifest, base_url, lib_q, doc_q)


def total_canvases(manifest: dict[str, Any]) -> int:
    """Return the number of canvases/pages present in the manifest.

    Handles both IIIF v2 (sequences) and v3 (items).
    """
    if "sequences" in manifest:
        return len(manifest.get("sequences", [{}])[0].get("canvases", []))
    return len(manifest.get("items", []))
