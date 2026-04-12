"""Institut de France (Bibnum) search."""

from __future__ import annotations

import re
from typing import Final

import requests

from universal_iiif_core.http_client import get_http_client
from universal_iiif_core.logger import get_logger
from universal_iiif_core.providers import get_provider
from universal_iiif_core.resolvers.base import BaseResolver
from universal_iiif_core.resolvers.models import SearchResult
from universal_iiif_core.resolvers.parsers import IIIFManifestParser

from ._common import DISCOVERY_TIMEOUT, HTML_BROWSER_HEADERS, clean_html_text, get_search_http_client

logger = get_logger(__name__)

INSTITUT_SEARCH_URL: Final = "https://bibnum.institutdefrance.fr/records/default"
INSTITUT_VIEWER_URL: Final = "https://bibnum.institutdefrance.fr/viewer/{doc_id}"

_INSTITUT_RECORD_LINK_RE: Final = re.compile(
    r"<a[^>]+href=[\"'](?P<href>/records/item/(?P<id>\d+)[^\"']*)[\"'][^>]*>(?P<title>.*?)</a>",
    flags=re.IGNORECASE | re.DOTALL,
)


def search_institut(query: str, max_results: int = 20, page: int = 1) -> list[SearchResult]:
    """Search Institut de France (Bibnum) records page and return IIIF entries."""
    if not (q := (query or "").strip()):
        return []

    try:
        logger.debug("Searching Institut records: %s", q)
        response = get_search_http_client().get(
            INSTITUT_SEARCH_URL,
            params={"search": q},
            headers=HTML_BROWSER_HEADERS,
            timeout=DISCOVERY_TIMEOUT,
            library_name="institut",
        )
        response.raise_for_status()
    except (requests.RequestException, requests.Timeout) as exc:
        logger.error("Institut search failed: %s", exc, exc_info=True)
        return []

    candidates = _extract_institut_candidates(response.text, max_results=max_results)
    if not candidates:
        return []

    resolver = get_provider("Institut de France").resolver()
    results: list[SearchResult] = []
    for doc_id, fallback_title in candidates:
        if len(results) >= max_results:
            break
        if result := _fetch_institut_manifest_result(doc_id, fallback_title, resolver):
            results.append(result)
    return results


def _extract_institut_candidates(html: str, max_results: int) -> list[tuple[str, str]]:
    """Extract unique `(doc_id, title)` candidates from Institut HTML search page."""
    candidates: list[tuple[str, str]] = []
    seen_ids: set[str] = set()

    for match in _INSTITUT_RECORD_LINK_RE.finditer(html):
        doc_id = match.group("id")
        if doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)

        title = clean_html_text(match.group("title")) or f"Document {doc_id}"
        candidates.append((doc_id, title))
        if len(candidates) >= max_results:
            break

    return candidates


def _fetch_institut_manifest_result(doc_id: str, fallback_title: str, resolver: BaseResolver) -> SearchResult | None:
    manifest_url, _ = resolver.get_manifest_url(doc_id)
    if not manifest_url:
        return None

    manifest = get_http_client().get_json(manifest_url)
    if not manifest:
        return _fallback_institut_result(doc_id, fallback_title, manifest_url)

    try:
        parsed = IIIFManifestParser.parse_manifest(
            manifest,
            manifest_url,
            library="Institut de France",
            doc_id=doc_id,
        )
    except ValueError as exc:
        logger.debug("Institut manifest parse failed for %s: %s", doc_id, exc, exc_info=True)
        return _fallback_institut_result(doc_id, fallback_title, manifest_url)

    if not parsed:
        return _fallback_institut_result(doc_id, fallback_title, manifest_url)

    if not parsed.get("title") or parsed.get("title") == doc_id:
        parsed["title"] = fallback_title
    parsed["library"] = "Institut de France"
    parsed["viewer_url"] = INSTITUT_VIEWER_URL.format(doc_id=doc_id)
    parsed.setdefault("raw", {})
    parsed["raw"]["viewer_url"] = INSTITUT_VIEWER_URL.format(doc_id=doc_id)
    return parsed


def _fallback_institut_result(doc_id: str, title: str, manifest_url: str) -> SearchResult:
    return {
        "id": doc_id,
        "title": title,
        "author": "Autore sconosciuto",
        "manifest": manifest_url,
        "thumbnail": "",
        "thumb": "",
        "viewer_url": INSTITUT_VIEWER_URL.format(doc_id=doc_id),
        "library": "Institut de France",
        "raw": {"viewer_url": INSTITUT_VIEWER_URL.format(doc_id=doc_id)},
    }
