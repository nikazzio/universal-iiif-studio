"""Vatican Library (DigiVatLib) search."""

from __future__ import annotations

import re
from typing import Any, Final

import requests

from universal_iiif_core.exceptions import ResolverError
from universal_iiif_core.http_client import get_http_client
from universal_iiif_core.logger import get_logger
from universal_iiif_core.providers import get_provider
from universal_iiif_core.resolvers.models import SearchResult

from ._common import HTML_BROWSER_HEADERS, TIMEOUT_SECONDS, regex_group_text

logger = get_logger(__name__)

VATICAN_HOME_URL: Final = "https://digi.vatlib.it/mss/"
VATICAN_SEARCH_URL: Final = "https://digi.vatlib.it/mss/search"

_VATICAN_RESULT_SPLIT_RE: Final = re.compile(
    r'<div class="row-search-result-record[^"]*">',
    flags=re.IGNORECASE,
)
_VATICAN_DOC_ID_RE: Final = re.compile(
    r'href="(?P<href>/mss/edition/(?P<id>MSS_[^"/?#]+))"',
    flags=re.IGNORECASE,
)
_VATICAN_TITLE_RE: Final = re.compile(
    r'class="link-search-result-record-view">(?P<value>.*?)</a>',
    flags=re.IGNORECASE | re.DOTALL,
)
_VATICAN_DETAIL_RE: Final = re.compile(
    r'<div class="title">(?P<value>.*?)</div>',
    flags=re.IGNORECASE | re.DOTALL,
)
_VATICAN_THUMB_RE: Final = re.compile(
    r'<img src="(?P<value>/pub/digit/[^"]+/cover/cover\.jpg)"',
    flags=re.IGNORECASE,
)

_VATICAN_NUMERIC_COLLECTIONS: Final[list[str]] = [
    "Urb.lat",
    "Vat.lat",
    "Pal.lat",
    "Reg.lat",
    "Barb.lat",
    "Vat.gr",
    "Pal.gr",
]
_VATICAN_TEXT_PREFIXES: Final[list[str]] = ["Urb.lat.", "Vat.lat.", "Pal.lat.", "Reg.lat.", "Barb.lat."]


def search_vatican(query: str, max_results: int = 5, page: int = 1) -> list[SearchResult]:
    """Search Vatican Library through a hybrid strategy."""
    from universal_iiif_core.resolvers.vatican import normalize_shelfmark

    normalized_query = (query or "").strip()
    if not normalized_query:
        return []

    resolver = get_provider("Vaticana").resolver()
    results: list[SearchResult] = []

    _append_normalized_candidate(results, normalized_query, resolver, normalize_shelfmark, max_results)
    if len(results) >= max_results:
        return results[:max_results]

    if normalized_query.isdigit():
        candidate_ids = _build_numeric_candidate_ids(normalized_query)
    else:
        candidate_ids = _build_text_candidate_ids(normalized_query)
    _append_candidate_results(results, candidate_ids, resolver, max_results)
    if len(results) >= max_results:
        return results[:max_results]

    if _query_can_use_vatican_text_search(normalized_query):
        official_results = _search_vatican_official_site(normalized_query, max_results=max_results - len(results))
        _append_unique_results(results, official_results, max_results)

    return results


def _append_normalized_candidate(results, query: str, resolver, normalize_shelfmark, max_results: int) -> None:
    if len(results) >= max_results:
        return
    try:
        normalized = normalize_shelfmark(query)
    except (ValueError, KeyError, ResolverError) as exc:
        logger.debug("Failed to normalize Vatican input %r: %s", query, exc, exc_info=True)
        return

    manifest_url = _build_vatican_manifest_url(normalized)
    if result := _verify_vatican_manifest(manifest_url, normalized, resolver):
        results.append(result)


def _build_numeric_candidate_ids(query: str) -> list[str]:
    return [f"MSS_{collection}.{query}" for collection in _VATICAN_NUMERIC_COLLECTIONS]


def _build_text_candidate_ids(query: str) -> list[str]:
    if _query_contains_known_prefix(query):
        return []
    if not (first_number := _extract_first_number(query)):
        return []
    return [f"MSS_{prefix}{first_number}" for prefix in _VATICAN_TEXT_PREFIXES]


def _query_contains_known_prefix(query: str) -> bool:
    compact_query = query.lower().replace(".", "").replace(" ", "")
    return any(prefix.lower().replace(".", "") in compact_query for prefix in _VATICAN_TEXT_PREFIXES)


def _extract_first_number(query: str) -> str | None:
    matches = re.findall(r"\d+", query)
    return matches[0] if matches else None


def _append_candidate_results(results, candidate_ids: list[str], resolver, max_results: int) -> None:
    for candidate_id in candidate_ids:
        if len(results) >= max_results:
            return
        manifest_url = _build_vatican_manifest_url(candidate_id)
        if result := _verify_vatican_manifest(manifest_url, candidate_id, resolver):
            results.append(result)


