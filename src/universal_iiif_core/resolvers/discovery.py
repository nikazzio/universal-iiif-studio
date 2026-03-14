from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree
from html import unescape
from json import JSONDecodeError
from typing import Any, Final
from urllib.parse import quote, urlencode

import requests

from ..discovery.contracts import ProviderResolution
from ..discovery.orchestrator import resolve_provider_input as resolve_provider_input_orchestrated
from ..discovery.search_adapters import build_search_strategy_handlers
from ..exceptions import ResolverError
from ..logger import get_logger
from ..providers import IIIFProvider
from ..utils import get_json
from .archive_org import ArchiveOrgResolver
from .ecodices import EcodicesResolver
from .gallica import GallicaResolver
from .institut import InstitutResolver
from .models import SearchResult
from .oxford import OxfordResolver
from .parsers import GallicaXMLParser, IIIFManifestParser
from .registry import resolve_shelfmark as registry_resolve

logger = get_logger(__name__)

# Constants
TIMEOUT_SECONDS: Final = 20
GALLICA_BASE_URL: Final = "https://gallica.bnf.fr/SRU"
ARCHIVE_ADVANCEDSEARCH_URL: Final = "https://archive.org/advancedsearch.php"
INSTITUT_SEARCH_URL: Final = "https://bibnum.institutdefrance.fr/records/default"
INSTITUT_VIEWER_URL: Final = "https://bibnum.institutdefrance.fr/viewer/{doc_id}"
BODLEIAN_SEARCH_URL: Final = "https://digital.bodleian.ox.ac.uk/search/"
ECODICES_SEARCH_URL: Final = "https://www.e-codices.unifr.ch/en/search/all"
VATICAN_HOME_URL: Final = "https://digi.vatlib.it/mss/"
VATICAN_SEARCH_URL: Final = "https://digi.vatlib.it/mss/search"
ARCHIVE_MANIFEST_PROBE_LIMIT: Final = 15

# Browser-like headers are required for several catalog/search surfaces that reject
# generic scripted requests with 403/500 responses.
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
_HTML_TAG_RE: Final = re.compile(r"<[^>]+>")
_SPACE_RE: Final = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT_RE: Final = re.compile(r"\s+([,;:!?])")
_SPACE_BEFORE_SINGLE_PERIOD_RE: Final = re.compile(r"(?<!\.)\s+\.(?!\.)")

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


def smart_search(input_text: str, *, gallica_type_filter: str = "all") -> list[SearchResult]:
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
    return search_gallica(text, gallica_type_filter=gallica_type_filter)


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
    except (requests.RequestException, requests.Timeout, ValueError, ResolverError) as exc:
        logger.error("Resolver crashed for %r/%r: %s", lib, s, exc, exc_info=True)
        return None, None


def _search_with_provider(
    provider: IIIFProvider,
    query: str,
    filters: dict[str, Any] | None = None,
) -> list[SearchResult]:
    text = (query or "").strip()
    if not text or not provider.supports_search():
        return []

    payload = dict(filters or {})
    handler = _SEARCH_STRATEGY_HANDLERS.get(provider.search_strategy or "")
    if not handler:
        return []
    return handler(text, payload)


def _try_provider_direct_resolution(provider: IIIFProvider, text: str) -> tuple[str | None, str | None]:
    resolver = provider.resolver()
    if not resolver.can_resolve(text):
        return None, None
    return resolve_shelfmark(provider.key, text)


def resolve_provider_input(
    library: str,
    user_input: str,
    *,
    filters: dict[str, Any] | None = None,
) -> ProviderResolution:
    """Resolve discovery input via the shared orchestrator module."""
    return resolve_provider_input_orchestrated(
        library,
        user_input,
        filters=filters,
        search_handlers=_SEARCH_STRATEGY_HANDLERS,
        resolve_shelfmark_fn=resolve_shelfmark,
        search_with_provider_fn=_search_with_provider,
    )


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


