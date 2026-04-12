"""e-codices search."""

from __future__ import annotations

import re
from typing import Final

import requests

from universal_iiif_core.logger import get_logger
from universal_iiif_core.providers import get_provider
from universal_iiif_core.resolvers.base import BaseResolver
from universal_iiif_core.resolvers.models import SearchResult

from ._common import DISCOVERY_TIMEOUT, HTML_BROWSER_HEADERS, get_search_http_client, regex_group_text

logger = get_logger(__name__)

ECODICES_SEARCH_URL: Final = "https://www.e-codices.unifr.ch/en/search/all"

_ECODICES_RESULT_SPLIT_RE: Final = re.compile(r'<div class="search-result">', flags=re.IGNORECASE)
_ECODICES_FACSIMILE_RE: Final = re.compile(
    r'<a href="(?P<href>https://www\.e-codices\.unifr\.ch/en/[a-z0-9]+/[a-z0-9._-]+)">Facsimile</a>',
    flags=re.IGNORECASE,
)
_ECODICES_COLLECTION_RE: Final = re.compile(
    r'<div class="collection-shelfmark">\s*(?P<value>.*?)\s*</div>',
    flags=re.IGNORECASE | re.DOTALL,
)
_ECODICES_TITLE_RE: Final = re.compile(
    r'<div class="document-headline">\s*(?P<value>.*?)\s*</div>',
    flags=re.IGNORECASE | re.DOTALL,
)
_ECODICES_MS_TITLE_RE: Final = re.compile(
    r'<div class="document-ms-title">\s*(?P<value>.*?)\s*</div>',
    flags=re.IGNORECASE | re.DOTALL,
)
_ECODICES_SUMMARY_RE: Final = re.compile(
    r'<p class="document-summary-search">\s*(?P<value>.*?)(?:<span class="summary-author"|</p>)',
    flags=re.IGNORECASE | re.DOTALL,
)
_ECODICES_IMAGE_RE: Final = re.compile(
    r'image-server-base-url="(?P<base>[^"]+)"\s+image-file-path="(?P<path>[^"]+)"',
    flags=re.IGNORECASE,
)


def search_ecodices(query: str, max_results: int = 20, page: int = 1) -> list[SearchResult]:
    """Search e-codices HTML results and map them to IIIF manifests."""
    if not (q := (query or "").strip()):
        return []

    requested_results = max(1, min(max_results, 20))
    try:
        logger.debug("Searching e-codices HTML search surface: %s", q)
        response = get_search_http_client().get(
            ECODICES_SEARCH_URL,
            params={
                "sQueryString": q,
                "sSearchField": "fullText",
                "iResultsPerPage": str(requested_results),
                "sSortField": "score",
                "aSelectedFacets": "",
            },
            headers=HTML_BROWSER_HEADERS,
            timeout=DISCOVERY_TIMEOUT,
            library_name="ecodices",
        )
        response.raise_for_status()
    except (requests.RequestException, requests.Timeout) as exc:
        logger.error("e-codices search failed for query '%s': %s", q, exc, exc_info=True)
        return []

    resolver = get_provider("e-codices").resolver()
    results: list[SearchResult] = []
    for chunk in _ECODICES_RESULT_SPLIT_RE.split(response.text):
        if not chunk.strip():
            continue
        if result := _build_ecodices_result(chunk, resolver):
            results.append(result)
        if len(results) >= requested_results:
            break

    return results


def _build_ecodices_result(chunk: str, resolver: BaseResolver) -> SearchResult | None:
    facsimile_match = _ECODICES_FACSIMILE_RE.search(chunk)
    if not facsimile_match:
        return None

    viewer_url = facsimile_match.group("href")
    manifest_url, doc_id = resolver.get_manifest_url(viewer_url)
    if not manifest_url or not doc_id:
        return None

    title = regex_group_text(_ECODICES_MS_TITLE_RE, chunk) or regex_group_text(_ECODICES_TITLE_RE, chunk) or doc_id
    collection = regex_group_text(_ECODICES_COLLECTION_RE, chunk)
    description = regex_group_text(_ECODICES_SUMMARY_RE, chunk)
    thumbnail = _build_ecodices_thumbnail(chunk)

    return {
        "id": doc_id,
        "title": title[:200],
        "author": "Autore sconosciuto",
        "description": description[:500],
        "publisher": collection[:200],
        "manifest": manifest_url,
        "thumbnail": thumbnail,
        "thumb": thumbnail,
        "viewer_url": viewer_url,
        "library": "e-codices",
        "raw": {"viewer_url": viewer_url},
    }


def _build_ecodices_thumbnail(chunk: str) -> str:
    if not (match := _ECODICES_IMAGE_RE.search(chunk)):
        return ""
    base = str(match.group("base") or "").strip().rstrip("/")
    path = str(match.group("path") or "").strip().lstrip("/")
    if not base or not path:
        return ""
    return f"{base}/{path}/full/180,/0/default.jpg"
