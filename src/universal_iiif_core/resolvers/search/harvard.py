"""Harvard Library search."""

from __future__ import annotations

import re
from typing import Any, Final
from urllib.parse import urlencode

from universal_iiif_core.http_client import get_http_client
from universal_iiif_core.logger import get_logger
from universal_iiif_core.resolvers.models import SearchResult

from ._common import HTML_BROWSER_HEADERS, clean_html_text

logger = get_logger(__name__)

HARVARD_API_URL: Final = "https://api.lib.harvard.edu/v2/items.json"

_HARVARD_IIIF_URL_RE: Final = re.compile(
    r"https://iiif\.lib\.harvard\.edu/manifests/(?:view/)?(?P<token>(?:drs|ids):\d+)",
    flags=re.IGNORECASE,
)
_HARVARD_PREVIEW_URL_RE: Final = re.compile(
    r"https://ids\.lib\.harvard\.edu/ids/iiif/[^\"'\s<>]+",
    flags=re.IGNORECASE,
)
_HARVARD_ALMA_CATALOG_URL_RE: Final = re.compile(
    r"https://id\.lib\.harvard\.edu/alma/(?P<id>\d+)/catalog",
    flags=re.IGNORECASE,
)


def search_harvard(query: str, max_results: int = 20, page: int = 1) -> list[SearchResult]:
    """Search Harvard metadata surface and extract IIIF manifest references when present."""
    if not (q := (query or "").strip()):
        return []

    requested_results = max(1, min(max_results, 20))
    api_limit = min(requested_results * 10, 100)
    start_offset = (max(1, page) - 1) * api_limit
    params = {"q": q, "limit": str(api_limit), "start": str(start_offset)}
    harvard_url = HARVARD_API_URL + "?" + urlencode(params)
    payload = get_http_client().get_json(harvard_url, headers=HTML_BROWSER_HEADERS, retries=2)
    collected = _extract_harvard_results(payload) if isinstance(payload, dict) else []

    if not any(str(item.get("manifest") or "").strip() for item in collected):
        enrichment_params = {"q": f"{q} iiif.lib.harvard.edu", "limit": str(min(requested_results * 10, 100))}
        enrichment_payload = get_http_client().get_json(
            HARVARD_API_URL + "?" + urlencode(enrichment_params),
            headers=HTML_BROWSER_HEADERS,
            retries=2,
        )
        if isinstance(enrichment_payload, dict):
            for item in _extract_harvard_results(enrichment_payload):
                if str(item.get("manifest") or "").strip():
                    collected.append(item)

    deduped: list[SearchResult] = []
    seen_ids: set[str] = set()
    for item in collected:
        doc_id = str(item.get("id") or "").strip().lower()
        if not doc_id or doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)
        deduped.append(item)
    return deduped


def _extract_harvard_manifest_tokens(payload: Any) -> list[str]:
    return list(dict.fromkeys(_HARVARD_IIIF_URL_RE.findall(str(payload))))


def _extract_harvard_results(payload: dict[str, Any]) -> list[SearchResult]:
    items = payload.get("items")
    if not isinstance(items, dict):
        return _build_generic_harvard_results(payload)
    mods = items.get("mods")
    if isinstance(mods, dict):
        mod_entries: list[dict[str, Any]] = [mods]
    elif isinstance(mods, list):
        mod_entries = [entry for entry in mods if isinstance(entry, dict)]
    else:
        mod_entries = []

    results: list[SearchResult] = []
    for mod in mod_entries:
        title = _extract_harvard_title(mod)
        preview = _extract_harvard_preview(mod)
        tokens = _extract_harvard_manifest_tokens(mod)
        catalog_url, catalog_id = _extract_harvard_catalog_reference(mod)
        for token in tokens:
            doc_id = token.lower()
            viewer_url = f"https://iiif.lib.harvard.edu/manifests/view/{doc_id}"
            results.append(
                {
                    "id": doc_id,
                    "title": title or f"Harvard item {doc_id}",
                    "author": "Autore sconosciuto",
                    "manifest": f"https://iiif.lib.harvard.edu/manifests/{doc_id}",
                    "thumbnail": preview,
                    "thumb": preview,
                    "viewer_url": viewer_url,
                    "library": "Harvard",
                    "raw": {"viewer_url": viewer_url},
                }
            )
        if tokens:
            continue
        if catalog_url and catalog_id:
            results.append(
                {
                    "id": catalog_id,
                    "title": title or f"Harvard record {catalog_id}",
                    "author": "Autore sconosciuto",
                    "thumbnail": preview,
                    "thumb": preview,
                    "viewer_url": catalog_url,
                    "library": "Harvard",
                    "raw": {
                        "viewer_url": catalog_url,
                        "consult_online_only": True,
                        "iiif_available": False,
                    },
                }
            )

    if results:
        return results
    return _build_generic_harvard_results(payload)


def _extract_harvard_title(mod: dict[str, Any]) -> str:
    title_info = mod.get("titleInfo")
    if isinstance(title_info, dict):
        title_info_entries: list[Any] = [title_info]
    elif isinstance(title_info, list):
        title_info_entries = title_info
    else:
        title_info_entries = []

    for entry in title_info_entries:
        if not isinstance(entry, dict):
            continue
        title = clean_html_text(str(entry.get("title") or ""))
        subtitle = clean_html_text(str(entry.get("subTitle") or ""))
        if title and subtitle:
            return f"{title}: {subtitle}"[:200]
        if title:
            return title[:200]
    return ""


def _extract_harvard_preview(mod: dict[str, Any]) -> str:
    match = _HARVARD_PREVIEW_URL_RE.search(str(mod))
    return str(match.group(0)).strip() if match else ""


def _extract_harvard_catalog_reference(mod: dict[str, Any]) -> tuple[str, str]:
    candidates = _harvard_location_url_candidates(mod)
    candidates.append(str(mod))
    for candidate in candidates:
        if match := _HARVARD_ALMA_CATALOG_URL_RE.search(candidate):
            viewer_url = str(match.group(0)).strip()
            record_id = str(match.group("id")).strip()
            if viewer_url and record_id:
                return viewer_url, record_id
    return "", ""


def _harvard_location_url_candidates(mod: dict[str, Any]) -> list[str]:
    location = mod.get("location")
    candidates: list[str] = []
    if isinstance(location, dict):
        location_urls = location.get("url")
        if isinstance(location_urls, str):
            candidates.append(location_urls)
        elif isinstance(location_urls, dict):
            candidates.append(str(location_urls.get("#text") or ""))
        elif isinstance(location_urls, list):
            for url_item in location_urls:
                if isinstance(url_item, str):
                    candidates.append(url_item)
                elif isinstance(url_item, dict):
                    candidates.append(str(url_item.get("#text") or ""))
    return candidates


def _build_generic_harvard_results(payload: Any) -> list[SearchResult]:
    results: list[SearchResult] = []
    for token in _extract_harvard_manifest_tokens(payload):
        doc_id = token.lower()
        viewer_url = f"https://iiif.lib.harvard.edu/manifests/view/{doc_id}"
        results.append(
            {
                "id": doc_id,
                "title": f"Harvard item {doc_id}",
                "author": "Autore sconosciuto",
                "manifest": f"https://iiif.lib.harvard.edu/manifests/{doc_id}",
                "thumbnail": "",
                "thumb": "",
                "viewer_url": viewer_url,
                "library": "Harvard",
                "raw": {"viewer_url": viewer_url},
            }
        )
    return results
