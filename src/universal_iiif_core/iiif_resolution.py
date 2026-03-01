from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import Any

import requests
from PIL import Image

from .logic.downloader import CanvasServiceLocator
from .utils import DEFAULT_HEADERS


def _manifest_canvases(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(manifest, dict):
        return []

    sequences = manifest.get("sequences")
    if isinstance(sequences, list) and sequences:
        first = sequences[0] or {}
        canvases = first.get("canvases")
        if isinstance(canvases, list):
            return [item for item in canvases if isinstance(item, dict)]

    items = manifest.get("items")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]

    return []


def _service_base_for_page(manifest: dict[str, Any], page_num_1_based: int) -> str | None:
    canvases = _manifest_canvases(manifest)
    idx = int(page_num_1_based) - 1
    if idx < 0 or idx >= len(canvases):
        return None
    return CanvasServiceLocator.locate(canvases[idx])


def probe_remote_max_dimensions(
    manifest: dict[str, Any],
    page_num_1_based: int,
    *,
    timeout_s: int = 12,
) -> tuple[int | None, int | None, str | None]:
    """Return `(width, height, service_base)` from remote IIIF info.json for one page."""
    base = _service_base_for_page(manifest, page_num_1_based)
    if not base:
        return None, None, None

    info_url = base.rstrip("/") + "/info.json"
    try:
        response = requests.get(info_url, headers=DEFAULT_HEADERS, timeout=max(3, int(timeout_s)))
        response.raise_for_status()
        payload = response.json() if response.content else {}
    except Exception:
        return None, None, base

    try:
        width = int(payload.get("width") or 0)
    except (TypeError, ValueError):
        width = 0

    try:
        height = int(payload.get("height") or 0)
    except (TypeError, ValueError):
        height = 0

    return (width or None), (height or None), base


def fetch_highres_page_image(
    manifest: dict[str, Any],
    page_num_1_based: int,
    out_path: Path,
    *,
    iiif_quality: str = "default",
    timeout_s: int = 45,
) -> tuple[bool, str]:
    """Download one page at `full/max` from IIIF and validate written image bytes."""
    base = _service_base_for_page(manifest, page_num_1_based)
    if not base:
        return False, "Servizio IIIF non disponibile per la pagina richiesta"

    quality = str(iiif_quality or "default").strip() or "default"
    image_url = f"{base.rstrip('/')}/full/max/0/{quality}.jpg"

    try:
        response = requests.get(
            image_url,
            headers=DEFAULT_HEADERS,
            timeout=max(8, int(timeout_s)),
            stream=True,
        )
        response.raise_for_status()

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)

        with Image.open(out_path) as img:
            img.verify()

        return True, "ok"
    except Exception as exc:
        if out_path.exists():
            with suppress(OSError):
                out_path.unlink()
        return False, str(exc)
