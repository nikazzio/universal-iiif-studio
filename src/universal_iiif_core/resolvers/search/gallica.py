"""Gallica (BnF) search via SRU API."""

from __future__ import annotations

import unicodedata
import xml.etree.ElementTree
from typing import Final

import requests

from universal_iiif_core.logger import get_logger
from universal_iiif_core.providers import get_provider
from universal_iiif_core.resolvers.models import SearchResult
from universal_iiif_core.resolvers.parsers import GallicaXMLParser

from ._common import DISCOVERY_TIMEOUT, REAL_BROWSER_HEADERS, get_search_http_client

logger = get_logger(__name__)

GALLICA_BASE_URL: Final = "https://gallica.bnf.fr/SRU"


def search_gallica_by_id(doc_id: str) -> list[SearchResult]:
    """Search Gallica SRU by document identifier (ARK ID)."""
    if not doc_id:
        return []

    cql = f'dc.identifier all "{doc_id}"'
    params = {
        "operation": "searchRetrieve",
        "version": "1.2",
        "query": cql,
        "maximumRecords": "5",
        "startRecord": "1",
    }

    try:
        logger.debug("Searching Gallica SRU by ID: %s", doc_id)
        resp = get_search_http_client().get(
            GALLICA_BASE_URL,
            params=params,
            headers=REAL_BROWSER_HEADERS,
            timeout=DISCOVERY_TIMEOUT,
            library_name="gallica",
        )
        resp.raise_for_status()

        resolver = get_provider("Gallica").resolver()
        return GallicaXMLParser.parse_sru(resp.content, resolver)

    except (requests.RequestException, xml.etree.ElementTree.ParseError, ValueError) as exc:
        logger.error("Gallica ID search failed for %s: %s", doc_id, exc, exc_info=True)
        return []


def _normalize_gallica_type_filter(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    if value in {"", "all", "any", "none"}:
        return "all"
    if value in {"manuscript", "manuscripts", "manuscrit"}:
        return "manuscrit"
    if value in {"print", "printed", "book", "books", "a_stampa", "stampa", "livre", "printed_book"}:
        return "printed"
    return "all"


def _normalize_match_text(value: str) -> str:
    lowered = str(value or "").strip().lower()
    return "".join(ch for ch in unicodedata.normalize("NFD", lowered) if unicodedata.category(ch) != "Mn")


def _matches_gallica_type_filter(item: SearchResult, normalized_filter: str) -> bool:
    if normalized_filter == "all":
        return True

    raw = item.get("raw")
    dc_types: list[str] = []
    if isinstance(raw, dict):
        raw_types = raw.get("dc_types")
        if isinstance(raw_types, list):
            dc_types = [str(v) for v in raw_types]

    types_text = " ".join(_normalize_match_text(v) for v in dc_types if v)
    if not types_text:
        types_text = " ".join(
            _normalize_match_text(str(item.get(key) or "")) for key in ("title", "description", "publisher")
        )

    manuscript_tokens = ("manuscrit", "manuscript")
    printed_tokens = ("monographie imprimee", "printed monograph", "imprime", "imprimee", "printed")

    if normalized_filter == "manuscrit":
        return any(token in types_text for token in manuscript_tokens)
    if normalized_filter == "printed":
        return any(token in types_text for token in printed_tokens)
    return True


def search_gallica(
    query: str, max_records: int = 20, *, page: int = 1, gallica_type_filter: str = "all"
) -> list[SearchResult]:
    """Search Gallica SRU and return parsed SearchResult entries."""
    if not (q := (query or "").strip()):
        return []

    clean_q = q.replace('"', "'")
    normalized_filter = _normalize_gallica_type_filter(gallica_type_filter)
    cql = f'dc.title all "{clean_q}"'
    requested_records = max(1, min(max_records, 50))
    fetch_records = 50 if normalized_filter != "all" else requested_records
    maximum_records = str(fetch_records)
    start_record = (max(1, page) - 1) * requested_records + 1
    resolver = get_provider("Gallica").resolver()
    params = {
        "operation": "searchRetrieve",
        "version": "1.2",
        "query": cql,
        "maximumRecords": maximum_records,
        "startRecord": str(start_record),
        "collapsing": "true",
    }
    try:
        logger.debug("Searching Gallica SRU: %s (filter=%s)", cql, normalized_filter)
        resp = get_search_http_client().get(
            GALLICA_BASE_URL,
            params=params,
            headers=REAL_BROWSER_HEADERS,
            timeout=DISCOVERY_TIMEOUT,
            library_name="gallica",
        )
        resp.raise_for_status()
        results = GallicaXMLParser.parse_sru(resp.content, resolver)
    except (requests.RequestException, xml.etree.ElementTree.ParseError, ValueError) as exc:
        logger.error("Gallica search failed for cql '%s': %s", cql, exc, exc_info=True)
        return []

    if normalized_filter == "all":
        return results[:requested_records]

    filtered = [item for item in results if _matches_gallica_type_filter(item, normalized_filter)]
    return filtered[:requested_records]
