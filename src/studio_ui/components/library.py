"""Library page components for local assets management."""

from __future__ import annotations

import base64
import json
from collections import OrderedDict
from urllib.parse import quote

from fasthtml.common import H2, H3, A, Button, Details, Div, Form, Img, Input, Option, P, Script, Select, Span, Summary

from universal_iiif_core.library_catalog import ITEM_TYPES

_STATE_STYLE = {
    "saved": ("Da scaricare", "app-chip app-chip-neutral"),
    "queued": ("In coda", "app-chip app-chip-accent"),
    "downloading": ("Download", "app-chip app-chip-primary"),
    "running": ("Download", "app-chip app-chip-primary"),
    "partial": ("Parziale", "app-chip app-chip-warning"),
    "complete": ("Completo", "app-chip app-chip-success"),
    "error": ("Errore", "app-chip app-chip-danger"),
}
_CATEGORY_LABELS = {
    "manoscritto": "Manoscritto",
    "libro a stampa": "Libro a stampa",
    "incunabolo": "Incunabolo",
    "periodico": "Periodico",
    "musica/spartito": "Musica/Spartito",
    "mappa/atlante": "Mappa/Atlante",
    "miscellanea": "Miscellanea",
    "non classificato": "Non classificato",
}
_SORT_LABELS = {
    "priority": "Priorita operativa",
    "recent": "Aggiornati di recente",
    "title_az": "Titolo A-Z",
    "pages_desc": "Piu pagine",
}
_ACTION_BUTTON_CLS = {
    "primary": "app-btn app-btn-primary",
    "success": "app-btn app-btn-primary",
    "accent": "app-btn app-btn-accent",
    "danger": "app-btn app-btn-danger",
    "warning": "app-btn app-btn-accent",
    "neutral": "app-btn app-btn-neutral",
    "info": "app-btn app-btn-info",
    "auto": "app-btn app-btn-accent",
}
_LINK_BUTTON_CLS = {
    "primary": "app-btn app-btn-primary",
    "neutral": "app-btn app-btn-neutral",
    "external": "app-btn app-btn-accent",
    "muted": "app-btn app-btn-muted",
}


