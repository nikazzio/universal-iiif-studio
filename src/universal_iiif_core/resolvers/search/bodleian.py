"""Digital Bodleian search."""

from __future__ import annotations

from json import JSONDecodeError
from typing import Any

import requests

from universal_iiif_core.logger import get_logger
from universal_iiif_core.providers import get_provider
from universal_iiif_core.resolvers.base import BaseResolver
from universal_iiif_core.resolvers.models import SearchResult

from ._common import DISCOVERY_TIMEOUT, HTML_BROWSER_HEADERS, first_text, get_search_http_client

logger = get_logger(__name__)

BODLEIAN_SEARCH_URL = "https://digital.bodleian.ox.ac.uk/search/"


def search_bodleian(query: str, max_results: int = 20, page: int = 1) -> list[SearchResult]:
    """Search Digital Bodleian using its JSON-LD search representation."""
    if not (q := (query or "").strip()):
        return []

    requested_results = max(1, min(max_results, 20))
    try:
        logger.debug("Searching Bodleian JSON-LD search surface: %s", q)
        response = get_search_http_client().get(
            BODLEIAN_SEARCH_URL,
            params={"q": q},
            headers={**HTML_BROWSER_HEADERS, "Accept": "application/ld+json"},
            timeout=DISCOVERY_TIMEOUT,
            library_name="bodleian",
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, JSONDecodeError, ValueError) as exc:
        logger.error("Bodleian search failed for query '%s': %s", q, exc, exc_info=True)
        return []

    members = payload.get("member", [])
    resolver = get_provider("Bodleian").resolver()
    results: list[SearchResult] = []

    for member in members:
        if not isinstance(member, dict):
            continue
        if result := _build_bodleian_result(member, resolver):
            results.append(result)
        if len(results) >= requested_results:
            break

    return results


def _build_bodleian_result(member: dict[str, Any], resolver: BaseResolver) -> SearchResult | None:
    viewer_url = str(member.get("id") or "").strip()
    manifest_url = str(member.get("manifest", {}).get("id") or "").strip()
    _, doc_id = resolver.get_manifest_url(viewer_url)
    if not manifest_url or not doc_id:
        return None

    display_fields = member.get("displayFields", {})
    if not isinstance(display_fields, dict):
        display_fields = {}

    title = first_text(display_fields.get("title")) or first_text(member.get("shelfmark")) or doc_id
    author = first_text(display_fields.get("people")) or "Autore sconosciuto"
    date = first_text(display_fields.get("dateStatement"))
    description = first_text(display_fields.get("snippet"))
    if not description:
        surface_count = int(member.get("surfaceCount") or 0)
        if surface_count > 0:
            description = f"{surface_count} pagine"

    thumbnail = _first_bodleian_thumbnail(member.get("thumbnail"))
    result: SearchResult = {
        "id": doc_id,
        "title": title[:200],
        "author": author[:150],
        "description": description[:400],
        "publisher": "Bodleian Libraries",
        "manifest": manifest_url,
        "thumbnail": thumbnail,
        "thumb": thumbnail,
        "viewer_url": viewer_url,
        "library": "Bodleian",
        "raw": {"viewer_url": viewer_url},
    }
    if date:
        result["date"] = date[:100]
    return result


def _first_bodleian_thumbnail(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and item.get("id"):
                return str(item["id"]).strip()
    if isinstance(value, dict) and value.get("id"):
        return str(value["id"]).strip()
    return ""
