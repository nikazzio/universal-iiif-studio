from __future__ import annotations

from universal_iiif_core.providers import get_provider
from universal_iiif_core.resolvers.generic import GenericResolver


class ResolverRegistry:
    """Registry mapping library values to resolver classes."""

    @classmethod
    def get_resolver_class(cls, library_name: str):
        """Return the resolver class matching the provided library name."""
        provider = get_provider(library_name, fallback="Unknown")
        return provider.resolver_cls if provider.resolver_cls is not None else GenericResolver


def resolve_shelfmark(library: str, shelfmark: str) -> tuple[str | None, str | None]:
    """Resolve a shelfmark to `(manifest_url, doc_id)` for a given library."""
    resolver_cls = ResolverRegistry.get_resolver_class(library)
    resolver = resolver_cls()
    return resolver.get_manifest_url((shelfmark or "").strip())


__all__ = ["ResolverRegistry", "resolve_shelfmark"]