def _append_unique_results(results: list[SearchResult], incoming: list[SearchResult], max_results: int) -> None:
    seen_ids = {str(item.get("id") or "") for item in results}
    for item in incoming:
        item_id = str(item.get("id") or "")
        if not item_id or item_id in seen_ids:
            continue
        results.append(item)
        seen_ids.add(item_id)
        if len(results) >= max_results:
            return


def _build_vatican_manifest_url(ms_id: str) -> str:
    return f"https://digi.vatlib.it/iiif/{ms_id}/manifest.json"


def _query_can_use_vatican_text_search(query: str) -> bool:
    stripped = (query or "").strip()
    if not stripped:
        return False
    if stripped.isdigit():
        return False
    return not _query_contains_known_prefix(stripped)


def _search_vatican_official_site(query: str, max_results: int = 5) -> list[SearchResult]:
    """Use DigiVatLib's public manuscripts search flow for free-text queries."""
    if not (q := (query or "").strip()):
        return []

    try:
        with requests.Session() as session:
            session.get(VATICAN_HOME_URL, headers=HTML_BROWSER_HEADERS, timeout=TIMEOUT_SECONDS)
            response = session.get(
                VATICAN_SEARCH_URL,
                params={"k_f": "0", "k_v": q},
                headers={**HTML_BROWSER_HEADERS, "Referer": VATICAN_HOME_URL},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
    except (requests.RequestException, requests.Timeout) as exc:
        logger.debug("Vatican official search failed for query %r: %s", q, exc)
        return []

    results: list[SearchResult] = []
    for chunk in _VATICAN_RESULT_SPLIT_RE.split(response.text):
        if not chunk.strip():
            continue
        if result := _build_vatican_html_result(chunk):
            results.append(result)
        if len(results) >= max_results:
            break
    return results


def _build_vatican_html_result(chunk: str) -> SearchResult | None:
    if not (doc_match := _VATICAN_DOC_ID_RE.search(chunk)):
        return None

    doc_id = str(doc_match.group("id") or "").strip()
    if not doc_id:
        return None

    title = regex_group_text(_VATICAN_TITLE_RE, chunk) or doc_id
    description = regex_group_text(_VATICAN_DETAIL_RE, chunk)
    thumb_rel = regex_group_text(_VATICAN_THUMB_RE, chunk)
    thumb = f"https://digi.vatlib.it{thumb_rel}" if thumb_rel.startswith("/") else thumb_rel

    return {
        "id": doc_id,
        "title": title[:200],
        "author": "",
        "description": description[:500],
        "manifest": _build_vatican_manifest_url(doc_id),
        "thumbnail": thumb,
        "thumb": thumb,
        "viewer_url": f"https://digi.vatlib.it/view/{doc_id}",
        "library": "Vaticana",
        "raw": {"viewer_url": f"https://digi.vatlib.it/view/{doc_id}"},
    }


def _extract_label_str(label: Any, fallback: str = "") -> str:
    """Normalise a IIIF label (string, list, or v3 language map) to a plain string."""
    if isinstance(label, str):
        return label
    if isinstance(label, list):
        return str(label[0]) if label else fallback
    if isinstance(label, dict):
        for vals in label.values():
            if isinstance(vals, list) and vals:
                return str(vals[0])
            if isinstance(vals, str):
                return vals
    return fallback


def _verify_vatican_manifest(manifest_url: str, ms_id: str, resolver) -> SearchResult | None:
    """Verify a Vatican manifest exists and return SearchResult if valid."""
    try:
        response = get_http_client().get(manifest_url)
        if response.status_code == 404:
            return None
        response.raise_for_status()

        try:
            manifest = response.json()
        except ValueError:
            return None

        if not manifest:
            return None

        label = _extract_label_str(manifest.get("label", ms_id), fallback=ms_id)

        meta_map: dict[str, str] = {}
        for item in manifest.get("metadata", []):
            lbl = _extract_label_str(item.get("label", ""))
            val = item.get("value", "")
            if isinstance(val, dict):
                val = _extract_label_str(val)
            elif isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            if isinstance(lbl, str) and lbl:
                meta_map[lbl.lower()] = str(val)

        thumb = manifest.get("thumbnail", {})
        thumb_url = thumb.get("@id") if isinstance(thumb, dict) else None

        sequences = manifest.get("sequences", [])
        canvases = sequences[0].get("canvases", []) if sequences else []
        page_count = len(canvases)

        result: SearchResult = {
            "id": ms_id,
            "title": label,
            "author": meta_map.get("author", meta_map.get("contributor", "")),
            "date": meta_map.get("date", ""),
            "description": meta_map.get("description", f"{page_count} pagine"),
            "manifest": manifest_url,
            "thumbnail": thumb_url or "",
            "thumb": thumb_url or "",
            "viewer_url": f"https://digi.vatlib.it/view/{ms_id}",
            "library": "Vaticana",
            "language": meta_map.get("language", ""),
            "publisher": meta_map.get("publisher", meta_map.get("source", "")),
            "raw": {"page_count": page_count},
        }

        return result

    except (requests.RequestException, requests.Timeout) as exc:
        logger.debug("Vatican manifest check failed for %s: %s", ms_id, exc)
        return None
