"""Library page components for local assets management."""

from __future__ import annotations

from fasthtml.common import H2, Div

from universal_iiif_core.library_catalog import ITEM_TYPES


def render_library_card(doc: dict, *, compact: bool = False) -> Div:
    """Render a single library card for targeted HTMX swaps."""
    from .library_cards import render_library_card as _render_library_card

    return _render_library_card(doc, compact=compact)


def render_library_page(
    docs: list[dict],
    *,
    view: str = "grid",
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "operativa",
    default_mode: str = "operativa",
    action_required: str = "0",
    sort_by: str = "",
    libraries: list[str] | None = None,
    categories: list[str] | None = None,
) -> Div:
    """Render the full Local Library page."""
    from .library_cards import _kpi_strip, _metadata_drawer, render_library_list
    from .library_filters import (
        _library_filters_persistence_script,
        _normalize_mode,
        _render_filters,
        _render_mode_switch,
    )

    libraries = libraries or []
    categories = categories or list(ITEM_TYPES)
    normalized_default_mode = _normalize_mode(default_mode, default_mode="operativa")
    current_mode = _normalize_mode(mode, default_mode=normalized_default_mode)

    return Div(
        Div(
            H2("Libreria Locale", cls="text-2xl font-bold text-slate-800 dark:text-slate-100"),
            _render_mode_switch(
                view=view,
                q=q,
                state=state,
                library_filter=library_filter,
                category=category,
                mode=current_mode,
                default_mode=normalized_default_mode,
                action_required=action_required,
                sort_by=sort_by,
            ),
            cls="flex items-center justify-between mb-4",
        ),
        _kpi_strip(docs),
        _render_filters(
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=current_mode,
            default_mode=normalized_default_mode,
            action_required=action_required,
            sort_by=sort_by,
            libraries=libraries,
            categories=categories,
        ),
        _library_filters_persistence_script(normalized_default_mode),
        render_library_list(docs, view=view, mode=current_mode),
        _metadata_drawer(),
        cls="p-6 max-w-7xl mx-auto",
        id="library-page",
    )


__all__ = ["render_library_card", "render_library_page"]
