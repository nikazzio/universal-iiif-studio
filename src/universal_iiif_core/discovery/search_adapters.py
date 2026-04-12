from __future__ import annotations

from collections.abc import Callable
from typing import Any

from universal_iiif_core.resolvers.models import SearchResult

# Default used when max_results is not provided via config/payload.
_DEFAULT_MAX_RESULTS = 20

SearchWithLimitFn = Callable[[str, int, int], list[SearchResult]]
SmartSearchFn = Callable[..., list[SearchResult]]


def _max_results_from_payload(payload: dict[str, Any]) -> int:
    """Read max_results from the adapter payload, falling back to the default."""
    raw = payload.get("max_results")
    if raw is not None:
        try:
            return max(1, min(int(raw), 50))
        except (TypeError, ValueError):
            pass
    return _DEFAULT_MAX_RESULTS


def _page_from_payload(payload: dict[str, Any]) -> int:
    """Read page number from the adapter payload (1-based, default 1)."""
    raw = payload.get("page")
    if raw is not None:
        try:
            return max(1, int(raw))
        except (TypeError, ValueError):
            pass
    return 1


def _search_gallica_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    smart_search_fn: SmartSearchFn,
) -> list[SearchResult]:
    return smart_search_fn(
        query,
        max_records=_max_results_from_payload(_payload),
        page=_page_from_payload(_payload),
        gallica_type_filter=str(_payload.get("gallica_type") or "all"),
    )


def _search_vatican_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_vatican_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_vatican_fn(query, _max_results_from_payload(_payload), _page_from_payload(_payload))


def _search_institut_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_institut_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_institut_fn(query, _max_results_from_payload(_payload), _page_from_payload(_payload))


def _search_archive_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_archive_org_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_archive_org_fn(query, _max_results_from_payload(_payload), _page_from_payload(_payload))


def _search_bodleian_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_bodleian_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_bodleian_fn(query, _max_results_from_payload(_payload), _page_from_payload(_payload))


def _search_ecodices_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_ecodices_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_ecodices_fn(query, _max_results_from_payload(_payload), _page_from_payload(_payload))


def _search_cambridge_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_cambridge_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_cambridge_fn(query, _max_results_from_payload(_payload), _page_from_payload(_payload))


def _search_harvard_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_harvard_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_harvard_fn(query, _max_results_from_payload(_payload), _page_from_payload(_payload))


def _search_loc_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_loc_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_loc_fn(query, _max_results_from_payload(_payload), _page_from_payload(_payload))


def _search_heidelberg_provider(
    query: str,
    _payload: dict[str, Any],
    *,
    search_heidelberg_fn: SearchWithLimitFn,
) -> list[SearchResult]:
    return search_heidelberg_fn(query, _max_results_from_payload(_payload), _page_from_payload(_payload))


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
    """Build provider search strategy handlers from injected adapter callables.

    .. deprecated::
        Use :func:`universal_iiif_core.providers.get_search_handlers` instead.
        This function is retained for backward-compatible test injection only
        and will be removed when search functions are decomposed (#118).
    """
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
