from __future__ import annotations

from collections.abc import Callable
from typing import Any

from universal_iiif_core.providers import IIIFProvider, get_provider
from universal_iiif_core.resolvers.models import SearchResult

from .contracts import ProviderResolution

ProviderSearchHandler = Callable[[str, dict[str, Any]], list[SearchResult]]
ResolveShelfmarkFn = Callable[[str, str], tuple[str | None, str | None]]
ProviderSearchWithProviderFn = Callable[[IIIFProvider, str, dict[str, Any] | None], list[SearchResult]]


def _search_with_provider(
    provider: IIIFProvider,
    query: str,
    *,
    filters: dict[str, Any] | None,
    search_handlers: dict[str, ProviderSearchHandler],
) -> list[SearchResult]:
    text = (query or "").strip()
    if not text or not provider.supports_search():
        return []

    payload = dict(filters or {})
    handler = search_handlers.get(provider.search_strategy or "")
    if not handler:
        return []
    return handler(text, payload)


def _try_provider_direct_resolution(
    provider: IIIFProvider,
    text: str,
    *,
    resolve_shelfmark_fn: ResolveShelfmarkFn,
) -> tuple[str | None, str | None]:
    """Attempt direct resolution only when the provider explicitly claims the input."""
    resolver = provider.resolver()
    if not resolver.can_resolve(text):
        return None, None
    return resolve_shelfmark_fn(provider.key, text)


def resolve_provider_input(
    library: str,
    user_input: str,
    *,
    filters: dict[str, Any] | None = None,
    search_handlers: dict[str, ProviderSearchHandler],
    resolve_shelfmark_fn: ResolveShelfmarkFn,
    search_with_provider_fn: ProviderSearchWithProviderFn | None = None,
) -> ProviderResolution:
    """Resolve a discovery request through the provider registry."""
    text = (user_input or "").strip()
    provider = get_provider(library, fallback="Unknown")
    filter_payload = dict(filters or {})

    if not text:
        return ProviderResolution(provider=provider, status="not_found", not_found_hint=provider.not_found_hint)

    if provider.search_mode == "search_first" and provider.supports_search():
        if search_with_provider_fn:
            results = search_with_provider_fn(provider, text, filter_payload)
        else:
            results = _search_with_provider(provider, text, filters=filter_payload, search_handlers=search_handlers)
        if results:
            return ProviderResolution(provider=provider, status="results", results=results)
        manifest_url, doc_id = _try_provider_direct_resolution(
            provider,
            text,
            resolve_shelfmark_fn=resolve_shelfmark_fn,
        )
        if manifest_url:
            return ProviderResolution(
                provider=provider,
                status="manifest",
                manifest_url=manifest_url,
                doc_id=doc_id,
            )
        return ProviderResolution(provider=provider, status="not_found", not_found_hint=provider.not_found_hint)

    manifest_url, doc_id = _try_provider_direct_resolution(provider, text, resolve_shelfmark_fn=resolve_shelfmark_fn)
    if manifest_url:
        return ProviderResolution(provider=provider, status="manifest", manifest_url=manifest_url, doc_id=doc_id)

    if provider.supports_search():
        if search_with_provider_fn:
            results = search_with_provider_fn(provider, text, filter_payload)
        else:
            results = _search_with_provider(provider, text, filters=filter_payload, search_handlers=search_handlers)
        if results:
            return ProviderResolution(provider=provider, status="results", results=results)

    return ProviderResolution(provider=provider, status="not_found", not_found_hint=provider.not_found_hint)
