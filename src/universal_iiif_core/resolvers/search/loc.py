"""Library of Congress search."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from universal_iiif_core.http_client import get_http_client
from universal_iiif_core.logger import get_logger
from universal_iiif_core.providers import get_provider
from universal_iiif_core.resolvers.models import SearchResult

from ._common import HTML_BROWSER_HEADERS, first_text

logger = get_logger(__name__)

LOC_SEARCH_URL = "https://www.loc.gov/search/"


def search_loc(query: str, max_results: int = 20, page: int = 1) -> list[SearchResult]:
    """Search Library of Congress JSON API and keep results that map to IIIF manifests."""
    if not (q := (query or "").strip()):
        return []

    requested_results = max(1, min(max_results, 20))
    params = {"q": q, "fo": "json", "sp": str(max(1, page)), "c": str(min(requested_results * 5, 100))}
    payload = get_http_client().get_json(_build_loc_search_url(params), headers=HTML_BROWSER_HEADERS, retries=2)
    if not isinstance(payload, dict):
        logger.error("LOC search failed for query '%s': empty/invalid payload", q)
        return []

    resolver = get_provider("Library of Congress").resolver()
    results: list[SearchResult] = []
    for entry in payload.get("results", []):
        if not isinstance(entry, dict):
            continue
        viewer_url = str(entry.get("id") or entry.get("url") or "").strip()
        if not viewer_url:
            continue
        manifest_url, doc_id = resolver.get_manifest_url(viewer_url)
        if not manifest_url or not doc_id:
            continue
        title = first_text(entry.get("title")) or doc_id
        thumbs = entry.get("image_url")
        thumbnail = str(thumbs[0]).strip() if isinstance(thumbs, list) and thumbs else ""
        results.append(
            {
                "id": doc_id,
                "title": title[:200],
                "author": "Autore sconosciuto",
                "manifest": manifest_url,
                "thumbnail": thumbnail,
                "thumb": thumbnail,
                "viewer_url": viewer_url,
                "library": "Library of Congress",
                "raw": {"viewer_url": viewer_url},
            }
        )
    return results


def _build_loc_search_url(params: dict[str, Any]) -> str:
    query = urlencode(params, doseq=True)
    return f"{LOC_SEARCH_URL}?{query}"
