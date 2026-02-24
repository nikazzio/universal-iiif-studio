"""Library page components for local assets management."""

from __future__ import annotations

from collections import OrderedDict
from urllib.parse import quote

from fasthtml.common import H2, H3, A, Button, Details, Div, Form, Input, Option, P, Select, Span, Summary, Textarea

from universal_iiif_core.library_catalog import ITEM_TYPES

_STATE_STYLE = {
    "saved": ("Registrato", "bg-slate-700 text-slate-100"),
    "queued": ("In coda", "bg-cyan-800 text-cyan-100"),
    "downloading": ("Download", "bg-indigo-700 text-indigo-100"),
    "running": ("Download", "bg-indigo-700 text-indigo-100"),
    "partial": ("Parziale", "bg-amber-700 text-amber-100"),
    "complete": ("Completo", "bg-emerald-700 text-emerald-100"),
    "error": ("Errore", "bg-rose-700 text-rose-100"),
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
_ACTION_BUTTON_CLS = {
    "primary": "text-xs bg-indigo-700 hover:bg-indigo-600 text-white px-2.5 py-1.5 rounded",
    "success": "text-xs bg-emerald-700 hover:bg-emerald-600 text-white px-2.5 py-1.5 rounded",
    "danger": "text-xs bg-rose-700 hover:bg-rose-600 text-white px-2.5 py-1.5 rounded",
    "warning": "text-xs bg-amber-700 hover:bg-amber-600 text-white px-2.5 py-1.5 rounded",
    "neutral": "text-xs bg-slate-700 hover:bg-slate-600 text-white px-2.5 py-1.5 rounded",
}


def _state_badge(state: str) -> Span:
    label, cls = _STATE_STYLE.get((state or "saved").lower(), ("Registrato", "bg-slate-700 text-slate-100"))
    return Span(label, cls=f"text-[10px] px-2 py-1 rounded {cls}")


def _action_button(label: str, url: str, tone: str = "neutral", confirm: str | None = None) -> Button:
    kwargs = {
        "cls": _ACTION_BUTTON_CLS[tone],
        "hx_post": url,
        "hx_target": "#app-main",
        "hx_swap": "innerHTML",
        "hx_include": "#library-filters",
    }
    if confirm:
        kwargs["hx_confirm"] = confirm
    return Button(label, **kwargs)


def _state_counts(docs: list[dict]) -> dict[str, int]:
    out = {k: 0 for k in _STATE_STYLE}
    for doc in docs:
        key = str(doc.get("asset_state") or "saved").lower()
        out[key] = out.get(key, 0) + 1
    return out


def _kpi_strip(docs: list[dict]) -> Div:
    counts = _state_counts(docs)
    kpis = [
        ("Totale", len(docs), "text-slate-100"),
        ("Completi", counts.get("complete", 0), "text-emerald-300"),
        ("Parziali", counts.get("partial", 0), "text-amber-300"),
        (
            "In coda",
            counts.get("queued", 0) + counts.get("downloading", 0) + counts.get("running", 0),
            "text-indigo-300",
        ),
        ("Errori", counts.get("error", 0), "text-rose-300"),
        ("Registrati", counts.get("saved", 0), "text-slate-300"),
    ]
    cards = [
        Div(
            P(label, cls="text-[11px] uppercase tracking-wide text-slate-400"),
            P(str(value), cls=f"text-xl font-bold {color}"),
            cls="rounded-xl border border-slate-700 bg-slate-900/60 p-3 min-w-[110px]",
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
    libraries: list[str],
    categories: list[str],
) -> Form:
    category_options = categories or list(ITEM_TYPES)
    return Form(
        Div(
            Input(
                type="text",
                name="q",
                value=q,
                placeholder="Cerca per titolo, reference, segnatura, id, biblioteca...",
                cls=(
                    "px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-100 text-sm min-w-[240px] flex-1"
                ),
            ),
            Select(
                Option("Tutti gli stati", value=""),
                Option("Registrato", value="saved", selected=state == "saved"),
                Option("In coda", value="queued", selected=state == "queued"),
                Option("Download", value="downloading", selected=state == "downloading"),
                Option("Parziale", value="partial", selected=state == "partial"),
                Option("Completo", value="complete", selected=state == "complete"),
                Option("Errore", value="error", selected=state == "error"),
                name="state",
                cls="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-100 text-sm",
            ),
            Select(
                Option("Tutte le biblioteche", value=""),
                *[Option(lib, value=lib, selected=library_filter == lib) for lib in libraries],
                name="library_filter",
                cls="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-100 text-sm",
            ),
            Select(
                Option("Tutte le categorie", value=""),
                *[
                    Option(_CATEGORY_LABELS.get(cat, cat.title()), value=cat, selected=category == cat)
                    for cat in category_options
                ],
                name="category",
                cls="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-100 text-sm",
            ),
            cls="flex flex-wrap gap-2",
        ),
        Div(
            Select(
                Option("Vista Operativa", value="operativa", selected=(mode or "operativa") == "operativa"),
                Option("Vista Archivio", value="archivio", selected=(mode or "operativa") == "archivio"),
                name="mode",
                cls="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-100 text-sm",
            ),
            Select(
                Option("Grid", value="grid", selected=view == "grid"),
                Option("List", value="list", selected=view == "list"),
                name="view",
                cls="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-100 text-sm",
            ),
            Select(
                Option("Tutti gli elementi", value="0", selected=action_required != "1"),
                Option("Solo elementi da gestire", value="1", selected=action_required == "1"),
                name="action_required",
                cls="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-100 text-sm",
            ),
            Button(
                "Applica",
                cls="px-4 py-2 bg-indigo-700 hover:bg-indigo-600 text-white rounded text-sm",
                type="submit",
            ),
            A(
                "Reset",
                href="/library",
                hx_get="/library",
                hx_target="#app-main",
                hx_swap="innerHTML",
                hx_push_url="true",
                cls="px-4 py-2 border border-slate-700 rounded text-slate-300 text-sm hover:bg-slate-800",
            ),
            Button(
                "Normalizza stati",
                cls="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded text-sm",
                hx_post="/api/library/normalize_states",
                hx_target="#app-main",
                hx_swap="innerHTML",
                hx_include="#library-filters",
                type="button",
            ),
            Button(
                "Riclassifica auto",
                cls="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded text-sm",
                hx_post="/api/library/reclassify_all",
                hx_target="#app-main",
                hx_swap="innerHTML",
                hx_include="#library-filters",
                type="button",
            ),
            cls="flex flex-wrap gap-2 items-center mt-2",
        ),
        id="library-filters",
        hx_get="/library",
        hx_target="#app-main",
        hx_swap="innerHTML",
        hx_push_url="true",
        cls="rounded-xl border border-slate-700 bg-slate-900/40 p-3 mb-5 sticky top-0 z-10 backdrop-blur",
    )


def _doc_actions(doc: dict) -> Div:
    doc_id = quote(str(doc.get("id") or ""), safe="")
    library = quote(str(doc.get("library") or "Unknown"), safe="")
    state = str(doc.get("asset_state") or "saved").lower()
    has_missing = bool(doc.get("has_missing_pages"))

    actions = [
        A(
            "Apri Studio",
            href=f"/studio?doc_id={doc_id}&library={library}",
            cls="text-xs text-indigo-300 hover:text-indigo-200 underline",
        ),
        _action_button(
            "Aggiorna metadati",
            f"/api/library/refresh_metadata?doc_id={doc_id}&library={library}",
            "neutral",
        ),
        _action_button("Riclassifica", f"/api/library/reclassify?doc_id={doc_id}&library={library}", "neutral"),
    ]

    if state in {"saved", "partial", "error"}:
        label = "Scarica" if state == "saved" else "Riprova download"
        actions.insert(
            1,
            _action_button(
                label,
                f"/api/library/start_download?doc_id={doc_id}&library={library}",
                "success",
            ),
        )

    if state == "partial" and has_missing:
        actions.insert(
            2,
            _action_button(
                "Riprendi mancanti",
                f"/api/library/retry_missing?doc_id={doc_id}&library={library}",
                "primary",
            ),
        )

    if state in {"partial", "error"}:
        actions.append(
            _action_button(
                "Pulizia parziale",
                f"/api/library/cleanup_partial?doc_id={doc_id}&library={library}",
                "warning",
            )
        )

    actions.append(
        _action_button(
            "Elimina",
            f"/api/library/delete?doc_id={doc_id}&library={library}",
            "danger",
            confirm="Confermi eliminazione completa del manoscritto locale?",
        )
    )
    return Div(*actions, cls="flex gap-2 flex-wrap")


def _doc_card(doc: dict, *, compact: bool = False) -> Div:
    state = str(doc.get("asset_state") or "saved").lower()
    title = str(doc.get("display_title") or doc.get("id") or "-")
    item_type = str(doc.get("item_type") or "non classificato")
    item_type_label = _CATEGORY_LABELS.get(item_type, item_type.title())
    item_type_source = str(doc.get("item_type_source") or "auto").lower()
    source_label = "Manuale" if item_type_source == "manual" else "Auto"

    total = int(doc.get("total_canvases") or 0)
    downloaded = int(doc.get("downloaded_canvases") or 0)
    progress = f"{downloaded}/{total}" if total > 0 else "0/0"
    missing_count = len(doc.get("missing_pages") or [])
    detail_ref = str(doc.get("reference_text") or "")
    source_detail_url = str(doc.get("source_detail_url") or "")
    date_label = str(doc.get("date_label") or "")
    lang = str(doc.get("language_label") or "")
    metadata_preview = doc.get("metadata_preview") or []

    doc_id = quote(str(doc.get("id") or ""), safe="")
    library = quote(str(doc.get("library") or "Unknown"), safe="")

    category_form = Form(
        Select(
            *[
                Option(_CATEGORY_LABELS.get(opt, opt.title()), value=opt, selected=item_type == opt)
                for opt in ITEM_TYPES
            ],
            name="item_type",
            onchange="this.form.requestSubmit()",
            cls="px-2 py-1 bg-slate-900 border border-slate-700 rounded text-slate-100 text-[11px]",
        ),
        hx_post=f"/api/library/set_type?doc_id={doc_id}&library={library}",
        hx_target="#app-main",
        hx_swap="innerHTML",
        hx_include="#library-filters",
    )

    note_box = Details(
        Summary("Note", cls="text-[11px] text-slate-300 cursor-pointer"),
        Form(
            Textarea(
                doc.get("user_notes", ""),
                name="user_notes",
                rows="3",
                cls="mt-2 w-full px-2 py-2 bg-slate-900 border border-slate-700 rounded text-slate-100 text-xs",
                placeholder="Aggiungi note contestuali, riferimenti, priorità di lavoro...",
            ),
            Button(
                "Salva note",
                type="submit",
                cls="mt-2 text-xs bg-slate-700 hover:bg-slate-600 text-white px-2.5 py-1.5 rounded",
            ),
            hx_post=f"/api/library/update_notes?doc_id={doc_id}&library={library}",
            hx_target="#app-main",
            hx_swap="innerHTML",
            hx_include="#library-filters",
        ),
        open=bool(doc.get("user_notes")),
        cls="rounded border border-slate-700 bg-slate-900/30 p-2",
    )

    metadata_details = (
        Details(
            Summary("Metadati manifest", cls="text-[11px] text-slate-300 cursor-pointer"),
            Div(
                *[
                    Div(
                        Span(f"{label}: ", cls="text-[11px] text-slate-400"),
                        Span(str(value), cls="text-[11px] text-slate-200"),
                        cls="leading-snug",
                    )
                    for label, value in metadata_preview
                ],
                cls="mt-2 space-y-1",
            ),
            cls="rounded border border-slate-700 bg-slate-900/30 p-2",
        )
        if metadata_preview
        else Div()
    )

    return Div(
        Div(
            H3(title, cls="text-sm font-bold text-slate-100 leading-tight"),
            P(
                f"{doc.get('library', 'Unknown')} · {doc.get('shelfmark', doc.get('id', '-'))}",
                cls="text-xs text-slate-400",
            ),
            cls="space-y-1",
        ),
        Div(
            _state_badge(state),
            Span(progress, cls="text-[11px] text-slate-300"),
            Span(item_type_label, cls="text-[10px] px-2 py-1 rounded bg-slate-700 text-slate-100"),
            Span(source_label, cls="text-[10px] px-2 py-1 rounded bg-slate-800 text-slate-300"),
            cls="flex gap-2 items-center flex-wrap mt-2",
        ),
        Div(
            Span(f"Data: {date_label or '-'}", cls="text-[11px] text-slate-400"),
            Span(f"Lingua: {lang or '-'}", cls="text-[11px] text-slate-400"),
            Span(f"Mancanti: {missing_count}", cls="text-[11px] text-slate-400"),
            cls="flex flex-wrap gap-3",
        ),
        P(detail_ref, cls="text-xs text-slate-300 line-clamp-2") if detail_ref else Div(),
        (
            A(
                "Scheda catalogo esterna",
                href=source_detail_url,
                target="_blank",
                rel="noreferrer",
                cls="text-xs text-sky-300 hover:text-sky-200 underline",
            )
            if source_detail_url
            else Div()
        ),
        Div(
            Span("Categoria", cls="text-[11px] text-slate-400"),
            category_form,
            cls="flex items-center gap-2",
        ),
        _doc_actions(doc),
        metadata_details,
        note_box,
        cls=(
            "space-y-2 rounded-xl border border-slate-700 "
            + ("bg-slate-900/35 p-3" if compact else "bg-slate-900/45 p-4")
        ),
    )


def render_library_list(docs: list[dict], view: str = "grid") -> Div:
    """Render grouped library entries in grid/list mode."""
    if not docs:
        return Div(
            P("Nessun documento trovato con i filtri correnti.", cls="text-sm text-slate-400"),
            id="library-content",
        )

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
            grid_cls = "space-y-3" if view == "list" else "grid sm:grid-cols-2 xl:grid-cols-2 gap-3"
            category_blocks.append(
                Div(
                    Div(
                        H3(_CATEGORY_LABELS.get(cat, cat.title()), cls="text-sm font-semibold text-slate-200"),
                        Span(str(len(entries)), cls="text-xs text-slate-400"),
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
                        H3(lib, cls="text-lg font-bold text-slate-100"),
                        Span(f"{sum(len(v) for v in by_category.values())} elementi", cls="text-xs text-slate-400"),
                        cls="flex items-center justify-between",
                    ),
                    cls="cursor-pointer list-none",
                ),
                Div(*category_blocks, cls="mt-3"),
                open=True,
                cls="rounded-xl border border-slate-700 bg-slate-900/30 p-3 mb-4",
            )
        )

    return Div(*sections, id="library-content")


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
    libraries: list[str] | None = None,
    categories: list[str] | None = None,
) -> Div:
    """Render the full Local Library page."""
    libraries = libraries or []
    categories = categories or list(ITEM_TYPES)
    return Div(
        H2("Libreria Locale", cls="text-2xl font-bold text-slate-100 mb-4"),
        _kpi_strip(docs),
        _render_filters(
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            libraries=libraries,
            categories=categories,
        ),
        render_library_list(docs, view=view),
        cls="p-6 max-w-7xl mx-auto",
    )