def _state_badge(state: str) -> Span:
    label, cls = _STATE_STYLE.get(
        (state or "saved").lower(),
        ("Da scaricare", "app-chip app-chip-neutral"),
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
        ("Da scaricare", counts.get("saved", 0), "text-slate-600 dark:text-slate-300"),
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


def _render_filters(
    *,
    view: str,
    q: str,
    state: str,
    library_filter: str,
    category: str,
    mode: str,
    action_required: str,
    sort_by: str,
    libraries: list[str],
    categories: list[str],
) -> Form:
    current_state = (state or "").strip().lower()
    current_mode = (mode or "operativa").strip().lower()
    current_action_required = (action_required or "0").strip()
    current_sort = (sort_by or "").strip() or ("title_az" if (mode or "operativa") == "archivio" else "priority")
    category_options = categories or list(ITEM_TYPES)

    return Form(
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
                cls="app-btn app-btn-neutral",
            ),
            cls="flex flex-wrap gap-2",
        ),
        Div(
            Select(
                Option("Tutti gli stati", value=""),
                Option("Da scaricare", value="saved", selected=current_state == "saved"),
                Option("In coda", value="queued", selected=current_state == "queued"),
                Option("In download", value="downloading", selected=current_state == "downloading"),
                Option("Parziale", value="partial", selected=current_state == "partial"),
                Option("Completo", value="complete", selected=current_state == "complete"),
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
                Option("Vista Operativa", value="operativa", selected=current_mode == "operativa"),
                Option("Vista Archivio", value="archivio", selected=current_mode == "archivio"),
                name="mode",
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
        cls=(
            "rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/30 "
            "p-3 mb-5 sticky top-0 z-10 backdrop-blur"
        ),
    )


def _category_select_cls(item_type: str) -> str:
    _ = item_type
    return "app-field min-w-[180px] px-2.5 py-1.5 text-sm font-medium bg-white/90 dark:bg-slate-900/70"


def _primary_action(doc: dict):
    doc_id = quote(str(doc.get("id") or ""), safe="")
    library = quote(str(doc.get("library") or "Unknown"), safe="")
    state = str(doc.get("asset_state") or "saved").lower()
    has_missing = bool(doc.get("has_missing_pages"))

    if state == "partial" and has_missing:
        return _action_button(
            "🔁 Riprendi mancanti",
            f"/api/library/retry_missing?doc_id={doc_id}&library={library}",
            "accent",
        )

    if state in {"saved", "partial", "error"}:
        return _action_button(
            "⬇️ Scarica" if state == "saved" else "🔁 Riprova download",
            f"/api/library/start_download?doc_id={doc_id}&library={library}",
            "primary",
        )

    return None


def _maintenance_actions(doc: dict) -> list[Button]:
    doc_id = quote(str(doc.get("id") or ""), safe="")
    library = quote(str(doc.get("library") or "Unknown"), safe="")
    state = str(doc.get("asset_state") or "saved").lower()

    actions = []

    if state in {"partial", "error"}:
        actions.append(
            _action_button(
                "🧹 Pulizia parziale",
                f"/api/library/cleanup_partial?doc_id={doc_id}&library={library}",
                "warning",
            )
        )
    return actions


def _delete_action(doc: dict) -> Button:
    doc_id = quote(str(doc.get("id") or ""), safe="")
    library = quote(str(doc.get("library") or "Unknown"), safe="")
    return _action_button(
        "🗑️ Elimina",
        f"/api/library/delete?doc_id={doc_id}&library={library}",
        "danger",
        confirm="Confermi eliminazione completa del manoscritto locale?",
    )


def _category_form(doc: dict, item_type: str) -> Form:
    doc_id = quote(str(doc.get("id") or ""), safe="")
    library = quote(str(doc.get("library") or "Unknown"), safe="")
    return Form(
        Select(
            *[
                Option(_CATEGORY_LABELS.get(opt, opt.title()), value=opt, selected=item_type == opt)
                for opt in ITEM_TYPES
            ],
            name="item_type",
            onchange="this.form.requestSubmit()",
            cls=_category_select_cls(item_type),
        ),
        hx_post=f"/api/library/set_type?doc_id={doc_id}&library={library}",
        hx_target="#library-page",
        hx_swap="outerHTML show:none",
        hx_include="#library-filters",
    )


def _to_optional_bool(value) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n", ""}:
        return False
    return None


def _pdf_technical_info(doc: dict) -> tuple[str, str]:
    source_raw = str(doc.get("pdf_source") or "").strip().lower()
    if source_raw not in {"native", "images", "unknown"}:
        native = _to_optional_bool(doc.get("has_native_pdf"))
        if native is True:
            source_raw = "native"
        elif native is False:
            source_raw = "images"
        else:
            source_raw = "unknown"

    local_available = bool(_to_optional_bool(doc.get("pdf_local_available")))
    local_count = int(doc.get("pdf_local_count") or 0)

    source_map = {
        "native": "nativa",
        "images": "da immagini",
        "unknown": "non nota",
    }
    source_label = source_map[source_raw]
    local_count_label = str(max(local_count, 1) if local_available else 0)
    return source_label, local_count_label


def _compact_label(text: str) -> str:
    return "".join(ch for ch in (text or "").lower().strip() if ch.isalnum())


def library_card_dom_id(doc_id: str, library: str) -> str:
    """Return a stable DOM id for one library card."""
    raw = f"{library}::{doc_id}"
    token = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")
    return f"library-card-{token or 'item'}"


def _doc_card_dom_id(doc: dict) -> str:
    return library_card_dom_id(
        str(doc.get("id") or ""),
        str(doc.get("library") or "Unknown"),
    )


def _metadata_items(doc: dict) -> list[tuple[str, str]]:
    raw = str(doc.get("metadata_json") or "").strip()
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []
    out: list[tuple[str, str]] = []
    for key, value in payload.items():
        label = str(key or "").strip()
        text = str(value or "").strip()
        if label and text:
            out.append((label, text))
    return out


def _metadata_payload(doc: dict) -> str:
    payload = {
        "doc_id": str(doc.get("id") or ""),
        "library": str(doc.get("library") or "Unknown"),
        "card_id": _doc_card_dom_id(doc),
        "title": str(doc.get("display_title") or doc.get("id") or "-"),
        "shelfmark": str(doc.get("shelfmark") or doc.get("id") or "-"),
        "date_label": str(doc.get("date_label") or ""),
        "language_label": str(doc.get("language_label") or ""),
        "reference_text": str(doc.get("reference_text") or ""),
        "source_detail_url": str(doc.get("source_detail_url") or ""),
        "metadata_items": _metadata_items(doc),
    }
    text = json.dumps(payload, ensure_ascii=True)
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _tech_row(label: str, value: str) -> Div:
    return Div(
        Span(f"{label}:", cls="app-tech-key"),
        Span(value, cls="app-tech-val"),
        cls="app-tech-row",
    )


def _doc_card(doc: dict, *, compact: bool = False) -> Div:
    state = str(doc.get("asset_state") or "saved").lower()
    title = str(doc.get("display_title") or doc.get("id") or "-")
    item_type = str(doc.get("item_type") or "non classificato")
    total = int(doc.get("total_canvases") or 0)
    downloaded = int(doc.get("downloaded_canvases") or 0)
    progress = f"{downloaded}/{total}" if total > 0 else "0/0"
    missing_count = len(doc.get("missing_pages") or [])
    if missing_count <= 0 and total > downloaded:
        missing_count = max(total - downloaded, 0)
    detail_ref = str(doc.get("reference_text") or "")
    source_detail_url = str(doc.get("source_detail_url") or "")
    date_label = str(doc.get("date_label") or "")
    lang = str(doc.get("language_label") or "")
    shelfmark = str(doc.get("shelfmark") or doc.get("id") or "-")
    library_name = str(doc.get("library") or "Unknown")
    thumb_url = str(doc.get("thumbnail_url") or "")
    pdf_source_label, pdf_local_count = _pdf_technical_info(doc)
    compact_title = _compact_label(title)
    compact_shelfmark = _compact_label(shelfmark)
    compact_reference = _compact_label(detail_ref)
    show_reference = bool(detail_ref) and compact_reference not in {compact_title, compact_shelfmark}

    doc_id = quote(str(doc.get("id") or ""), safe="")
    library = quote(str(doc.get("library") or "Unknown"), safe="")
    studio_href = f"/studio?doc_id={doc_id}&library={library}"

    thumbnail_block = (
        Img(
            src=thumb_url,
            cls=(
                "w-full md:w-32 h-44 md:h-40 object-cover rounded-lg border border-slate-200 dark:border-slate-700 "
                "bg-slate-100 dark:bg-slate-800"
            ),
        )
        if thumb_url
        else Div(
            "Anteprima non disponibile",
            cls=(
                "w-full md:w-32 h-44 md:h-40 rounded-lg border border-dashed border-slate-300 dark:border-slate-700 "
                "text-xs text-slate-500 dark:text-slate-400 flex items-center justify-center text-center px-2"
            ),
        )
    )

    utility_actions = [
        _link_button("📖 Apri Studio", studio_href, tone="primary"),
        _link_button("🔗 Scheda catalogo ↗", source_detail_url, tone="external", external=True),
        Button(
            "🧾 Metadati",
            type="button",
            cls=_ACTION_BUTTON_CLS["info"],
            data_payload=_metadata_payload(doc),
            onclick="openLibraryMetadata(this.dataset.payload)",
        ),
    ]
    primary_action = _primary_action(doc)
    action_buttons = [*utility_actions]
    if primary_action is not None:
        action_buttons.append(primary_action)
    action_buttons.extend(_maintenance_actions(doc))

    media_badges = Div(
        _state_badge(state),
        cls="flex flex-wrap gap-2 mt-2",
    )
    technical_rows = Div(
        _tech_row("Pagine scaricate", progress),
        _tech_row("Pagine mancanti", str(missing_count)),
        _tech_row("Data", date_label or "-"),
        _tech_row("Lingua", lang or "-"),
        _tech_row("Sorgente PDF", pdf_source_label),
        _tech_row("PDF locali", pdf_local_count),
        cls="app-tech-list mt-2",
    )
    media_column = Div(
        thumbnail_block,
        media_badges,
        technical_rows,
        cls="w-full md:w-44 shrink-0",
    )

    headline = Div(
        H3(title, cls="text-base md:text-lg font-bold text-slate-900 dark:text-slate-100 leading-tight"),
        Div(
            Span(library_name, cls="text-sm text-slate-700 dark:text-slate-200 font-semibold"),
            _category_form(doc, item_type),
            cls="flex flex-wrap items-center justify-between gap-2",
        ),
        P(f"Segnatura: {shelfmark}", cls="text-sm text-slate-500 dark:text-slate-400"),
        cls="space-y-1 min-w-0",
    )

    return Div(
        media_column,
        Div(
            Div(
                headline,
                cls="flex items-start justify-between gap-3",
            ),
            (
                P(detail_ref, cls="text-sm text-slate-600 dark:text-slate-300 border-l-2 border-slate-300 pl-2")
                if show_reference
                else Div()
            ),
            Div(
                Div(*action_buttons, cls="flex flex-wrap items-center gap-2"),
                Div(_delete_action(doc), cls="flex items-center"),
                cls="flex flex-wrap items-start justify-between gap-2 pt-1",
            ),
            cls="space-y-3 flex-1",
        ),
        cls=(
            "flex flex-col md:flex-row gap-4 rounded-xl border border-slate-200 dark:border-slate-700 "
            + ("bg-slate-50 dark:bg-slate-800/55 p-3" if compact else "bg-slate-50 dark:bg-slate-800/75 p-4")
        ),
        id=_doc_card_dom_id(doc),
        data_library_card="1",
    )


def render_library_card(doc: dict, *, compact: bool = False) -> Div:
    """Render a single library card for targeted HTMX swaps."""
    return _doc_card(doc, compact=compact)


def _render_operational_list(docs: list[dict], view: str) -> Div:
    buckets = OrderedDict(
        [
            ("critici", {"label": "Critici", "entries": []}),
            ("in_corso", {"label": "In corso", "entries": []}),
            ("da_scaricare", {"label": "Da scaricare", "entries": []}),
            ("completati", {"label": "Completati", "entries": []}),
        ]
    )

    for doc in docs:
        state = str(doc.get("asset_state") or "saved").lower()
        if state == "error" or (state == "partial" and bool(doc.get("has_missing_pages"))):
            buckets["critici"]["entries"].append(doc)
        elif state in {"downloading", "running", "queued"}:
            buckets["in_corso"]["entries"].append(doc)
        elif state in {"saved", "partial"}:
            buckets["da_scaricare"]["entries"].append(doc)
        else:
            buckets["completati"]["entries"].append(doc)

    sections = []
    grid_cls = "space-y-3" if view == "list" else "grid xl:grid-cols-2 gap-3"
    for data in buckets.values():
        entries = data["entries"]
        if not entries:
            continue
        cards = [_doc_card(doc, compact=view == "list") for doc in entries]
        sections.append(
            Div(
                Div(
                    H3(data["label"], cls="text-base font-semibold text-slate-800 dark:text-slate-200"),
                    Span(str(len(entries)), cls="text-sm text-slate-500 dark:text-slate-400"),
                    cls="flex items-center justify-between mb-2",
                ),
                Div(*cards, cls=grid_cls),
                cls="mb-5",
            )
        )
    return Div(*sections, id="library-content")


def _render_archive_list(docs: list[dict], view: str) -> Div:
    grouped: OrderedDict[str, OrderedDict[str, list[dict]]] = OrderedDict()
    for doc in docs:
        lib = str(doc.get("library") or "Unknown")
        cat = str(doc.get("item_type") or "non classificato")
        grouped.setdefault(lib, OrderedDict()).setdefault(cat, []).append(doc)

    sections = []
    for lib, by_category in grouped.items():
        category_blocks = []
        for cat in ITEM_TYPES:
            entries = by_category.get(cat)
            if not entries:
                continue
            cards = [_doc_card(doc, compact=view == "list") for doc in entries]
            grid_cls = "space-y-3" if view == "list" else "grid xl:grid-cols-2 gap-3"
            category_blocks.append(
                Div(
                    Div(
                        H3(
                            _CATEGORY_LABELS.get(cat, cat.title()),
                            cls="text-base font-semibold text-slate-700 dark:text-slate-200",
                        ),
                        Span(str(len(entries)), cls="text-sm text-slate-500 dark:text-slate-400"),
                        cls="flex items-center justify-between mb-2",
                    ),
                    Div(*cards, cls=grid_cls),
                    cls="mb-4",
                )
            )

        sections.append(
            Details(
                Summary(
                    Div(
                        H3(lib, cls="text-lg font-bold text-slate-800 dark:text-slate-100"),
                        Span(
                            f"{sum(len(v) for v in by_category.values())} elementi",
                            cls="text-sm text-slate-500 dark:text-slate-400",
                        ),
                        cls="flex items-center justify-between",
                    ),
                    cls="cursor-pointer list-none",
                ),
                Div(*category_blocks, cls="mt-3"),
                open=True,
                cls="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/20 p-3 mb-4",
            )
        )

    return Div(*sections, id="library-content")


def render_library_list(docs: list[dict], view: str = "grid", mode: str = "operativa") -> Div:
    """Render grouped library entries in grid/list mode."""
    if not docs:
        return Div(
            P("Nessun documento trovato con i filtri correnti.", cls="text-sm text-slate-500 dark:text-slate-400"),
            id="library-content",
        )

    if (mode or "operativa").lower() == "archivio":
        return _render_archive_list(docs, view)
    return _render_operational_list(docs, view)


def _metadata_drawer() -> Div:
    return Div(
        Div(
            id="library-meta-overlay",
            onclick="closeLibraryMetadata(event)",
            cls="hidden fixed inset-0 z-40 bg-slate-900/50",
        ),
        Div(
            Div(
                Div(
                    H3(
                        "Metadati documento",
                        id="library-meta-title",
                        cls="text-lg font-semibold text-slate-900 dark:text-slate-100",
                    ),
                    Button(
                        "✕",
                        type="button",
                        onclick="closeLibraryMetadata()",
                        cls="text-lg text-slate-500 hover:text-slate-700 dark:text-slate-300 dark:hover:text-slate-100",
                    ),
                    cls="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 px-4 py-3",
                ),
                Div(
                    Div(
                        Div(
                            Span("Segnatura:", cls="app-tech-key"),
                            Span("-", id="library-meta-shelfmark", cls="app-tech-val"),
                            cls="app-tech-row",
                        ),
                        Div(
                            Span("Data:", cls="app-tech-key"),
                            Span("-", id="library-meta-date", cls="app-tech-val"),
                            cls="app-tech-row",
                        ),
                        Div(
                            Span("Lingua:", cls="app-tech-key"),
                            Span("-", id="library-meta-language", cls="app-tech-val"),
                            cls="app-tech-row",
                        ),
                        id="library-meta-tech",
                        cls="app-tech-list",
                    ),
                    P("", id="library-meta-reference", cls="text-sm text-slate-600 dark:text-slate-300"),
                    Div(id="library-meta-items", cls="space-y-1"),
                    cls="p-4 space-y-3 overflow-y-auto flex-1",
                ),
                Div(
                    Button(
                        "🧾 Aggiorna metadati",
                        id="library-meta-refresh",
                        type="button",
                        cls=_ACTION_BUTTON_CLS["info"],
                        hx_target="#library-page",
                        hx_swap="outerHTML show:none",
                        hx_include="#library-filters",
                    ),
                    A(
                        "🔗 Scheda catalogo ↗",
                        id="library-meta-catalog",
                        href="#",
                        target="_blank",
                        rel="noreferrer",
                        cls=_LINK_BUTTON_CLS["external"],
                    ),
                    cls="border-t border-slate-200 dark:border-slate-700 px-4 py-3 flex flex-wrap gap-2",
                ),
                cls=(
                    "flex h-full flex-col bg-white dark:bg-slate-900 shadow-2xl "
                    "rounded-t-2xl sm:rounded-none sm:rounded-l-2xl"
                ),
            ),
            id="library-meta-sheet",
            cls=(
                "hidden fixed z-50 inset-x-0 bottom-0 max-h-[85vh] "
                "sm:inset-y-0 sm:right-0 sm:left-auto sm:h-full sm:max-h-none sm:w-[560px]"
            ),
        ),
        Script(
            """(function () {
                function isLibraryMutation(detail) {
                    const path = (detail && detail.requestConfig && detail.requestConfig.path) || '';
                    if (typeof path === 'string' && path.startsWith('/api/library/')) return true;
                    const responseUrl = (detail && detail.xhr && detail.xhr.responseURL) || '';
                    return responseUrl.indexOf('/api/library/') !== -1;
                }

                function isMetadataRefreshRequest(detail) {
                    const path = String((detail && detail.requestConfig && detail.requestConfig.path) || '');
                    if (path.indexOf('/api/library/refresh_metadata') !== -1) return true;
                    const trigger = detail && detail.elt;
                    if (trigger && trigger.id === 'library-meta-refresh') return true;
                    return false;
                }

                function renderMetaRows(items) {
                    const holder = document.getElementById('library-meta-items');
                    if (!holder) return;
                    holder.innerHTML = '';
                    if (!Array.isArray(items) || !items.length) {
                        const empty = document.createElement('p');
                        empty.className = 'text-sm text-slate-500 dark:text-slate-400';
                        empty.textContent = 'Nessun metadato dettagliato disponibile.';
                        holder.appendChild(empty);
                        return;
                    }
                    items.forEach((entry) => {
                        if (!Array.isArray(entry) || entry.length < 2) return;
                        const row = document.createElement('div');
                        row.className = 'leading-snug';
                        const k = document.createElement('span');
                        k.className = 'text-sm text-slate-500 dark:text-slate-400';
                        k.textContent = String(entry[0] || '') + ': ';
                        const v = document.createElement('span');
                        v.className = 'text-sm text-slate-700 dark:text-slate-200';
                        v.textContent = String(entry[1] || '');
                        row.appendChild(k);
                        row.appendChild(v);
                        holder.appendChild(row);
                    });
                }

                function parsePayload(encoded) {
                    if (!encoded) return null;
                    try {
                        return JSON.parse(atob(encoded));
                    } catch (_e) {
                        return null;
                    }
                }

                window.openLibraryMetadata = function (encoded) {
                    const data = parsePayload(encoded);
                    if (!data) return;

                    const overlay = document.getElementById('library-meta-overlay');
                    const sheet = document.getElementById('library-meta-sheet');
                    const title = document.getElementById('library-meta-title');
                    const shelfmark = document.getElementById('library-meta-shelfmark');
                    const dateLabel = document.getElementById('library-meta-date');
                    const language = document.getElementById('library-meta-language');
                    const reference = document.getElementById('library-meta-reference');
                    const refresh = document.getElementById('library-meta-refresh');
                    const catalog = document.getElementById('library-meta-catalog');
                    if (
                        !overlay || !sheet || !title || !shelfmark || !dateLabel || !language ||
                        !reference || !refresh || !catalog
                    ) return;

                    title.textContent = data.title || 'Metadati documento';
                    shelfmark.textContent = data.shelfmark || '-';
                    dateLabel.textContent = data.date_label || '-';
                    language.textContent = data.language_label || '-';

                    reference.textContent = data.reference_text || '';
                    reference.classList.toggle('hidden', !data.reference_text);
                    renderMetaRows(data.metadata_items || []);

                    const refreshUrl = '/api/library/refresh_metadata?doc_id='
                        + encodeURIComponent(String(data.doc_id || ''))
                        + '&library='
                        + encodeURIComponent(String(data.library || 'Unknown'));
                    const targetCard = String(data.card_id || '').trim();
                    const cardRefreshUrl = refreshUrl + (targetCard ? '&card_only=1' : '');
                    refresh.setAttribute('data-card-id', targetCard);
                    refresh.setAttribute('hx-target', targetCard ? ('#' + targetCard) : '#library-page');
                    refresh.setAttribute('hx-swap', 'outerHTML show:none');
                    refresh.setAttribute('hx-post', cardRefreshUrl);
                    if (window.htmx && typeof window.htmx.process === 'function') {
                        window.htmx.process(refresh);
                    }

                    if (data.source_detail_url) {
                        catalog.setAttribute('href', data.source_detail_url);
                        catalog.classList.remove('hidden');
                    } else {
                        catalog.setAttribute('href', '#');
                        catalog.classList.add('hidden');
                    }

                    overlay.classList.remove('hidden');
                    sheet.classList.remove('hidden');
                    document.body.classList.add('overflow-hidden');
                };

                window.closeLibraryMetadata = function (event) {
                    if (event && event.target && event.target.id !== 'library-meta-overlay') return;
                    const overlay = document.getElementById('library-meta-overlay');
                    const sheet = document.getElementById('library-meta-sheet');
                    if (overlay) overlay.classList.add('hidden');
                    if (sheet) sheet.classList.add('hidden');
                    document.body.classList.remove('overflow-hidden');
                };

                document.addEventListener('keydown', (event) => {
                    if (event.key === 'Escape') window.closeLibraryMetadata();
                });

                if (!window.__libraryScrollRestoreBound) {
                    window.__libraryScrollRestoreBound = true;

                    document.body.addEventListener('htmx:beforeRequest', (event) => {
                        if (!isLibraryMutation(event.detail)) return;
                        const isMetaRefresh = isMetadataRefreshRequest(event.detail);
                        const appMain = document.getElementById('app-main');
                        if (appMain) {
                            window.__libraryScrollTop = appMain.scrollTop || 0;
                        }
                        if (isMetaRefresh) {
                            const refreshBtn = document.getElementById('library-meta-refresh');
                            const explicitCardId = refreshBtn
                                ? String(refreshBtn.getAttribute('data-card-id') || '').trim()
                                : '';
                            const targetSelector = refreshBtn ? String(refreshBtn.getAttribute('hx-target') || '') : '';
                            const targetCardId = explicitCardId || (
                                targetSelector.startsWith('#library-card-')
                                    ? targetSelector.slice(1)
                                    : ''
                            );
                            window.__libraryMetaRefreshContext = {
                                cardId: targetCardId
                            };
                        } else if (typeof window.closeLibraryMetadata === 'function') {
                            window.closeLibraryMetadata();
                            window.__libraryMetaRefreshContext = null;
                        }
                        if (!isMetaRefresh) {
                            const active = document.activeElement;
                            if (active && typeof active.blur === 'function') active.blur();
                        }
                    });

                    document.body.addEventListener('htmx:afterSwap', (event) => {
                        if (!isLibraryMutation(event.detail)) return;
                        if (!event.detail || !event.detail.target) return;
                        const targetId = event.detail.target.id || '';

                        if (isMetadataRefreshRequest(event.detail)) {
                            const ctx = window.__libraryMetaRefreshContext || {};
                            const cardId = String(ctx.cardId || '').trim();
                            if (cardId && typeof window.openLibraryMetadata === 'function') {
                                const card = document.getElementById(cardId);
                                const opener = card ? card.querySelector('[data-payload]') : null;
                                const payload = opener && opener.dataset ? opener.dataset.payload : '';
                                if (payload) {
                                    window.openLibraryMetadata(payload);
                                }
                            }
                            window.__libraryMetaRefreshContext = null;
                        }

                        if (targetId !== 'app-main' && targetId !== 'library-page') return;
                        const appMain = document.getElementById('app-main');
                        if (!appMain) return;
                        const targetTop = Number(window.__libraryScrollTop);
                        if (!Number.isFinite(targetTop)) return;
                        window.requestAnimationFrame(() => {
                            appMain.scrollTop = Math.max(0, targetTop);
                        });
                    });
                }
            })();"""
        ),
    )


def render_library_page(
    docs: list[dict],
    *,
    view: str = "grid",
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "operativa",
    action_required: str = "0",
    sort_by: str = "",
    libraries: list[str] | None = None,
    categories: list[str] | None = None,
) -> Div:
    """Render the full Local Library page."""
    libraries = libraries or []
    categories = categories or list(ITEM_TYPES)
    active_mode = "Archivio" if (mode or "operativa") == "archivio" else "Operativa"

    return Div(
        Div(
            H2("Libreria Locale", cls="text-2xl font-bold text-slate-800 dark:text-slate-100"),
            Span(f"Vista {active_mode}", cls="text-sm text-slate-500 dark:text-slate-400"),
            cls="flex items-center justify-between mb-4",
        ),
        _kpi_strip(docs),
        _render_filters(
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
            libraries=libraries,
            categories=categories,
        ),
        render_library_list(docs, view=view, mode=mode),
        _metadata_drawer(),
        cls="p-6 max-w-7xl mx-auto",
        id="library-page",
    )
