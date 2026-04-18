"""Discovery orchestration — public API and backward-compatible re-exports.

The actual per-provider search implementations live in ``resolvers.search.*``.
This module re-exports them so that existing callers (``providers.py``'s
``getattr(_disc, search_fn)`` and test files) continue to work unchanged.
"""

from __future__ import annotations

from typing import Any

import requests

from ..discovery.contracts import ProviderResolution
from ..discovery.orchestrator import resolve_provider_input as resolve_provider_input_orchestrated
from ..exceptions import ResolverError
from ..http_client import get_http_client
from ..logger import get_logger
from ..providers import IIIFProvider, get_provider, get_search_handlers
from .models import SearchResult
from .parsers import IIIFManifestParser
from .registry import resolve_shelfmark as registry_resolve
from .search import (  # noqa: F401 — re-exports for backward compatibility
    archive_manifest_is_usable,
    search_archive_org,
    search_bodleian,
    search_cambridge,
    search_ecodices,
    search_gallica,
    search_gallica_by_id,
    search_harvard,
    search_heidelberg,
    search_institut,
    search_internetculturale,
    search_loc,
    search_vatican,
)
from .search._common import TIMEOUT_SECONDS  # noqa: F401

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Orchestration layer
# ---------------------------------------------------------------------------


def smart_search(
    input_text: str, *, max_records: int = 20, page: int = 1, gallica_type_filter: str = "all"
) -> list[SearchResult]:
    """Main entry point — hybrid Gallica ID resolution + SRU text search."""
    text = (input_text or "").strip()
    if not text:
        return []

    gallica_resolver = get_provider("Gallica").resolver()

    if gallica_resolver.can_resolve(text):
        logger.info("Input '%s' riconosciuto come ID/URL Gallica.", text)
        manifest_url, doc_id = gallica_resolver.get_manifest_url(text)

        if manifest_url and doc_id:
            logger.info("Searching via SRU for document ID: %s", doc_id)
            results = search_gallica_by_id(doc_id)
            if results:
                results[0]["raw"] = results[0].get("raw", {})
                results[0]["raw"]["_is_direct_match"] = True
                return results
            else:
                logger.warning("No SRU results for ID: %s", doc_id)

    logger.info("Input '%s' interpretato come ricerca SRU.", text)
    return search_gallica(text, max_records=max_records, page=page, gallica_type_filter=gallica_type_filter)


def resolve_shelfmark(library: str, shelfmark: str) -> tuple[str | None, str | None]:
    """Resolve a shelfmark into (manifest_url, id) using the registry."""
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
    handler = get_search_handlers().get(provider.search_strategy or "")
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
        search_handlers=get_search_handlers(),
        resolve_shelfmark_fn=resolve_shelfmark,
        search_with_provider_fn=_search_with_provider,
    )


def get_manifest_details(manifest_url: str) -> SearchResult | None:
    """Fetch a manifest URL and return a parsed SearchResult or None."""
    url = (manifest_url or "").strip()
    if not url:
        return None

    manifest = get_http_client().get_json(url)
    if not manifest:
        return None

    try:
        doc_id = manifest.get("id") if isinstance(manifest, dict) else None
        return IIIFManifestParser.parse_manifest(manifest, url, doc_id=doc_id)
    except (ValueError, Exception) as exc:
        logger.error("Failed to parse manifest %r: %s", url, exc, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Backward-compatible private references used by test_search_vatican_unit etc.
# Tests access ``discovery._build_vatican_html_result`` via the module object.
# ---------------------------------------------------------------------------
from .search.vatican import _build_vatican_html_result as _build_vatican_html_result  # noqa: E402, F401

__all__ = [
    "ProviderResolution",
    "TIMEOUT_SECONDS",
    "archive_manifest_is_usable",
    "get_manifest_details",
    "resolve_provider_input",
    "resolve_shelfmark",
    "search_archive_org",
    "search_bodleian",
    "search_cambridge",
    "search_ecodices",
    "search_gallica",
    "search_gallica_by_id",
    "search_harvard",
    "search_heidelberg",
    "search_institut",
    "search_internetculturale",
    "search_loc",
    "search_vatican",
    "smart_search",
]
