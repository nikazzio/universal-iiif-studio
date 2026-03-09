from __future__ import annotations

import json
from contextlib import suppress
from pathlib import Path
from typing import Any

from PIL import Image

from .http_client import HTTPClient
from .logic.downloader import CanvasServiceLocator


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
    http_client: HTTPClient | None = None,
    library_name: str | None = None,
    timeout_s: int = 12,
) -> tuple[int | None, int | None, str | None]:
    """
    Return `(width, height, service_base)` from remote IIIF info.json for one page.
    
    If http_client is not provided, creates a temporary one with default settings.
    """
    base = _service_base_for_page(manifest, page_num_1_based)
    if not base:
        return None, None, None

    info_url = base.rstrip("/") + "/info.json"
    
    # Create temporary client if none provided
    if http_client is None:
        from .config_manager import get_config_manager
        cm = get_config_manager()
        http_client = HTTPClient(network_policy=cm.data.get("settings", {}))
    
    try:
        payload = http_client.get_json(info_url, library_name=library_name, timeout=max(3, int(timeout_s)))
        if not payload:
            return None, None, base
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
    http_client: HTTPClient | None = None,
    library_name: str | None = None,
    iiif_quality: str = "default",
    timeout_s: int = 45,
) -> tuple[bool, str]:
    """
    Download one page at `full/max` from IIIF and validate written image bytes.
    
    If http_client is not provided, creates a temporary one with default settings.
    """
    base = _service_base_for_page(manifest, page_num_1_based)
    if not base:
        return False, "Servizio IIIF non disponibile per la pagina richiesta"

    quality = str(iiif_quality or "default").strip() or "default"
    image_url = f"{base.rstrip('/')}/full/max/0/{quality}.jpg"

    # Create temporary client if none provided
    if http_client is None:
        from .config_manager import get_config_manager
        cm = get_config_manager()
        http_client = HTTPClient(network_policy=cm.data.get("settings", {}))

    try:
        response = http_client.get(
            image_url,
            library_name=library_name,
            timeout=max(8, int(timeout_s)),
        )
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}"

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("wb") as fh:
            fh.write(response.content)

        with Image.open(out_path) as img:
            img.verify()

        return True, "ok"
    except (json.JSONDecodeError, Exception) as exc:
        if out_path.exists():
            with suppress(OSError):
                out_path.unlink()
        return False, str(exc)