def search_gallica(query: str, max_records: int = 15, *, gallica_type_filter: str = "all") -> list[SearchResult]:
    """Search Gallica SRU and return parsed SearchResult entries.

    Network errors are logged here; parser returns structured results or
    raises parsing errors back to the caller which we convert to empty
    results to keep the public API stable.
    """
    if not (q := (query or "").strip()):
        return []

    # Keep SRU query broad, then apply local type filter from parsed dc:type values.
    clean_q = q.replace('"', "'")
    normalized_filter = _normalize_gallica_type_filter(gallica_type_filter)
    cql = f'dc.title all "{clean_q}"'
    requested_records = max(1, min(max_records, 50))
    fetch_records = 50 if normalized_filter != "all" else requested_records
    maximum_records = str(fetch_records)
    resolver = GallicaResolver()
    params = {
        "operation": "searchRetrieve",
        "version": "1.2",
        "query": cql,
        "maximumRecords": maximum_records,
        "startRecord": "1",
        "collapsing": "true",  # Raggruppa versioni simili
    }
    try:
        logger.debug("Searching Gallica SRU: %s (filter=%s)", cql, normalized_filter)
        resp = requests.get(GALLICA_BASE_URL, params=params, headers=REAL_BROWSER_HEADERS, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        results = GallicaXMLParser.parse_sru(resp.content, resolver)
    except (requests.RequestException, xml.etree.ElementTree.ParseError, ValueError) as exc:
        logger.error("Gallica search failed for cql '%s': %s", cql, exc, exc_info=True)
        return []

    if normalized_filter == "all":
        return results[:requested_records]

    filtered = [item for item in results if _matches_gallica_type_filter(item, normalized_filter)]
    return filtered[:requested_records]


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
    except (requests.RequestException, requests.Timeout) as exc:
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


def search_archive_org(query: str, max_results: int = 12) -> list[SearchResult]:
    """Search Internet Archive advancedsearch and return IIIF-ready results."""
    if not (q := (query or "").strip()):
        return []

    clean_q = q.replace('"', " ")
    requested_results = max(1, min(max_results, 20))
    fetch_rows = min(max(requested_results * 3, requested_results), 30)
    params = {
        "q": f"({clean_q}) AND mediatype:texts",
        "fl[]": ["identifier", "title", "creator", "date", "mediatype"],
        "rows": str(fetch_rows),
        "page": "1",
        "output": "json",
    }

    logger.debug("Searching Archive.org advancedsearch: %s", clean_q)
    payload = get_json(
        _build_archive_search_url(params),
        headers=HTML_BROWSER_HEADERS,
        retries=2,
    )
    if not isinstance(payload, dict):
        logger.error("Archive.org search failed for query '%s': empty/invalid payload", clean_q)
        return []

    docs = payload.get("response", {}).get("docs", [])
    resolver = ArchiveOrgResolver()
    results: list[SearchResult] = []
    manifest_probes = 0

    for doc in docs:
        manifest_url, doc_id, manifest_probes, should_stop = _resolve_archive_candidate(
            doc,
            resolver,
            manifest_probes,
        )
        if should_stop:
            break
        if not manifest_url or not doc_id or not isinstance(doc, dict):
            continue
        result = _build_archive_result(doc, doc_id=doc_id, manifest_url=manifest_url)
        results.append(result)
        if len(results) >= requested_results:
            break

    return results[:requested_results]


def search_bodleian(query: str, max_results: int = 12) -> list[SearchResult]:
    """Search Digital Bodleian using its JSON-LD search representation."""
    if not (q := (query or "").strip()):
        return []

    requested_results = max(1, min(max_results, 20))
    try:
        logger.debug("Searching Bodleian JSON-LD search surface: %s", q)
        response = requests.get(
            BODLEIAN_SEARCH_URL,
            params={"q": q},
            headers={**HTML_BROWSER_HEADERS, "Accept": "application/ld+json"},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, JSONDecodeError, ValueError) as exc:
        logger.error("Bodleian search failed for query '%s': %s", q, exc, exc_info=True)
        return []

    members = payload.get("member", [])
    resolver = OxfordResolver()
    results: list[SearchResult] = []

    for member in members:
        if not isinstance(member, dict):
            continue
        if result := _build_bodleian_result(member, resolver):
            results.append(result)
        if len(results) >= requested_results:
            break

    return results


def search_ecodices(query: str, max_results: int = 12) -> list[SearchResult]:
    """Search e-codices HTML results and map them to IIIF manifests."""
    if not (q := (query or "").strip()):
        return []

    requested_results = max(1, min(max_results, 20))
    try:
        logger.debug("Searching e-codices HTML search surface: %s", q)
        response = requests.get(
            ECODICES_SEARCH_URL,
            params={
                "sQueryString": q,
                "sSearchField": "fullText",
                "iResultsPerPage": str(requested_results),
                "sSortField": "score",
                "aSelectedFacets": "",
            },
            headers=HTML_BROWSER_HEADERS,
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except (requests.RequestException, requests.Timeout) as exc:
        logger.error("e-codices search failed for query '%s': %s", q, exc, exc_info=True)
        return []

    resolver = EcodicesResolver()
    results: list[SearchResult] = []
    for chunk in _ECODICES_RESULT_SPLIT_RE.split(response.text):
        if not chunk.strip():
            continue
        if result := _build_ecodices_result(chunk, resolver):
            results.append(result)
        if len(results) >= requested_results:
            break

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
        manifest = get_json(manifest_url)
        if not manifest:
            raise ValueError("Empty manifest")
    except (ValueError, Exception) as exc:
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


def _clean_html_text(value: str) -> str:
    no_tags = _HTML_TAG_RE.sub(" ", value or "")
    compact = _SPACE_RE.sub(" ", unescape(no_tags)).strip()
    compact = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", compact)
    return _SPACE_BEFORE_SINGLE_PERIOD_RE.sub(".", compact)


def _archive_scalar(value: Any) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "").strip()


def _archive_thumbnail_url(identifier: str) -> str:
    encoded = quote(f"{identifier}/__ia_thumb.jpg", safe="")
    return f"https://iiif.archive.org/image/iiif/2/{encoded}/full/180,/0/default.jpg"


def _archive_manifest_is_usable(manifest_url: str) -> bool:
    """Quickly validate Archive.org manifests before exposing them in search results."""
    payload = get_json(
        manifest_url,
        headers={**HTML_BROWSER_HEADERS, "Accept": "application/json"},
        retries=1,
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


def _resolve_archive_candidate(
    doc: Any,
    resolver: ArchiveOrgResolver,
    manifest_probes: int,
) -> tuple[str | None, str | None, int, bool]:
    if not isinstance(doc, dict):
        return None, None, manifest_probes, False
    identifier = str(doc.get("identifier") or "").strip()
    if not identifier:
        return None, None, manifest_probes, False

    manifest_url, doc_id = resolver.get_manifest_url(identifier)
    if not manifest_url or not doc_id:
        return None, None, manifest_probes, False
    if manifest_probes >= ARCHIVE_MANIFEST_PROBE_LIMIT:
        logger.debug("Archive.org manifest probe limit reached (%s)", ARCHIVE_MANIFEST_PROBE_LIMIT)
        return None, None, manifest_probes, True
    manifest_probes += 1
    if not _archive_manifest_is_usable(manifest_url):
        logger.debug("Skipping Archive.org result with unusable manifest: %s", manifest_url)
        return None, None, manifest_probes, False
    return manifest_url, doc_id, manifest_probes, False


def _build_archive_result(doc: dict[str, Any], *, doc_id: str, manifest_url: str) -> SearchResult:
    title = _archive_scalar(doc.get("title")) or doc_id
    author = _archive_scalar(doc.get("creator")) or "Autore sconosciuto"
    date = _archive_scalar(doc.get("date"))
    mediatype = _archive_scalar(doc.get("mediatype")) or "texts"
    thumb = _archive_thumbnail_url(doc_id)

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
    return result


def _first_text(values: Any) -> str:
    if isinstance(values, list):
        for value in values:
            clean = _clean_html_text(str(value or ""))
            if clean:
                return clean
        return ""
    return _clean_html_text(str(values or ""))


def _build_bodleian_result(member: dict[str, Any], resolver: OxfordResolver) -> SearchResult | None:
    viewer_url = str(member.get("id") or "").strip()
    manifest_url = str(member.get("manifest", {}).get("id") or "").strip()
    _, doc_id = resolver.get_manifest_url(viewer_url)
    if not manifest_url or not doc_id:
        return None

    display_fields = member.get("displayFields", {})
    if not isinstance(display_fields, dict):
        display_fields = {}

    title = _first_text(display_fields.get("title")) or _first_text(member.get("shelfmark")) or doc_id
    author = _first_text(display_fields.get("people")) or "Autore sconosciuto"
    date = _first_text(display_fields.get("dateStatement"))
    description = _first_text(display_fields.get("snippet"))
    if not description:
        surface_count = int(member.get("surfaceCount") or 0)
        if surface_count > 0:
            description = f"{surface_count} pagine"

    thumbnail = _first_bodleian_thumbnail(member.get("thumbnail"))
    result: SearchResult = {
        "id": doc_id,
        "title": title[:200],
        "author": author[:150],
        "description": description[:400],
        "publisher": "Bodleian Libraries",
        "manifest": manifest_url,
        "thumbnail": thumbnail,
        "thumb": thumbnail,
        "viewer_url": viewer_url,
        "library": "Bodleian",
        "raw": {"viewer_url": viewer_url},
    }
    if date:
        result["date"] = date[:100]
    return result


def _first_bodleian_thumbnail(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and item.get("id"):
                return str(item["id"]).strip()
    if isinstance(value, dict) and value.get("id"):
        return str(value["id"]).strip()
    return ""


def _build_ecodices_result(chunk: str, resolver: EcodicesResolver) -> SearchResult | None:
    facsimile_match = _ECODICES_FACSIMILE_RE.search(chunk)
    if not facsimile_match:
        return None

    viewer_url = facsimile_match.group("href")
    manifest_url, doc_id = resolver.get_manifest_url(viewer_url)
    if not manifest_url or not doc_id:
        return None

    title = _regex_group_text(_ECODICES_MS_TITLE_RE, chunk) or _regex_group_text(_ECODICES_TITLE_RE, chunk) or doc_id
    collection = _regex_group_text(_ECODICES_COLLECTION_RE, chunk)
    description = _regex_group_text(_ECODICES_SUMMARY_RE, chunk)
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


def _regex_group_text(pattern: re.Pattern[str], chunk: str) -> str:
    if not (match := pattern.search(chunk)):
        return ""
    return _clean_html_text(match.group("value"))


def _build_ecodices_thumbnail(chunk: str) -> str:
    if not (match := _ECODICES_IMAGE_RE.search(chunk)):
        return ""
    base = str(match.group("base") or "").strip().rstrip("/")
    path = str(match.group("path") or "").strip().lstrip("/")
    if not base or not path:
        return ""
    return f"{base}/{path}/full/180,/0/default.jpg"


def get_manifest_details(manifest_url: str) -> SearchResult | None:
    """Fetch a manifest URL and return a parsed SearchResult or None.

    All network errors are logged here; the parser focuses on data shape only.
    """
    url = (manifest_url or "").strip()
    if not url:
        return None

    try:
        manifest = get_json(url)
        if not manifest:
            raise ValueError("Empty manifest")

        # Attempt to find a document id from manifest or fallback to URL
        doc_id = manifest.get("id") if isinstance(manifest, dict) else None
        return IIIFManifestParser.parse_manifest(manifest, url, doc_id=doc_id)
    except (ValueError, Exception) as exc:
        logger.error("Failed to fetch/parse manifest %r: %s", url, exc, exc_info=True)
        return None


def search_vatican(query: str, max_results: int = 5) -> list[SearchResult]:
    """Search Vatican Library through a hybrid strategy.

    We first try direct shelfmark normalization and a few historical heuristics for
    common manuscript patterns. If that fails and the query looks like free text, we
    fall back to DigiVatLib's public manuscripts search flow.

    Args:
        query: User input (e.g., "1223", "Urb lat 1223", "Vat.gr.123", "dante")
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
    """Use DigiVatLib's public manuscripts search flow for free-text queries.

    The result page rejects cold requests from non-browser clients, so we first prime the
    session on the manuscripts landing page and then send the actual search with a referer.
    """
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

    title = _regex_group_text(_VATICAN_TITLE_RE, chunk) or doc_id
    description = _regex_group_text(_VATICAN_DETAIL_RE, chunk)
    thumb_rel = _regex_group_text(_VATICAN_THUMB_RE, chunk)
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


def _verify_vatican_manifest(manifest_url: str, ms_id: str, resolver) -> SearchResult | None:
    """Verify a Vatican manifest exists and return SearchResult if valid."""
    try:
        manifest = get_json(manifest_url)
        if not manifest:
            return None

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


_SEARCH_STRATEGY_HANDLERS: Final[dict[str, Any]] = build_search_strategy_handlers(
    smart_search_fn=smart_search,
    search_vatican_fn=search_vatican,
    search_institut_fn=search_institut,
    search_archive_org_fn=search_archive_org,
    search_bodleian_fn=search_bodleian,
    search_ecodices_fn=search_ecodices,
)


__all__ = [
    "ProviderResolution",
    "resolve_provider_input",
    "resolve_shelfmark",
    "search_gallica",
    "search_gallica_by_id",
    "search_institut",
    "search_vatican",
    "get_manifest_details",
    "search_archive_org",
    "search_bodleian",
    "search_ecodices",
    "smart_search",
    "TIMEOUT_SECONDS",
]
