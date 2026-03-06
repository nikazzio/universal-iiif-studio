"""Library filters and query helpers."""

from __future__ import annotations

import json
from urllib.parse import urlencode

from fasthtml.common import A, Button, Details, Div, Form, Input, Option, P, Script, Select, Span, Summary

from studio_ui.common.library_constants import (
    ACTION_BUTTON_CLS,
    CATEGORY_LABELS,
    LINK_BUTTON_CLS,
    SORT_LABELS,
    STATE_STYLE,
)
from universal_iiif_core.library_catalog import ITEM_TYPES

_STATE_STYLE = STATE_STYLE
_CATEGORY_LABELS = CATEGORY_LABELS
_SORT_LABELS = SORT_LABELS
_ACTION_BUTTON_CLS = ACTION_BUTTON_CLS
_LINK_BUTTON_CLS = LINK_BUTTON_CLS


def _normalize_mode(mode: str | None, *, default_mode: str = "operativa") -> str:
    fallback = "archivio" if str(default_mode or "").strip().lower() == "archivio" else "operativa"
    value = str(mode or "").strip().lower()
    return value if value in {"operativa", "archivio"} else fallback


def _state_badge(state: str) -> Span:
    label, cls = _STATE_STYLE.get(
        (state or "saved").lower(),
        ("Remoto", "app-chip app-chip-neutral"),
    )
    return Span(label, cls=cls)


def _action_button(
    label: str,
    url: str,
    tone: str = "neutral",
    confirm: str | None = None,
    hint: str | None = None,
) -> Button:
    kwargs = {
        "cls": _ACTION_BUTTON_CLS[tone],
        "hx_post": url,
        "hx_target": "#library-page",
        "hx_swap": "outerHTML show:none",
        "hx_include": "#library-filters",
    }
    if confirm:
        kwargs["hx_confirm"] = confirm
    if hint:
        kwargs["title"] = hint
    return Button(label, **kwargs)


def _link_button(label: str, href: str, tone: str = "neutral", *, external: bool = False):
    if not href:
        return Span(label, cls=_LINK_BUTTON_CLS["muted"])
    kwargs = {"href": href, "cls": _LINK_BUTTON_CLS[tone]}
    if external:
        kwargs["target"] = "_blank"
        kwargs["rel"] = "noreferrer"
    return A(label, **kwargs)


def _state_counts(docs: list[dict]) -> dict[str, int]:
    out = {k: 0 for k in _STATE_STYLE}
    for doc in docs:
        key = str(doc.get("asset_state") or "saved").lower()
        out[key] = out.get(key, 0) + 1
    return out


def _kpi_strip(docs: list[dict]) -> Div:
    counts = _state_counts(docs)
    kpis = [
        ("Totale", len(docs), "text-slate-800 dark:text-slate-100"),
        ("Completi", counts.get("complete", 0), "text-slate-700 dark:text-slate-200"),
        ("Parziali", counts.get("partial", 0), "text-slate-700 dark:text-slate-200"),
        (
            "In coda",
            counts.get("queued", 0) + counts.get("downloading", 0) + counts.get("running", 0),
            "text-slate-700 dark:text-slate-200",
        ),
        ("Errori", counts.get("error", 0), "text-rose-600 dark:text-rose-300"),
        ("Remoti", counts.get("saved", 0), "text-slate-600 dark:text-slate-300"),
    ]
    cards = [
        Div(
            P(label, cls="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400"),
            P(str(value), cls=f"text-2xl font-bold {color}"),
            cls=(
                "rounded-xl border border-slate-200 dark:border-slate-700 "
                "bg-white dark:bg-slate-800/60 p-3 min-w-[110px]"
            ),
        )
        for label, value, color in kpis
    ]
    return Div(*cards, cls="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 mb-5")


