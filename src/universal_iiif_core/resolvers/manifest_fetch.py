"""Centralized manifest-to-dict fetcher.

Handles both native IIIF JSON manifests and the ICCU MAG/XML endpoint, which
must be converted to a IIIF v2 dict before UI/library code can inspect it.
"""

from __future__ import annotations

from typing import Any

from ..http_client import get_http_client
from ..logger import get_logger
from .mag_parser import fetch_and_convert, is_iccu_magparser_url

logger = get_logger(__name__)


def fetch_manifest_dict(url: str, **kwargs: Any) -> dict[str, Any] | None:
    """Return a manifest as a dict regardless of the source format.

    - ICCU magparser URLs go through the MAG→IIIF v2 converter.
    - Everything else uses the shared HTTPClient JSON getter.

    Extra kwargs (e.g. ``retries``) are forwarded to ``get_json`` and ignored
    for the MAG path, which has its own retry-free synchronous fetch.
    """
    clean = str(url or "").strip()
    if not clean:
        return None

    if is_iccu_magparser_url(clean):
        try:
            return fetch_and_convert(clean)
        except Exception as exc:
            logger.debug("MAG→IIIF conversion failed for %s: %s", clean, exc)
            return None

    return get_http_client().get_json(clean, **kwargs)


__all__ = ["fetch_manifest_dict"]
