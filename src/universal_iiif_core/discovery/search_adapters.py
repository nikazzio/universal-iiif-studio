from __future__ import annotations

from collections.abc import Callable
from typing import Any

from universal_iiif_core.resolvers.models import SearchResult

SearchWithLimitFn = Callable[[str, int], list[SearchResult]]
SmartSearchFn = Callable[..., list[SearchResult]]


def _search_gallica_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    smart_search_fn: SmartSearchFn,
) -> list[SearchResult]:
    return smart_search_fn(query, gallica_type_filter=str(_payload.get("gallica_type") or "all"))


def _search_vatican_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_vatican_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_vatican_fn(query, 5)


def _search_institut_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_institut_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_institut_fn(query, 10)


def _search_archive_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_archive_org_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_archive_org_fn(query, 10)


def _search_bodleian_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_bodleian_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_bodleian_fn(query, 10)


def _search_ecodices_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_ecodices_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_ecodices_fn(query, 10)


def _search_cambridge_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_cambridge_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_cambridge_fn(query, 10)


def _search_harvard_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_harvard_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_harvard_fn(query, 10)


def _search_loc_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_loc_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_loc_fn(query, 10)


def _search_heidelberg_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_heidelberg_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_heidelberg_fn(query, 10)


def build_search_strategy_handlers(
    *,
    smart_search_fn: SmartSearchFn,
    search_vatican_fn: SearchWithLimitFn,
    search_institut_fn: SearchWithLimitFn,
    search_archive_org_fn: SearchWithLimitFn,
    search_bodleian_fn: SearchWithLimitFn,
    search_ecodices_fn: SearchWithLimitFn,
    search_cambridge_fn: SearchWithLimitFn,
    search_harvard_fn: SearchWithLimitFn,
    search_loc_fn: SearchWithLimitFn,
    search_heidelberg_fn: SearchWithLimitFn,
) -> dict[str, Callable[[str, dict[str, Any]], list[SearchResult]]]:
    """Build provider search strategy handlers from injected adapter callables."""
    return {
        "archive_org": lambda query, payload: _search_archive_provider(
            query,
            payload,
            search_archive_org_fn=search_archive_org_fn,
        ),
        "bodleian": lambda query, payload: _search_bodleian_provider(
            query,
            payload,
            search_bodleian_fn=search_bodleian_fn,
        ),
        "ecodices": lambda query, payload: _search_ecodices_provider(
            query,
            payload,
            search_ecodices_fn=search_ecodices_fn,
        ),
        "cambridge": lambda query, payload: _search_cambridge_provider(
            query,
            payload,
            search_cambridge_fn=search_cambridge_fn,
        ),
        "harvard": lambda query, payload: _search_harvard_provider(
            query,
            payload,
            search_harvard_fn=search_harvard_fn,
        ),
        "loc": lambda query, payload: _search_loc_provider(
            query,
            payload,
            search_loc_fn=search_loc_fn,
        ),
        "heidelberg": lambda query, payload: _search_heidelberg_provider(
            query,
            payload,
            search_heidelberg_fn=search_heidelberg_fn,
        ),
        "gallica": lambda query, payload: _search_gallica_provider(
            query,
            payload,
            smart_search_fn=smart_search_fn,
        ),
        "institut": lambda query, payload: _search_institut_provider(
            query,
            payload,
            search_institut_fn=search_institut_fn,
        ),
        "vatican": lambda query, payload: _search_vatican_provider(
            query,
            payload,
            search_vatican_fn=search_vatican_fn,
        ),
    }


__all__ = ["build_search_strategy_handlers"]
