"""Cambridge University Digital Library search."""

from __future__ import annotations

import re
from typing import Final
from urllib.parse import urlencode

import requests

from universal_iiif_core.logger import get_logger
from universal_iiif_core.providers import get_provider
from universal_iiif_core.resolvers.models import SearchResult

from ._common import DISCOVERY_TIMEOUT, HTML_BROWSER_HEADERS, clean_html_text, get_search_http_client

logger = get_logger(__name__)

CAMBRIDGE_SEARCH_URL: Final = "https://cudl.lib.cam.ac.uk/search"

_CAMBRIDGE_VIEW_LINK_RE: Final = re.compile(
    r'<a[^>]+href=["\'](?P<href>(?:https://cudl\.lib\.cam\.ac\.uk)?/view/[^"\'?#]+)[^"\']*["\'][^>]*>(?P<title>.*?)</a>',
    flags=re.IGNORECASE | re.DOTALL,
)
_CAMBRIDGE_INLINE_ID_RE: Final = re.compile(r"\b(?P<id>[A-Z0-9]+(?:-[A-Z0-9]+){2,})\b")


def search_cambridge(query: str, max_results: int = 20, page: int = 1) -> list[SearchResult]:
    """Search Cambridge Digital Library and map viewer hits to IIIF manifests."""
    if not (q := (query or "").strip()):
        return []

    requested_results = max(1, min(max_results, 20))
    resolver = get_provider("Cambridge").resolver()
    direct_manifest_url, direct_id = resolver.get_manifest_url(q)
    if direct_manifest_url and direct_id:
        return [
            {
                "id": direct_id,
                "title": direct_id,
                "author": "Autore sconosciuto",
                "manifest": direct_manifest_url,
                "thumbnail": "",
                "thumb": "",
                "viewer_url": f"https://cudl.lib.cam.ac.uk/view/{direct_id}",
                "library": "Cambridge",
                "raw": {"viewer_url": f"https://cudl.lib.cam.ac.uk/view/{direct_id}"},
            }
        ]
    if inline_match := _CAMBRIDGE_INLINE_ID_RE.search(q.upper()):
        doc_id = inline_match.group("id")
        manifest_url, resolved_id = resolver.get_manifest_url(doc_id)
        if manifest_url and resolved_id:
            return [
                {
                    "id": resolved_id,
                    "title": resolved_id,
                    "author": "Autore sconosciuto",
                    "manifest": manifest_url,
                    "thumbnail": "",
                    "thumb": "",
                    "viewer_url": f"https://cudl.lib.cam.ac.uk/view/{resolved_id}",
                    "library": "Cambridge",
                    "raw": {"viewer_url": f"https://cudl.lib.cam.ac.uk/view/{resolved_id}"},
                }
            ]

    try:
        response = get_search_http_client().get(
            CAMBRIDGE_SEARCH_URL,
            params={"keyword": q},
            headers=HTML_BROWSER_HEADERS,
            timeout=DISCOVERY_TIMEOUT,
            library_name="cambridge",
        )
        if response.status_code == 202 and response.headers.get("x-amzn-waf-action") == "challenge":
            logger.warning("Cambridge search is blocked by WAF challenge in current environment.")
            return [_build_cambridge_browser_handoff_result(q)]
        response.raise_for_status()
    except (requests.RequestException, requests.Timeout) as exc:
        logger.error("Cambridge search failed for query '%s': %s", q, exc, exc_info=True)
        return [_build_cambridge_browser_handoff_result(q)]

    results: list[SearchResult] = []
    seen_ids: set[str] = set()
    for match in _CAMBRIDGE_VIEW_LINK_RE.finditer(response.text):
        href = str(match.group("href") or "").strip()
        viewer_url = href if href.startswith("http") else f"https://cudl.lib.cam.ac.uk{href}"
        manifest_url, doc_id = resolver.get_manifest_url(viewer_url)
        if not manifest_url or not doc_id or doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)
        title = clean_html_text(match.group("title")) or doc_id
        results.append(
            {
                "id": doc_id,
                "title": title[:200],
                "author": "Autore sconosciuto",
                "manifest": manifest_url,
                "thumbnail": "",
                "thumb": "",
                "viewer_url": viewer_url,
                "library": "Cambridge",
                "raw": {"viewer_url": viewer_url},
            }
        )
        if len(results) >= requested_results:
            break
    return results if results else [_build_cambridge_browser_handoff_result(q)]


def _build_cambridge_browser_handoff_result(query: str) -> SearchResult:
    search_url = f"{CAMBRIDGE_SEARCH_URL}?{urlencode({'keyword': query})}"
    return {
        "id": f"cambridge-search:{query[:80]}",
        "title": "Apri la ricerca Cambridge nel browser",
        "author": "",
        "description": (
            "La ricerca libera di Cambridge University Digital Library richiede il browser del sito. "
            "Apri la ricerca con questa query, poi incolla qui signature o URL del record."
        ),
        "manifest": "",
        "thumbnail": "",
        "thumb": "",
        "viewer_url": search_url,
        "library": "Cambridge",
        "raw": {
            "viewer_url": search_url,
            "consult_online_only": True,
        },
    }
