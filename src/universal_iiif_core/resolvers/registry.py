from __future__ import annotations

from typing import Any, Final

from .gallica import GallicaResolver
from .generic import GenericResolver
from .institut import InstitutResolver
from .oxford import OxfordResolver
from .vatican import VaticanResolver


class ResolverRegistry:
    """Registry mapping library keywords to resolver classes.

    Keeps the keyword -> resolver mapping in one place and provides a
    clean lookup API instead of ad-hoc if/elif chains.
    """

    _MAP: Final = {
        "vatican": VaticanResolver,
        "gallica": GallicaResolver,
        "bnf": GallicaResolver,
        "institut": InstitutResolver,
        "bibnum": InstitutResolver,
        "oxford": OxfordResolver,
        "bodleian": OxfordResolver,
    }

    @classmethod
    def get_resolver_class(cls, library_name: str) -> Any:
        """Return the resolver class matching the provided library name."""
        name = (library_name or "").lower()
        for key, resolver in cls._MAP.items():
            if key in name:
                return resolver
        return GenericResolver


def resolve_shelfmark(library: str, shelfmark: str) -> tuple[str | None, str | None]:
    """Resolve a shelfmark to `(manifest_url, doc_id)` for a given library."""
    resolver_cls = ResolverRegistry.get_resolver_class(library)
    resolver = resolver_cls()
    return resolver.get_manifest_url((shelfmark or "").strip())


__all__ = ["ResolverRegistry", "resolve_shelfmark"]
