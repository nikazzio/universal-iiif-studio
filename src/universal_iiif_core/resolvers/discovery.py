from __future__ import annotations

from typing import Final

import requests

from ..logger import get_logger
from .gallica import GallicaResolver
from .models import SearchResult
from .parsers import GallicaXMLParser, IIIFManifestParser
from .registry import resolve_shelfmark as registry_resolve

logger = get_logger(__name__)

# Constants
TIMEOUT_SECONDS: Final = 20
GALLICA_BASE_URL: Final = "https://gallica.bnf.fr/SRU"

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

    query = (query or "").strip()
    if not query:
        return []

    resolver = VaticanResolver()
    results: list[SearchResult] = []

    # 1. Prima prova a normalizzare direttamente (caso: input già valido)
    try:
        normalized = normalize_shelfmark(query)
        manifest_url = f"https://digi.vatlib.it/iiif/{normalized}/manifest.json"
        result = _verify_vatican_manifest(manifest_url, normalized, resolver)
        if result:
            results.append(result)
    except Exception:
        pass  # Input non è una segnatura valida, proviamo varianti

    # 2. Se l'input sembra un numero, genera varianti per fondi comuni
    if query.isdigit() and len(results) < max_results:
        collections = ["Urb.lat", "Vat.lat", "Pal.lat", "Reg.lat", "Barb.lat", "Vat.gr", "Pal.gr"]
        for coll in collections:
            if len(results) >= max_results:
                break
            ms_id = f"MSS_{coll}.{query}"
            manifest_url = f"https://digi.vatlib.it/iiif/{ms_id}/manifest.json"
            result = _verify_vatican_manifest(manifest_url, ms_id, resolver)
            if result:
                results.append(result)

    # 3. Se l'input contiene lettere, prova a interpretarlo come segnatura parziale
    if not query.isdigit() and len(results) < max_results:
        # Prova varianti con prefissi comuni
        prefixes = ["Urb.lat.", "Vat.lat.", "Pal.lat.", "Reg.lat.", "Barb.lat."]
        for prefix in prefixes:
            if len(results) >= max_results:
                break
            # Se query contiene già un pattern simile, skip
            if any(p.lower().replace(".", "") in query.lower().replace(".", " ").replace(".", "") for p in prefixes):
                break
            # Estrai numero se presente
            import re
            nums = re.findall(r"\d+", query)
            if nums:
                ms_id = f"MSS_{prefix}{nums[0]}"
                manifest_url = f"https://digi.vatlib.it/iiif/{ms_id}/manifest.json"
                result = _verify_vatican_manifest(manifest_url, ms_id, resolver)
                if result:
                    results.append(result)

    return results


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


__all__ = ["resolve_shelfmark", "search_gallica", "search_gallica_by_id", "search_vatican", "get_manifest_details", "smart_search", "TIMEOUT_SECONDS"]