def _library_query_params(
    *,
    view: str,
    q: str,
    state: str,
    library_filter: str,
    category: str,
    mode: str,
    default_mode: str,
    action_required: str,
    sort_by: str,
) -> dict[str, str]:
    params: dict[str, str] = {}
    if q:
        params["q"] = q
    if state:
        params["state"] = state
    if library_filter:
        params["library_filter"] = library_filter
    if category:
        params["category"] = category
    normalized_mode = _normalize_mode(mode, default_mode=default_mode)
    normalized_default_mode = _normalize_mode(default_mode, default_mode="operativa")
    if normalized_mode != normalized_default_mode:
        params["mode"] = normalized_mode
    if view and view != "grid":
        params["view"] = view
    if action_required and action_required != "0":
        params["action_required"] = action_required
    if sort_by:
        params["sort_by"] = sort_by
    return params


def _library_url_with_filters(**kwargs) -> str:
    query = urlencode(_library_query_params(**kwargs))
    return f"/library?{query}" if query else "/library"


def _render_mode_switch(
    *,
    view: str,
    q: str,
    state: str,
    library_filter: str,
    category: str,
    mode: str,
    default_mode: str,
    action_required: str,
    sort_by: str,
) -> Div:
    current_mode = _normalize_mode(mode, default_mode=default_mode)
    normalized_default_mode = _normalize_mode(default_mode, default_mode="operativa")

    operational_url = _library_url_with_filters(
        view=view,
        q=q,
        state=state,
        library_filter=library_filter,
        category=category,
        mode="operativa",
        default_mode=normalized_default_mode,
        action_required=action_required,
        sort_by=sort_by,
    )
    archive_url = _library_url_with_filters(
        view=view,
        q=q,
        state=state,
        library_filter=library_filter,
        category=category,
        mode="archivio",
        default_mode=normalized_default_mode,
        action_required=action_required,
        sort_by=sort_by,
    )
    operational_cls = (
        "app-btn app-btn-accent font-semibold" if current_mode == "operativa" else "app-btn app-btn-neutral"
    )
    archive_cls = "app-btn app-btn-accent font-semibold" if current_mode == "archivio" else "app-btn app-btn-neutral"

    return Div(
        A(
            "Vista Operativa",
            href=operational_url,
            hx_get=operational_url,
            hx_target="#library-page",
            hx_swap="outerHTML show:none",
            hx_push_url="true",
            cls=operational_cls,
        ),
        A(
            "Vista Archivio",
            href=archive_url,
            hx_get=archive_url,
            hx_target="#library-page",
            hx_swap="outerHTML show:none",
            hx_push_url="true",
            cls=archive_cls,
        ),
        cls="flex flex-wrap items-center justify-end gap-2",
    )


