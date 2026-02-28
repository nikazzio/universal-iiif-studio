from __future__ import annotations

import re
from html import unescape
from typing import Final

import requests

from ..logger import get_logger
from .gallica import GallicaResolver
from .institut import InstitutResolver
from .models import SearchResult
from .parsers import GallicaXMLParser, IIIFManifestParser
from .registry import resolve_shelfmark as registry_resolve

logger = get_logger(__name__)

# Constants
TIMEOUT_SECONDS: Final = 20
GALLICA_BASE_URL: Final = "https://gallica.bnf.fr/SRU"
INSTITUT_SEARCH_URL: Final = "https://bibnum.institutdefrance.fr/records/default"
INSTITUT_VIEWER_URL: Final = "https://bibnum.institutdefrance.fr/viewer/{doc_id}"

# HEADER REALI PER EVITARE IL BAN (Errore 500/403)
# Gallica blocca le richieste se non sembrano provenire da un browser.
REAL_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}
HTML_BROWSER_HEADERS = {
    **REAL_BROWSER_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_INSTITUT_RECORD_LINK_RE: Final = re.compile(
    r"<a[^>]+href=[\"'](?P<href>/records/item/(?P<id>\d+)[^\"']*)[\"'][^>]*>(?P<title>.*?)</a>",
    flags=re.IGNORECASE | re.DOTALL,
)
_HTML_TAG_RE: Final = re.compile(r"<[^>]+>")
_SPACE_RE: Final = re.compile(r"\s+")

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


def smart_search(input_text: str) -> list[SearchResult]:
    """PUNTO DI INGRESSO PRINCIPALE (Logica Ibrida).

    Logica:
    1. Pulisce l'input.
    2. Controlla se è un ID o URL valido (Gallica, Vatican, Oxford, ecc).
       Se SÌ -> Cerca tramite SRU con dc.identifier (più affidabile del manifest diretto).
    3. Se NO -> Esegue una ricerca testuale su Gallica (lista con N elementi).
    """
    text = (input_text or "").strip()
    if not text:
        return []

    # 1. TENTATIVO RISOLUZIONE DIRETTA (ID o LINK)
    # Usiamo il resolver Gallica specifico per catturare short ID (es. bpt6k...)
    gallica_resolver = GallicaResolver()

    # Se sembra un link/ID Gallica valido
    if gallica_resolver.can_resolve(text):
        logger.info("Input '%s' riconosciuto come ID/URL Gallica.", text)
        manifest_url, doc_id = gallica_resolver.get_manifest_url(text)

        if manifest_url and doc_id:
            # STRATEGIA ANTI-BAN: Invece di scaricare il manifest diretto (403),
            # usiamo la ricerca SRU per identifier che è l'API ufficiale
            logger.info("Searching via SRU for document ID: %s", doc_id)
            results = search_gallica_by_id(doc_id)
            if results:
                # Flagghiamo il primo risultato come match diretto
                results[0]["raw"] = results[0].get("raw", {})
                results[0]["raw"]["_is_direct_match"] = True
                return results
            else:
                logger.warning("No SRU results for ID: %s", doc_id)

    # Potresti aggiungere qui controlli per Vaticana/Oxford se vuoi supportarli nello stesso campo
    # ma per ora ci concentriamo su Gallica come richiesto.

    # 2. RICERCA TESTUALE (FALLBACK)
    logger.info("Input '%s' interpretato come ricerca SRU.", text)
    return search_gallica(text)


def resolve_shelfmark(library: str, shelfmark: str) -> tuple[str | None, str | None]:
    """Resolve a shelfmark into (manifest_url, id) using the registry.

    Errors are logged with exc_info at the service boundary.
    """
    s = (shelfmark or "").strip()
    lib = (library or "").strip()

    logger.debug("Resolving shelfmark for Library=%r input=%r", lib, s)

    try:
        manifest_url, doc_id = registry_resolve(lib, s)
        if manifest_url:
            logger.info("Resolved '%s' -> %s", s, manifest_url)
        else:
            logger.warning("No manifest for '%s' (lib=%s)", s, lib)
        return manifest_url, doc_id
    except Exception as exc:
        logger.error("Resolver crashed for %r/%r: %s", lib, s, exc, exc_info=True)
        return None, None


def search_gallica_by_id(doc_id: str) -> list[SearchResult]:
    """Search Gallica SRU by document identifier (ARK ID).

    This is more reliable than fetching the manifest directly as it uses
    the official SRU API instead of the IIIF endpoint which gets blocked.
    """
    if not doc_id:
        return []

    # Search by identifier field
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
        resp = requests.get(GALLICA_BASE_URL, params=params, headers=REAL_BROWSER_HEADERS, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()

        resolver = GallicaResolver()
        return GallicaXMLParser.parse_sru(resp.content, resolver)

    except Exception as exc:
        logger.error("Gallica ID search failed for %s: %s", doc_id, exc, exc_info=True)
        return []


def search_gallica(query: str, max_records: int = 15) -> list[SearchResult]:
    """Search Gallica SRU and return parsed SearchResult entries.

    Network errors are logged here; parser returns structured results or
    raises parsing errors back to the caller which we convert to empty
    results to keep the public API stable.
    """
    if not (q := (query or "").strip()):
        return []

    # FIX QUERY: Puliamo le virgolette per evitare errori SRU 500
    clean_q = q.replace('"', "'")

    # Cerca nel titolo e filtra per tipo 'manuscrit'
    cql = f'dc.title all "{clean_q}" and dc.type all "manuscrit"'

    params = {
        "operation": "searchRetrieve",
        "version": "1.2",
        "query": cql,
        "maximumRecords": str(min(max_records, 50)),
        "startRecord": "1",
        "collapsing": "true",  # Raggruppa versioni simili
    }

    try:
        logger.debug("Searching Gallica SRU: %s", cql)

        # FIX HEADERS: Usiamo quelli reali definiti in alto per evitare il ban
        resp = requests.get(GALLICA_BASE_URL, params=params, headers=REAL_BROWSER_HEADERS, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()

        # Delegate XML parsing to the parser module
        resolver = GallicaResolver()
        return GallicaXMLParser.parse_sru(resp.content, resolver)

    except Exception as exc:
        logger.error("Gallica search failed: %s", exc, exc_info=True)
        return []


def search_institut(query: str, max_results: int = 12) -> list[SearchResult]:
    """Search Institut de France (Bibnum) records page and return IIIF entries."""
    if not (q := (query or "").strip()):
        return []

    try:
        logger.debug("Searching Institut records: %s", q)
        response = requests.get(
            INSTITUT_SEARCH_URL,
            params={"search": q},
            headers=HTML_BROWSER_HEADERS,
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.error("Institut search failed: %s", exc, exc_info=True)
        return []

    candidates = _extract_institut_candidates(response.text, max_results=max_results)
    if not candidates:
        return []

    resolver = InstitutResolver()
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

        title = _clean_html_text(match.group("title")) or f"Document {doc_id}"
        candidates.append((doc_id, title))
        if len(candidates) >= max_results:
            break

    return candidates


def _fetch_institut_manifest_result(
    doc_id: str, fallback_title: str, resolver: InstitutResolver
) -> SearchResult | None:
    manifest_url, _ = resolver.get_manifest_url(doc_id)
    if not manifest_url:
        return None

    try:
        response = requests.get(manifest_url, headers=REAL_BROWSER_HEADERS, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        manifest = response.json()
    except Exception as exc:
        logger.debug("Institut manifest fetch failed for %s: %s", doc_id, exc, exc_info=True)
        return _fallback_institut_result(doc_id, fallback_title, manifest_url)

    parsed = IIIFManifestParser.parse_manifest(
        manifest,
        manifest_url,
        library="Institut de France",
        doc_id=doc_id,
    )
    if not parsed:
        return _fallback_institut_result(doc_id, fallback_title, manifest_url)

    if not parsed.get("title") or parsed.get("title") == doc_id:
        parsed["title"] = fallback_title
    parsed["library"] = "Institut de France"
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
        "library": "Institut de France",
        "raw": {"viewer_url": INSTITUT_VIEWER_URL.format(doc_id=doc_id)},
    }


def _clean_html_text(value: str) -> str:
    no_tags = _HTML_TAG_RE.sub(" ", value or "")
    return _SPACE_RE.sub(" ", unescape(no_tags)).strip()


def get_manifest_details(manifest_url: str) -> SearchResult | None:
    """Fetch a manifest URL and return a parsed SearchResult or None.

    All network errors are logged here; the parser focuses on data shape only.
    """
    url = (manifest_url or "").strip()
    if not url:
        return None

    try:
        # FIX HEADERS: Anche qui servono headers reali per scaricare il JSON
        resp = requests.get(url, headers=REAL_BROWSER_HEADERS, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        manifest = resp.json()

        # Attempt to find a document id from manifest or fallback to URL
        doc_id = manifest.get("id") if isinstance(manifest, dict) else None
        return IIIFManifestParser.parse_manifest(manifest, url, doc_id=doc_id)
    except Exception as exc:
        logger.error("Failed to fetch/parse manifest %r: %s", url, exc, exc_info=True)
        return None


def search_vatican(query: str, max_results: int = 5) -> list[SearchResult]:
    """Search Vatican Library by generating shelfmark variants.

    Since Vatican doesn't have a public search API, we try common shelfmark
    patterns and verify which manifests actually exist.

    Args:
        query: User input (e.g., "1223", "Urb lat 1223", "Vat.gr.123")
        max_results: Maximum number of results to return

    Returns:
        List of SearchResult for manifests that exist
    """
    from .vatican import VaticanResolver, normalize_shelfmark

    normalized_query = (query or "").strip()
    if not normalized_query:
        return []

    resolver = VaticanResolver()
    results: list[SearchResult] = []

    _append_normalized_candidate(results, normalized_query, resolver, normalize_shelfmark, max_results)
    if len(results) >= max_results:
        return results[:max_results]

    if normalized_query.isdigit():
        candidate_ids = _build_numeric_candidate_ids(normalized_query)
    else:
        candidate_ids = _build_text_candidate_ids(normalized_query)
    _append_candidate_results(results, candidate_ids, resolver, max_results)

    return results


def _append_normalized_candidate(results, query: str, resolver, normalize_shelfmark, max_results: int) -> None:
    if len(results) >= max_results:
        return
    try:
        normalized = normalize_shelfmark(query)
    except Exception as exc:
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


def _build_vatican_manifest_url(ms_id: str) -> str:
    return f"https://digi.vatlib.it/iiif/{ms_id}/manifest.json"


def _verify_vatican_manifest(manifest_url: str, ms_id: str, resolver) -> SearchResult | None:
    """Verify a Vatican manifest exists and return SearchResult if valid."""
    try:
        # Vatican doesn't support HEAD, use GET with short timeout
        resp = requests.get(manifest_url, headers=REAL_BROWSER_HEADERS, timeout=8)
        if resp.status_code != 200:
            return None

        manifest = resp.json()

        # Parse metadata
        label = manifest.get("label", ms_id)
        if isinstance(label, list):
            label = label[0] if label else ms_id

        # Extract metadata from manifest
        meta_map: dict[str, str] = {}
        for item in manifest.get("metadata", []):
            lbl = item.get("label", "")
            val = item.get("value", "")
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            meta_map[lbl.lower()] = str(val)

        thumb = manifest.get("thumbnail", {})
        thumb_url = thumb.get("@id") if isinstance(thumb, dict) else None

        # Count canvases
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
            "library": "Vaticana",
            "language": meta_map.get("language", ""),
            "publisher": meta_map.get("shelfmark", ms_id),
            "raw": {"page_count": page_count},
        }

        return result

    except Exception as exc:
        logger.debug("Vatican manifest check failed for %s: %s", ms_id, exc)
        return None


__all__ = [
    "resolve_shelfmark",
    "search_gallica",
    "search_gallica_by_id",
    "search_institut",
    "search_vatican",
    "get_manifest_details",
    "smart_search",
    "TIMEOUT_SECONDS",
]
