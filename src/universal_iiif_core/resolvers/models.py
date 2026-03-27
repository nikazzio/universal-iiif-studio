from __future__ import annotations

from typing import Any, Final, TypedDict


class _DCData(TypedDict, total=False):
    title: str
    author: str
    date: str | None
    description: list[str]
    publisher: str | None
    language: str | None
    identifiers: list[str]
    types: list[str]


class SearchResult(TypedDict, total=False):
    """Canonical search result schema returned by discovery APIs.

    Keep this as the single source of truth for callers.
    """

    id: str
    title: str
    author: str
    date: str
    description: str
    publisher: str
    language: str
    thumbnail: str
    manifest: str
    manifest_status: str  # "ok" | "pending" | "unavailable"
    viewer_url: str
    library: str
    thumb: str
    ark: str
    raw: dict[str, Any]


__all__: Final = ["SearchResult", "_DCData"]
