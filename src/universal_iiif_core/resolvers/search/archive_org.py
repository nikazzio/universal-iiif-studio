"""Internet Archive (Archive.org) search."""

from __future__ import annotations

import re
from typing import Any, Final
from urllib.parse import quote, urlencode

from universal_iiif_core.http_client import get_http_client
from universal_iiif_core.logger import get_logger
from universal_iiif_core.providers import get_provider
from universal_iiif_core.resolvers.models import SearchResult

from ._common import _HTML_TAG_RE, _SPACE_RE, HTML_BROWSER_HEADERS

logger = get_logger(__name__)

ARCHIVE_ADVANCEDSEARCH_URL: Final = "https://archive.org/advancedsearch.php"
_ARCHIVE_VOLUME_RE: Final = re.compile(r"\b(?:v(?:ol(?:ume)?)?\.?|t(?:omo)?\.?)\s*(\d+)\b", flags=re.IGNORECASE)


def search_archive_org(query: str, max_results: int = 20, page: int = 1) -> list[SearchResult]:
    """Search Internet Archive advancedsearch and return IIIF-ready results."""
    if not (q := (query or "").strip()):
        return []

    clean_q = q.replace('"', " ")
    requested_results = max(1, min(max_results, 50))
    params = {
        "q": f"({clean_q}) AND mediatype:texts",
        "fl[]": ["identifier", "title", "creator", "date", "mediatype", "description", "volume", "language"],
        "rows": str(requested_results),
        "page": str(max(1, page)),
        "output": "json",
    }

    logger.debug("Searching Archive.org advancedsearch: %s", clean_q)
    payload = get_http_client().get_json(
        _build_archive_search_url(params),
        headers=HTML_BROWSER_HEADERS,
        retries=2,
    )
    if not isinstance(payload, dict):
        logger.error("Archive.org search failed for query '%s': empty/invalid payload", clean_q)
        return []

    docs = payload.get("response", {}).get("docs", [])
    resolver = get_provider("Archive.org").resolver()
    results: list[SearchResult] = []

    for doc in docs:
        if not isinstance(doc, dict):
            continue
        identifier = str(doc.get("identifier") or "").strip()
        if not identifier:
            continue
        manifest_url, doc_id = resolver.get_manifest_url(identifier)
        if not manifest_url or not doc_id:
            continue
        result = _build_archive_result(doc, doc_id=doc_id, manifest_url=manifest_url)
        result["manifest_status"] = "pending"
        results.append(result)
        if len(results) >= requested_results:
            break

    return results[:requested_results]


def archive_manifest_is_usable(manifest_url: str) -> bool:
    """Validate whether a IIIF manifest URL resolves to an actual manifest."""
    payload = get_http_client().get_json(
        manifest_url,
        headers={**HTML_BROWSER_HEADERS, "Accept": "application/json"},
        retries=0,
        timeout=(5, 8),
    )
    if payload is None:
        logger.debug("Archive.org manifest probe failed for %s: empty payload", manifest_url)
        return False

    if not isinstance(payload, dict):
        return False
    if payload.get("type") == "Manifest" or payload.get("@type") == "sc:Manifest":
        return True
    return "items" in payload or "sequences" in payload


def _build_archive_search_url(params: dict[str, Any]) -> str:
    query = urlencode(params, doseq=True)
    return f"{ARCHIVE_ADVANCEDSEARCH_URL}?{query}"


def _archive_scalar(value: Any) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "").strip()


def _archive_thumbnail_url(identifier: str) -> str:
    encoded = quote(f"{identifier}/__ia_thumb.jpg", safe="")
    return f"https://iiif.archive.org/image/iiif/2/{encoded}/full/180,/0/default.jpg"


def _archive_strip_description(raw: str) -> str:
    """Strip HTML tags and normalise whitespace from an Archive.org description."""
    text = _HTML_TAG_RE.sub(" ", raw)
    return _SPACE_RE.sub(" ", text).strip()


def _build_archive_result(doc: dict[str, Any], *, doc_id: str, manifest_url: str) -> SearchResult:
    title = _archive_scalar(doc.get("title")) or doc_id
    author = _archive_scalar(doc.get("creator")) or "Autore sconosciuto"
    date = _archive_scalar(doc.get("date"))
    mediatype = _archive_scalar(doc.get("mediatype")) or "texts"
    language = _archive_scalar(doc.get("language")) or ""
    thumb = _archive_thumbnail_url(doc_id)

    volume = _archive_scalar(doc.get("volume"))
    raw_desc = _archive_scalar(doc.get("description")) or ""
    description = _archive_strip_description(raw_desc)

    if not volume and description:
        vol_match = _ARCHIVE_VOLUME_RE.search(description)
        if vol_match:
            volume = vol_match.group(1)

    result: SearchResult = {
        "id": doc_id,
        "title": title[:200],
        "author": author[:100],
        "manifest": manifest_url,
        "thumbnail": thumb,
        "thumb": thumb,
        "viewer_url": f"https://archive.org/details/{doc_id}",
        "library": "Archive.org",
        "publisher": "Internet Archive",
        "raw": {
            "viewer_url": f"https://archive.org/details/{doc_id}",
            "mediatype": mediatype,
        },
    }
    if date:
        result["date"] = date[:100]
    if description:
        prefix = f"Vol. {volume} — " if volume else ""
        result["description"] = (prefix + description)[:220]
    if language:
        result["language"] = language[:40]
    return result