def _render_filters(
    *,
    view: str,
    q: str,
    state: str,
    library_filter: str,
    category: str,
    mode: str,
    default_mode: str,
    action_required: str,
    sort_by: str,
    libraries: list[str],
    categories: list[str],
) -> Details:
    current_state = (state or "").strip().lower()
    current_mode = _normalize_mode(mode, default_mode=default_mode)
    current_action_required = (action_required or "0").strip()
    normalized_default_mode = _normalize_mode(default_mode, default_mode="operativa")
    default_sort = "title_az" if current_mode == "archivio" else "priority"
    current_sort = (sort_by or "").strip() or default_sort
    category_options = categories or list(ITEM_TYPES)
    active_filters_count = 0
    if (q or "").strip():
        active_filters_count += 1
    if current_state:
        active_filters_count += 1
    if (library_filter or "").strip():
        active_filters_count += 1
    if (category or "").strip():
        active_filters_count += 1
    if current_sort != default_sort:
        active_filters_count += 1
    if (view or "grid") != "grid":
        active_filters_count += 1
    if current_action_required == "1":
        active_filters_count += 1
    if current_mode != normalized_default_mode:
        active_filters_count += 1

    return Details(
        Summary(
            Div(
                Span("Filtri", cls="text-sm font-semibold text-slate-800 dark:text-slate-100"),
                Span(
                    f"{active_filters_count} attivi" if active_filters_count > 0 else "Nessun filtro attivo",
                    cls="text-xs text-slate-500 dark:text-slate-400",
                ),
                cls="flex items-center justify-between gap-2",
            ),
            cls="cursor-pointer list-none px-3 py-2",
        ),
        Form(
            Div(
                Input(
                    type="text",
                    name="q",
                    value=q,
                    placeholder="Cerca per titolo, segnatura, reference, ID o biblioteca",
                    cls=(
                        "px-3 py-2.5 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 "
                        "rounded text-slate-800 dark:text-slate-100 text-sm flex-1 min-w-[240px]"
                    ),
                ),
                Button(
                    "Filtra",
                    cls="app-btn app-btn-primary",
                    type="submit",
                ),
                A(
                    "Reset",
                    href="/library",
                    hx_get="/library",
                    hx_target="#library-page",
                    hx_swap="outerHTML show:none",
                    hx_push_url="true",
                    id="library-reset-filters",
                    cls="app-btn app-btn-neutral",
                ),
                cls="flex flex-wrap gap-2",
            ),
            Div(
                Input(type="hidden", name="mode", value=current_mode),
                Select(
                    Option("Tutti gli stati", value=""),
                    Option("Remoto", value="saved", selected=current_state == "saved"),
                    Option("In coda", value="queued", selected=current_state == "queued"),
                    Option("In download", value="downloading", selected=current_state == "downloading"),
                    Option("Locale parziale", value="partial", selected=current_state == "partial"),
                    Option("Locale completo", value="complete", selected=current_state == "complete"),
                    Option("Errore", value="error", selected=current_state == "error"),
                    name="state",
                    cls=(
                        "px-3 py-2.5 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 "
                        "rounded text-slate-800 dark:text-slate-100 text-sm"
                    ),
                ),
                Select(
                    Option("Tutte le biblioteche", value=""),
                    *[Option(lib, value=lib, selected=library_filter == lib) for lib in libraries],
                    name="library_filter",
                    cls=(
                        "px-3 py-2.5 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 "
                        "rounded text-slate-800 dark:text-slate-100 text-sm"
                    ),
                ),
                Select(
                    Option("Tutte le categorie", value=""),
                    *[
                        Option(_CATEGORY_LABELS.get(cat, cat.title()), value=cat, selected=category == cat)
                        for cat in category_options
                    ],
                    name="category",
                    cls=(
                        "px-3 py-2.5 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 "
                        "rounded text-slate-800 dark:text-slate-100 text-sm"
                    ),
                ),
                Select(
                    *[Option(label, value=key, selected=current_sort == key) for key, label in _SORT_LABELS.items()],
                    name="sort_by",
                    cls=(
                        "px-3 py-2.5 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 "
                        "rounded text-slate-800 dark:text-slate-100 text-sm"
                    ),
                ),
                Select(
                    Option("Grid", value="grid", selected=view == "grid"),
                    Option("List", value="list", selected=view == "list"),
                    name="view",
                    cls=(
                        "px-3 py-2.5 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 "
                        "rounded text-slate-800 dark:text-slate-100 text-sm"
                    ),
                ),
                Select(
                    Option("Tutti gli elementi", value="0", selected=current_action_required != "1"),
                    Option("Solo elementi da gestire", value="1", selected=current_action_required == "1"),
                    name="action_required",
                    cls=(
                        "px-3 py-2.5 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 "
                        "rounded text-slate-800 dark:text-slate-100 text-sm"
                    ),
                ),
                cls="grid sm:grid-cols-2 xl:grid-cols-3 gap-2 mt-2",
            ),
            id="library-filters",
            hx_get="/library",
            hx_target="#library-page",
            hx_swap="outerHTML show:none",
            hx_push_url="true",
            hx_trigger="submit, change delay:200ms from:select, keyup changed delay:400ms from:input[name='q']",
            cls="px-3 pb-3",
        ),
        open=active_filters_count > 0,
        id="library-filters-panel",
        data_collapsible_key="filters",
        cls=("rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/30 mb-5"),
    )


