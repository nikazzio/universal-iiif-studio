"""Heidelberg University Library search."""

from __future__ import annotations

import re
from typing import Final
from urllib.parse import urlencode

import requests

from universal_iiif_core.logger import get_logger
from universal_iiif_core.providers import get_provider
from universal_iiif_core.resolvers.models import SearchResult

from ._common import DISCOVERY_TIMEOUT, HTML_BROWSER_HEADERS, get_search_http_client

logger = get_logger(__name__)

HEIDELBERG_SITE_SEARCH_URL: Final = "https://www.ub.uni-heidelberg.de/cgi-bin/search.cgi"

_HEIDELBERG_DIGILIT_LINK_RE: Final = re.compile(
    r"https://digi\.ub\.uni-heidelberg\.de/diglit/(?P<id>[a-z]{3}\d{2,})",
    flags=re.IGNORECASE,
)
_HEIDELBERG_INLINE_ID_RE: Final = re.compile(r"\b(?P<id>(?:cpg|cpl)\d{2,})\b", flags=re.IGNORECASE)


def search_heidelberg(query: str, max_results: int = 20, page: int = 1) -> list[SearchResult]:
    """Search Heidelberg website and map diglit hits to IIIF manifests when discoverable."""
    if not (q := (query or "").strip()):
        return []

    requested_results = max(1, min(max_results, 20))
    resolver = get_provider("Heidelberg").resolver()
    direct_manifest_url, direct_id = resolver.get_manifest_url(q)
    if direct_manifest_url and direct_id:
        viewer_url = f"https://digi.ub.uni-heidelberg.de/diglit/{direct_id}"
        return [
            {
                "id": direct_id,
                "title": direct_id,
                "author": "Autore sconosciuto",
                "manifest": direct_manifest_url,
                "thumbnail": "",
                "thumb": "",
                "viewer_url": viewer_url,
                "library": "Heidelberg",
                "raw": {"viewer_url": viewer_url},
            }
        ]
    if inline_match := _HEIDELBERG_INLINE_ID_RE.search(q):
        doc_id = inline_match.group("id").lower()
        manifest_url, resolved_id = resolver.get_manifest_url(doc_id)
        if manifest_url and resolved_id:
            viewer_url = f"https://digi.ub.uni-heidelberg.de/diglit/{resolved_id}"
            return [
                {
                    "id": resolved_id,
                    "title": resolved_id,
                    "author": "Autore sconosciuto",
                    "manifest": manifest_url,
                    "thumbnail": "",
                    "thumb": "",
                    "viewer_url": viewer_url,
                    "library": "Heidelberg",
                    "raw": {"viewer_url": viewer_url},
                }
            ]

    try:
        response = get_search_http_client().get(
            HEIDELBERG_SITE_SEARCH_URL,
            params={"query": q, "q": "homepage", "sprache": "ger", "wo": "w"},
            headers=HTML_BROWSER_HEADERS,
            timeout=DISCOVERY_TIMEOUT,
            library_name="heidelberg",
        )
        response.raise_for_status()
    except (requests.RequestException, requests.Timeout) as exc:
        logger.error("Heidelberg search failed for query '%s': %s", q, exc, exc_info=True)
        return [_build_heidelberg_browser_handoff_result(q)]

    seen_ids: set[str] = set()
    results: list[SearchResult] = []
    for match in _HEIDELBERG_DIGILIT_LINK_RE.finditer(response.text):
        doc_id = str(match.group("id") or "").lower()
        if not doc_id or doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)
        viewer_url = f"https://digi.ub.uni-heidelberg.de/diglit/{doc_id}"
        manifest_url, resolved_id = resolver.get_manifest_url(viewer_url)
        if not manifest_url or not resolved_id:
            continue
        results.append(
            {
                "id": resolved_id,
                "title": resolved_id,
                "author": "Autore sconosciuto",
                "manifest": manifest_url,
                "thumbnail": "",
                "thumb": "",
                "viewer_url": viewer_url,
                "library": "Heidelberg",
                "raw": {"viewer_url": viewer_url},
            }
        )
        if len(results) >= requested_results:
            break
    return results if results else [_build_heidelberg_browser_handoff_result(q)]


def _build_heidelberg_browser_handoff_result(query: str) -> SearchResult:
    search_url = (
        f"{HEIDELBERG_SITE_SEARCH_URL}?{urlencode({'query': query, 'q': 'homepage', 'sprache': 'ger', 'wo': 'w'})}"
    )
    return {
        "id": f"heidelberg-search:{query[:80]}",
        "title": "Apri la ricerca Heidelberg nel browser",
        "author": "",
        "description": (
            "Apri la ricerca Heidelberg con questa query, poi incolla qui ID o URL del record digitalizzato."
        ),
        "manifest": "",
        "thumbnail": "",
        "thumb": "",
        "viewer_url": search_url,
        "library": "Heidelberg",
        "raw": {
            "viewer_url": search_url,
            "consult_online_only": True,
        },
    }
