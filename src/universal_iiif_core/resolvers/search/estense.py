"""Biblioteca Estense Digitale search via the Jarvis HATEOAS API.

Uses the Spring Data REST search endpoint
``findBySgttOrAutnOrPressmark`` which covers short title, author, and
pressmark fields in one call and returns paged results with
``totalElements`` / ``totalPages`` metadata.
"""

from __future__ import annotations

from typing import Any, Final
from urllib.parse import urlencode

from universal_iiif_core.logger import get_logger
from universal_iiif_core.resolvers.estense import (
    JARVIS_BASE,
    build_manifest_url,
    build_viewer_url,
)
from universal_iiif_core.resolvers.models import SearchResult

from ._common import DISCOVERY_TIMEOUT, REAL_BROWSER_HEADERS, get_search_http_client

logger = get_logger(__name__)

_SEARCH_ENDPOINT: Final = f"{JARVIS_BASE}/meta/culturalItems/search/findBySgttOrAutnOrPressmark"
_THUMBNAIL_PREFIX: Final = f"{JARVIS_BASE}/images/db/"


def _manifest_link(item: dict[str, Any], uuid: str) -> str:
    """Return the v2 manifest URL (trust the embedded link when present)."""
    link = (item.get("_links") or {}).get("manifest") or {}
    href = str(link.get("href") or "").strip()
    return href or build_manifest_url(uuid)


def _viewer_link(item: dict[str, Any], uuid: str) -> str:
    link = (item.get("_links") or {}).get("viewer_iiif") or {}
    href = str(link.get("href") or "").strip()
    return href or build_viewer_url(uuid)


def _thumbnail_link(item: dict[str, Any]) -> str:
    link = (item.get("_links") or {}).get("thumbnail") or {}
    href = str(link.get("href") or "").strip()
    return href


def _first_custom_metadata(item: dict[str, Any], key: str) -> str:
    """Extract a single value from the optional customMetadataList array."""
    for entry in item.get("customMetadataList") or []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("name") or "").strip().lower() == key.lower():
            value = entry.get("value")
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, list):
                for v in value:
                    if isinstance(v, str) and v.strip():
                        return v.strip()
    return ""


def _build_result(item: dict[str, Any]) -> SearchResult | None:
    uuid = str(item.get("uuid") or "").strip()
    if not uuid:
        return None

    sgtt = str(item.get("sgtt") or "").strip()
    autn = str(item.get("autn") or "").strip()
    pressmark = str(item.get("pressmark") or "").strip()
    description = _first_custom_metadata(item, "description") or _first_custom_metadata(item, "dcDescription")
    date = _first_custom_metadata(item, "date") or _first_custom_metadata(item, "dcDate")
    language = _first_custom_metadata(item, "language")

    title = sgtt or pressmark or uuid
    manifest_url = _manifest_link(item, uuid)
    viewer_url = _viewer_link(item, uuid)
    thumb = _thumbnail_link(item)

    return SearchResult(
        id=uuid,
        title=title,
        author=autn,
        date=date,
        description=description,
        language=language,
        library="Biblioteca Estense (Modena)",
        thumbnail=thumb,
        thumb=thumb,
        manifest=manifest_url,
        manifest_status="pending",
        viewer_url=viewer_url,
        raw={"uuid": uuid, "pressmark": pressmark, "sgtt": sgtt, "autn": autn},
    )


def search_estense(query: str, max_results: int = 20, page: int = 1) -> list[SearchResult]:
    """Search the Estense catalog by title / author / pressmark.

    Args:
        query: Free-text query, matched upstream with a "contains" semantic.
        max_results: Page size requested upstream (clamped to [1, 50]).
        page: 1-based page index.

    Returns:
        Parsed ``SearchResult`` list with a trailing ``_search_total_results``
        / ``_search_total_pages`` / ``_search_page`` block on the first item
        so the Discovery UI can render "Mostrati X di Y".
    """
    text = (query or "").strip()
    if not text:
        return []

    size = max(1, min(int(max_results), 50))
    page_idx = max(1, int(page)) - 1  # Spring Pageable is 0-based
    params = {"text": text, "size": str(size), "page": str(page_idx)}
    url = f"{_SEARCH_ENDPOINT}?{urlencode(params)}"

    try:
        resp = get_search_http_client().get(
            url,
            headers=REAL_BROWSER_HEADERS,
            timeout=DISCOVERY_TIMEOUT,
            library_name="estense",
            retries=2,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.error("Estense search failed for %r: %s", text, exc)
        return []

    try:
        payload = resp.json()
    except ValueError:
        logger.error("Estense search returned non-JSON payload for %r", text)
        return []

    embedded = payload.get("_embedded", {}) or {}
    items = embedded.get("culturalItems", []) or []
    page_meta = payload.get("page", {}) or {}

    results: list[SearchResult] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        parsed = _build_result(item)
        if parsed is not None:
            results.append(parsed)

    if results:
        total_elements = int(page_meta.get("totalElements") or 0)
        total_pages = int(page_meta.get("totalPages") or 0)
        raw = dict(results[0].get("raw") or {})
        raw["_search_total_results"] = total_elements
        raw["_search_total_pages"] = total_pages
        raw["_search_page"] = page_idx + 1
        results[0]["raw"] = raw

    logger.debug(
        "Estense search %r -> %d results (page %d of %d; total=%d)",
        text,
        len(results),
        page_idx + 1,
        int(page_meta.get("totalPages") or 0),
        int(page_meta.get("totalElements") or 0),
    )

    return results[:size]