def _library_filters_persistence_script(default_mode: str = "operativa") -> Script:
    safe_default_mode = "archivio" if str(default_mode or "").strip().lower() == "archivio" else "operativa"
    return Script(
        f"""
        (function () {{
            const STORAGE_KEY = 'ui.library.filters.v1';
            const DETAILS_STORAGE_KEY = 'ui.library.collapsible.v1';
            const DEFAULT_MODE = {json.dumps(safe_default_mode)};
            const FILTER_KEYS = [
                'q', 'state', 'library_filter', 'category', 'mode', 'view', 'action_required', 'sort_by'
            ];

            function defaultFilters() {{
                return {{
                    q: '',
                    state: '',
                    library_filter: '',
                    category: '',
                    mode: DEFAULT_MODE,
                    view: 'grid',
                    action_required: '0',
                    sort_by: ''
                }};
            }}

            function normalizeFilters(raw) {{
                const base = defaultFilters();
                const src = (raw && typeof raw === 'object') ? raw : {{}};
                FILTER_KEYS.forEach((key) => {{
                    base[key] = String(src[key] || '').trim();
                }});
                if (!base.mode) base.mode = DEFAULT_MODE;
                if (!base.view) base.view = 'grid';
                if (!base.action_required) base.action_required = '0';
                return base;
            }}

            function readSavedFilters() {{
                try {{
                    const raw = localStorage.getItem(STORAGE_KEY);
                    if (!raw) return null;
                    return normalizeFilters(JSON.parse(raw));
                }} catch (_e) {{
                    return null;
                }}
            }}

            function saveFilters(data) {{
                try {{
                    localStorage.setItem(STORAGE_KEY, JSON.stringify(normalizeFilters(data)));
                }} catch (_e) {{
                    /* ignore quota/storage errors */
                }}
            }}

            function clearSavedFilters() {{
                try {{
                    localStorage.removeItem(STORAGE_KEY);
                }} catch (_e) {{
                    /* ignore */
                }}
            }}

            function hasMeaningfulFilters(data) {{
                const f = normalizeFilters(data);
                return Boolean(
                    f.q ||
                    f.state ||
                    f.library_filter ||
                    f.category ||
                    f.sort_by ||
                    f.mode !== DEFAULT_MODE ||
                    f.view !== 'grid' ||
                    f.action_required !== '0'
                );
            }}

            function collectFormFilters(form) {{
                const payload = {{}};
                FILTER_KEYS.forEach((key) => {{
                    const input = form.querySelector('[name="' + key + '"]');
                    payload[key] = input ? String(input.value || '').trim() : '';
                }});
                return normalizeFilters(payload);
            }}

            function setFormFilters(form, data) {{
                const normalized = normalizeFilters(data);
                FILTER_KEYS.forEach((key) => {{
                    const input = form.querySelector('[name="' + key + '"]');
                    if (!input) return;
                    input.value = normalized[key];
                }});
            }}

            function urlHasFilterParams() {{
                try {{
                    const params = new URLSearchParams(window.location.search || '');
                    return FILTER_KEYS.some((key) => params.has(key));
                }} catch (_e) {{
                    return false;
                }}
            }}

            function filtersToQuery(data) {{
                const f = normalizeFilters(data);
                const params = new URLSearchParams();
                if (f.q) params.set('q', f.q);
                if (f.state) params.set('state', f.state);
                if (f.library_filter) params.set('library_filter', f.library_filter);
                if (f.category) params.set('category', f.category);
                if (f.sort_by) params.set('sort_by', f.sort_by);
                if (f.mode !== DEFAULT_MODE) params.set('mode', f.mode);
                if (f.view !== 'grid') params.set('view', f.view);
                if (f.action_required !== '0') params.set('action_required', f.action_required);
                return params.toString();
            }}

            function bindFormPersistence(form) {{
                if (!form || form.dataset.persistBound === '1') return;
                const persist = () => saveFilters(collectFormFilters(form));
                form.addEventListener('change', persist);
                form.addEventListener('submit', persist);
                form.dataset.persistBound = '1';
            }}

            function bindResetAction() {{
                const resetLink = document.getElementById('library-reset-filters');
                if (!resetLink || resetLink.dataset.resetBound === '1') return;
                resetLink.addEventListener('click', () => clearSavedFilters());
                resetLink.dataset.resetBound = '1';
            }}

            function readCollapsibleState() {{
                try {{
                    const raw = localStorage.getItem(DETAILS_STORAGE_KEY);
                    if (!raw) return {{}};
                    const parsed = JSON.parse(raw);
                    return parsed && typeof parsed === 'object' ? parsed : {{}};
                }} catch (_e) {{
                    return {{}};
                }}
            }}

            function saveCollapsibleState(state) {{
                try {{
                    localStorage.setItem(DETAILS_STORAGE_KEY, JSON.stringify(state || {{}}));
                }} catch (_e) {{
                    /* ignore storage errors */
                }}
            }}

            function bindCollapsiblePersistence() {{
                const nodes = document.querySelectorAll('details[data-collapsible-key]');
                if (!nodes || !nodes.length) return;
                const state = readCollapsibleState();
                nodes.forEach((el) => {{
                    const key = String(el.getAttribute('data-collapsible-key') || '').trim();
                    if (!key) return;
                    if (Object.prototype.hasOwnProperty.call(state, key)) {{
                        el.open = Boolean(state[key]);
                    }}
                    if (el.dataset.collapsibleBound === '1') return;
                    el.addEventListener('toggle', () => {{
                        const current = readCollapsibleState();
                        current[key] = Boolean(el.open);
                        saveCollapsibleState(current);
                    }});
                    el.dataset.collapsibleBound = '1';
                }});
            }}

            function restoreFiltersIfNeeded(form) {{
                if (urlHasFilterParams()) return false;
                const saved = readSavedFilters();
                if (!saved || !hasMeaningfulFilters(saved)) return false;
                const query = filtersToQuery(saved);
                if (!query) return false;

                setFormFilters(form, saved);
                saveFilters(saved);
                const url = '/library?' + query;
                try {{
                    window.history.replaceState(window.history.state, '', url);
                }} catch (_e) {{
                    /* ignore */
                }}

                if (window.htmx && typeof window.htmx.ajax === 'function') {{
                    window.htmx.ajax('GET', url, {{ target: '#library-page', swap: 'outerHTML show:none' }});
                    return true;
                }}
                window.location.href = url;
                return true;
            }}

            function initLibraryFiltersPersistence() {{
                bindCollapsiblePersistence();
                const form = document.getElementById('library-filters');
                if (form) {{
                    bindFormPersistence(form);
                    bindResetAction();
                    const restored = restoreFiltersIfNeeded(form);
                    if (!restored) {{
                        saveFilters(collectFormFilters(form));
                    }}
                }}
            }}

            if (!window.__libraryFiltersPersistenceBootstrapped) {{
                window.__libraryFiltersPersistenceBootstrapped = true;
                document.addEventListener('DOMContentLoaded', initLibraryFiltersPersistence);
                document.body.addEventListener('htmx:afterSwap', (event) => {{
                    const target = event && event.target;
                    if (!target) return;
                    if (target.id === 'app-main' || target.id === 'library-page') {{
                        initLibraryFiltersPersistence();
                    }}
                }});
            }}

            initLibraryFiltersPersistence();
        }})();
        """
    )
