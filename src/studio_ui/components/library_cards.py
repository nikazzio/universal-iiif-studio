"""Library card/list rendering helpers."""

from __future__ import annotations

import base64
import json
from collections import OrderedDict
from urllib.parse import quote

from fasthtml.common import H3, A, Button, Details, Div, Form, Img, Option, P, Script, Select, Span, Summary

from studio_ui.common.library_constants import (
    ACTION_BUTTON_CLS,
    CATEGORY_LABELS,
    CATEGORY_SELECT_TONE,
    LINK_BUTTON_CLS,
    STATE_STYLE,
)
from studio_ui.common.title_utils import truncate_title
from universal_iiif_core.library_catalog import ITEM_TYPES

_STATE_STYLE = STATE_STYLE
_CATEGORY_LABELS = CATEGORY_LABELS
_ACTION_BUTTON_CLS = ACTION_BUTTON_CLS
_LINK_BUTTON_CLS = LINK_BUTTON_CLS
_CATEGORY_SELECT_TONE = CATEGORY_SELECT_TONE


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
    *,
    enabled: bool = True,
) -> Button:
    base_cls = _ACTION_BUTTON_CLS[tone]
    if not enabled:
        disabled_cls = f"{base_cls} opacity-45 cursor-not-allowed pointer-events-none"
        kwargs = {
            "type": "button",
            "cls": disabled_cls,
            "disabled": True,
        }
        if hint:
            kwargs["title"] = hint
        return Button(label, **kwargs)

    kwargs = {
        "cls": base_cls,
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
        ("Locali completi", counts.get("complete", 0), "text-slate-700 dark:text-slate-200"),
        ("Locali parziali", counts.get("partial", 0), "text-slate-700 dark:text-slate-200"),
        (
            "In download",
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


def _category_select_cls(item_type: str) -> str:
    tone = _CATEGORY_SELECT_TONE.get(item_type, _CATEGORY_SELECT_TONE["non classificato"])
    return f"app-field min-w-[180px] px-2.5 py-1.5 text-sm font-medium {tone}"


def _card_action_flags(doc: dict) -> dict[str, bool]:
    state = str(doc.get("asset_state") or "saved").lower()
    is_running = state in {"downloading", "running", "queued"}
    has_missing = bool(doc.get("has_missing_pages"))
    return {
        "download_full": not is_running and state == "saved",
        "retry_missing": not is_running and has_missing,
        "cleanup_partial": not is_running and state in {"partial", "error"},
        "delete_doc": not is_running,
    }


def _delete_action(doc: dict, *, enabled: bool = True) -> Button:
    doc_id = quote(str(doc.get("id") or ""), safe="")
    library = quote(str(doc.get("library") or "Unknown"), safe="")
    return _action_button(
        "🗑️ Elimina",
        f"/api/library/delete?doc_id={doc_id}&library={library}",
        "danger",
        confirm="Confermi eliminazione completa del manoscritto locale?",
        enabled=enabled,
        hint="Disabilitato durante un download attivo." if not enabled else None,
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


_METADATA_LABEL_MAP: dict[str, str] = {
    "author": "Autore",
    "creator": "Autore",
    "autore": "Autore",
    "dc:creator": "Autore",
    "dc.creator": "Autore",
    "créateur": "Autore",
    "contributor": "Contributore",
    "title": "Titolo",
    "titre": "Titolo",
    "titolo": "Titolo",
    "dc:title": "Titolo",
    "dc.title": "Titolo",
    "publisher": "Editore",
    "editore": "Editore",
    "éditeur": "Editore",
    "dc:publisher": "Editore",
    "dc.publisher": "Editore",
    "source": "Fonte",
    "date": "Data",
    "issued": "Data",
    "dc:date": "Data",
    "dc.date": "Data",
    "language": "Lingua",
    "lingua": "Lingua",
    "dc:language": "Lingua",
    "dc.language": "Lingua",
    "description": "Descrizione",
    "descrizione": "Descrizione",
    "dc:description": "Descrizione",
    "dc.description": "Descrizione",
    "shelfmark": "Segnatura",
    "segnatura": "Segnatura",
    "shelf mark": "Segnatura",
    "call number": "Segnatura",
    "cote": "Segnatura",
    "type": "Tipo",
    "dc:type": "Tipo",
    "dc.type": "Tipo",
    "genre": "Genere",
    "subject": "Soggetto",
    "soggetto": "Soggetto",
    "dc:subject": "Soggetto",
    "dc.subject": "Soggetto",
    "material": "Materiale",
    "format": "Formato",
    "dc:format": "Formato",
    "dc.format": "Formato",
    "extent": "Dimensioni",
    "dimensions": "Dimensioni",
    "identifier": "Identificativo",
    "dc:identifier": "Identificativo",
    "dc.identifier": "Identificativo",
    "relation": "Relazione",
    "dc:relation": "Relazione",
    "dc.relation": "Relazione",
    "rights": "Diritti",
    "dc:rights": "Diritti",
    "dc.rights": "Diritti",
    "license": "Licenza",
    "repository": "Repository",
    "collection": "Collezione",
    "provenance": "Provenienza",
    "ext_repository": "Repository",
    "ext_collection": "Collezione",
    "ext_institution": "Istituzione",
}

# Sections: key patterns mapped to section names
_SECTION_IDENTIFICATION = {"autore", "titolo", "editore", "fonte", "data", "lingua", "segnatura"}
_SECTION_CONTENT = {"descrizione", "tipo", "genere", "soggetto", "materiale"}
_SECTION_PROVENANCE = {"repository", "collezione", "provenienza", "istituzione"}
_SECTION_TECHNICAL = {"formato", "dimensioni", "identificativo", "relazione", "diritti", "licenza", "contributore"}


def _categorize_metadata_item(label_it: str) -> str:
    """Return the section name for a normalized Italian label."""
    lbl = label_it.lower()
    if lbl in _SECTION_IDENTIFICATION:
        return "identification"
    if lbl in _SECTION_CONTENT:
        return "content"
    if lbl in _SECTION_PROVENANCE:
        return "provenance"
    if lbl in _SECTION_TECHNICAL:
        return "technical"
    return "other"


# Fields already shown in fixed header — skip in the item list
_DRAWER_FIXED_KEYS = {
    "shelfmark",
    "segnatura",
    "shelf mark",
    "call number",
    "cote",
    "date",
    "issued",
    "dc:date",
    "dc.date",
    "language",
    "lingua",
    "dc:language",
    "dc.language",
    "title",
    "titre",
    "titolo",
    "dc:title",
    "dc.title",
    "author",
    "creator",
    "autore",
    "dc:creator",
    "dc.creator",
    "créateur",
    "publisher",
    "editore",
    "éditeur",
    "dc:publisher",
    "dc.publisher",
    "description",
    "descrizione",
    "dc:description",
    "dc.description",
    "source",
}


def _metadata_items(doc: dict) -> list[tuple[str, str, str]]:
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
        if not label or not text:
            continue
        # Skip fields shown in fixed header
        if label.lower().strip() in _DRAWER_FIXED_KEYS:
            continue
        # Clean ext_ prefix
        clean_key = label[4:] if label.lower().startswith("ext_") else label
        # Normalize label
        normalized = _METADATA_LABEL_MAP.get(label.lower().strip(), clean_key)
        # Categorize for section grouping
        section = _categorize_metadata_item(normalized)
        out.append((normalized, text, section))
    return out


def _metadata_payload(doc: dict) -> str:
    payload = {
        "doc_id": str(doc.get("id") or ""),
        "library": str(doc.get("library") or "Unknown"),
        "card_id": _doc_card_dom_id(doc),
        "title": str(doc.get("display_title") or doc.get("id") or "-"),
        "author": str(doc.get("author") or ""),
        "publisher": str(doc.get("publisher") or ""),
        "description": str(doc.get("description") or ""),
        "attribution": str(doc.get("attribution") or ""),
        "shelfmark": str(doc.get("shelfmark") or doc.get("id") or "-"),
        "date_label": str(doc.get("date_label") or ""),
        "language_label": str(doc.get("language_label") or ""),
        "reference_text": str(doc.get("reference_text") or ""),
        "source_detail_url": str(doc.get("source_detail_url") or ""),
        "user_notes": str(doc.get("user_notes") or ""),
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
    temp_pages_count = int(doc.get("temp_pages_count") or 0)
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
    author = str(doc.get("author") or "")
    publisher = str(doc.get("publisher") or "")
    description = str(doc.get("description") or "")
    user_notes = str(doc.get("user_notes") or "")
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

    action_flags = _card_action_flags(doc)
    open_studio_action = A(
        "📖 Apri Studio",
        href=studio_href,
        cls="app-btn app-btn-primary w-full md:w-auto",
    )
    item_action_buttons = [
        _action_button(
            "⬇️ Scarica locale",
            f"/api/library/download_full?doc_id={doc_id}&library={library}",
            "neutral",
            enabled=action_flags["download_full"],
            hint="Disabilitato: item gia completo o download in corso.",
        ),
        _action_button(
            "🔁 Riprendi mancanti",
            f"/api/library/retry_missing?doc_id={doc_id}&library={library}",
            "neutral",
            enabled=action_flags["retry_missing"],
            hint="Attivo solo quando ci sono pagine mancanti note.",
        ),
        _action_button(
            "🧹 Pulizia parziale",
            f"/api/library/cleanup_partial?doc_id={doc_id}&library={library}",
            "neutral",
            enabled=action_flags["cleanup_partial"],
            hint="Attivo su item parziali o in errore.",
        ),
    ]

    info_inline = Div(
        Button(
            "🧾 Metadati",
            type="button",
            cls=(
                "text-xs font-medium text-slate-600 dark:text-slate-300 "
                "hover:text-slate-900 dark:hover:text-slate-100 underline underline-offset-2"
            ),
            data_payload=_metadata_payload(doc),
            onclick="openLibraryMetadata(this.dataset.payload)",
        ),
        (
            A(
                "🔗 Scheda catalogo ↗",
                href=source_detail_url,
                target="_blank",
                rel="noreferrer",
                cls=(
                    "text-xs font-medium text-slate-600 dark:text-slate-300 "
                    "hover:text-slate-900 dark:hover:text-slate-100 underline underline-offset-2"
                ),
            )
            if source_detail_url
            else Span("🔗 Scheda catalogo non disponibile", cls="text-xs text-slate-400 dark:text-slate-500")
        ),
        cls="flex flex-wrap items-center gap-3",
    )

    actions_block = Div(
        Div(
            Span(
                "Azione principale",
                cls="text-[10px] uppercase tracking-wide text-slate-500 dark:text-slate-400",
            ),
            Div(open_studio_action, cls="mt-1"),
            cls="space-y-1",
        ),
        Div(
            Span(
                "Azioni documento",
                cls="text-[10px] uppercase tracking-wide text-slate-500 dark:text-slate-400",
            ),
            Div(*item_action_buttons, cls="flex flex-wrap items-center gap-1.5 mt-1"),
            cls="space-y-1",
        ),
        Div(
            _delete_action(doc, enabled=action_flags["delete_doc"]),
            cls="flex justify-end border-t border-slate-200 dark:border-slate-700 pt-2 mt-1",
        ),
        cls="mt-auto flex flex-col gap-2.5 pt-2",
    )

    media_badges = Div(
        _state_badge(state),
        cls="flex flex-wrap gap-2 mt-2",
    )
    technical_rows = Div(
        _tech_row("Pagine scaricate", progress),
        _tech_row("Pagine temporanee", str(temp_pages_count)),
        _tech_row("Pagine mancanti", str(missing_count)),
        _tech_row("Data", date_label or "-"),
        _tech_row("Lingua", lang or "-"),
        cls="app-tech-list mt-2",
    )
    media_column = Div(
        thumbnail_block,
        media_badges,
        technical_rows,
        cls="w-full md:w-44 shrink-0",
    )

    card_title = truncate_title(title, max_len=70, suffix="[...]")

    # Build headline with author and publisher info
    headline_children = [
        H3(
            A(
                card_title,
                href=studio_href,
                cls=(
                    "text-slate-900 dark:text-slate-100 hover:text-slate-700 "
                    "dark:hover:text-slate-200 hover:underline underline-offset-2"
                ),
            ),
            title=title,
            cls="text-base md:text-lg font-bold leading-tight",
        ),
    ]
    if author:
        headline_children.append(
            P(
                author,
                cls="text-sm text-slate-600 dark:text-slate-300 italic",
                title=author,
            )
        )
    headline_children.append(
        Div(
            Span(library_name, cls="text-sm text-slate-700 dark:text-slate-200 font-semibold"),
            _category_form(doc, item_type),
            cls="flex flex-wrap items-center gap-2",
        )
    )
    headline_children.append(P(f"Segnatura: {shelfmark}", cls="text-sm text-slate-500 dark:text-slate-400"))
    if publisher:
        headline_children.append(
            P(
                f"Editore: {publisher}",
                cls="text-xs text-slate-500 dark:text-slate-400",
                title=publisher,
            )
        )
    headline_children.append(info_inline)
    headline = Div(*headline_children, cls="space-y-1 min-w-0")

    # Optional description preview (max 2 lines)
    desc_block = (
        P(
            truncate_title(description, max_len=160, suffix="…"),
            cls="text-xs text-slate-500 dark:text-slate-400 line-clamp-2",
            title=description,
        )
        if description
        else Div()
    )

    # User notes indicator
    notes_block = (
        Div(
            Span("📝", cls="text-sm"),
            Span(
                truncate_title(user_notes, max_len=80, suffix="…"),
                cls="text-xs text-slate-500 dark:text-slate-400 italic",
            ),
            cls="flex items-center gap-1",
        )
        if user_notes
        else Div()
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
            desc_block,
            notes_block,
            actions_block,
            cls="space-y-3 flex-1 min-w-0 flex flex-col",
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
            ("remoti", {"label": "Remoti / Parziali", "entries": []}),
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
            buckets["remoti"]["entries"].append(doc)
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
        lib_key = base64.urlsafe_b64encode(lib.encode("utf-8")).decode("ascii").rstrip("=") or "library"
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
                data_collapsible_key=f"archive:{lib_key}",
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
                    # Fixed identification fields
                    Div(
                        Div(
                            Span("Autore:", cls="app-tech-key"),
                            Span("-", id="library-meta-author", cls="app-tech-val"),
                            cls="app-tech-row",
                        ),
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
                        Div(
                            Span("Editore:", cls="app-tech-key"),
                            Span("-", id="library-meta-publisher", cls="app-tech-val"),
                            cls="app-tech-row hidden",
                            id="library-meta-publisher-row",
                        ),
                        Div(
                            Span("Attribuzione:", cls="app-tech-key"),
                            Span("-", id="library-meta-attribution", cls="app-tech-val"),
                            cls="app-tech-row hidden",
                            id="library-meta-attribution-row",
                        ),
                        id="library-meta-tech",
                        cls="app-tech-list",
                    ),
                    # Description block
                    P("", id="library-meta-description", cls="text-sm text-slate-600 dark:text-slate-300 hidden"),
                    # Reference text
                    P("", id="library-meta-reference", cls="text-sm text-slate-600 dark:text-slate-300"),
                    # User notes
                    Div(
                        Span("📝 ", cls="text-sm"),
                        Span("", id="library-meta-notes", cls="text-sm text-slate-500 dark:text-slate-400 italic"),
                        id="library-meta-notes-row",
                        cls="hidden",
                    ),
                    # Metadata sections container
                    Div(id="library-meta-items", cls="space-y-3"),
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

                var SECTION_LABELS = {
                    'content': 'Contenuto',
                    'provenance': 'Provenienza',
                    'technical': 'Tecnico',
                    'other': 'Altro'
                };

                function renderMetaRows(items) {
                    var holder = document.getElementById('library-meta-items');
                    if (!holder) return;
                    holder.innerHTML = '';
                    if (!Array.isArray(items) || !items.length) {
                        var empty = document.createElement('p');
                        empty.className = 'text-sm text-slate-500 dark:text-slate-400';
                        empty.textContent = 'Nessun metadato dettagliato disponibile.';
                        holder.appendChild(empty);
                        return;
                    }
                    // Group by section
                    var sections = {};
                    items.forEach(function(entry) {
                        if (!Array.isArray(entry) || entry.length < 2) return;
                        var section = (entry.length >= 3 && entry[2]) ? entry[2] : 'other';
                        if (!sections[section]) sections[section] = [];
                        sections[section].push(entry);
                    });
                    var order = ['content', 'provenance', 'technical', 'other'];
                    order.forEach(function(sectionKey) {
                        var sectionItems = sections[sectionKey];
                        if (!sectionItems || !sectionItems.length) return;
                        var sectionDiv = document.createElement('div');
                        sectionDiv.className = 'space-y-1';
                        var heading = document.createElement('h4');
                        heading.className = 'text-xs font-semibold uppercase tracking-wide '
                            + 'text-slate-400 dark:text-slate-500 pt-2 border-t border-slate-100 dark:border-slate-800';
                        heading.textContent = SECTION_LABELS[sectionKey] || sectionKey;
                        sectionDiv.appendChild(heading);
                        sectionItems.forEach(function(entry) {
                            var row = document.createElement('div');
                            row.className = 'leading-snug';
                            var k = document.createElement('span');
                            k.className = 'text-sm text-slate-500 dark:text-slate-400';
                            k.textContent = String(entry[0] || '') + ': ';
                            var v = document.createElement('span');
                            v.className = 'text-sm text-slate-700 dark:text-slate-200';
                            v.textContent = String(entry[1] || '');
                            row.appendChild(k);
                            row.appendChild(v);
                            sectionDiv.appendChild(row);
                        });
                        holder.appendChild(sectionDiv);
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

                function setFieldVisible(elId, value, rowId) {
                    var el = document.getElementById(elId);
                    if (el) el.textContent = value || '-';
                    if (rowId) {
                        var row = document.getElementById(rowId);
                        if (row) row.classList.toggle('hidden', !value);
                    }
                }

                window.openLibraryMetadata = function (encoded) {
                    var data = parsePayload(encoded);
                    if (!data) return;

                    var overlay = document.getElementById('library-meta-overlay');
                    var sheet = document.getElementById('library-meta-sheet');
                    var title = document.getElementById('library-meta-title');
                    var shelfmark = document.getElementById('library-meta-shelfmark');
                    var dateLabel = document.getElementById('library-meta-date');
                    var language = document.getElementById('library-meta-language');
                    var reference = document.getElementById('library-meta-reference');
                    var refresh = document.getElementById('library-meta-refresh');
                    var catalog = document.getElementById('library-meta-catalog');
                    if (
                        !overlay || !sheet || !title || !shelfmark || !dateLabel || !language ||
                        !reference || !refresh || !catalog
                    ) return;

                    title.textContent = data.title || 'Metadati documento';
                    shelfmark.textContent = data.shelfmark || '-';
                    dateLabel.textContent = data.date_label || '-';
                    language.textContent = data.language_label || '-';

                    // Author
                    setFieldVisible('library-meta-author', data.author || '');
                    // Publisher
                    setFieldVisible('library-meta-publisher', data.publisher || '', 'library-meta-publisher-row');
                    // Attribution
                    setFieldVisible('library-meta-attribution', data.attribution || '', 'library-meta-attribution-row');

                    // Description
                    var descEl = document.getElementById('library-meta-description');
                    if (descEl) {
                        descEl.textContent = data.description || '';
                        descEl.classList.toggle('hidden', !data.description);
                    }

                    // User notes
                    var notesEl = document.getElementById('library-meta-notes');
                    var notesRow = document.getElementById('library-meta-notes-row');
                    if (notesEl) notesEl.textContent = data.user_notes || '';
                    if (notesRow) notesRow.classList.toggle('hidden', !data.user_notes);

                    reference.textContent = data.reference_text || '';
                    reference.classList.toggle('hidden', !data.reference_text);
                    renderMetaRows(data.metadata_items || []);

                    var refreshUrl = '/api/library/refresh_metadata?doc_id='
                        + encodeURIComponent(String(data.doc_id || ''))
                        + '&library='
                        + encodeURIComponent(String(data.library || 'Unknown'));
                    var targetCard = String(data.card_id || '').trim();
                    var cardRefreshUrl = refreshUrl + (targetCard ? '&card_only=1' : '');
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
                    var overlay = document.getElementById('library-meta-overlay');
                    var sheet = document.getElementById('library-meta-sheet');
                    if (overlay) overlay.classList.add('hidden');
                    if (sheet) sheet.classList.add('hidden');
                    document.body.classList.remove('overflow-hidden');
                };

                document.addEventListener('keydown', function(event) {
                    if (event.key === 'Escape') window.closeLibraryMetadata();
                });

                if (!window.__libraryScrollRestoreBound) {
                    window.__libraryScrollRestoreBound = true;

                    document.body.addEventListener('htmx:beforeRequest', function(event) {
                        if (!isLibraryMutation(event.detail)) return;
                        var isMetaRefresh = isMetadataRefreshRequest(event.detail);
                        var appMain = document.getElementById('app-main');
                        if (appMain) {
                            window.__libraryScrollTop = appMain.scrollTop || 0;
                        }
                        if (isMetaRefresh) {
                            var refreshBtn = document.getElementById('library-meta-refresh');
                            var explicitCardId = refreshBtn
                                ? String(refreshBtn.getAttribute('data-card-id') || '').trim()
                                : '';
                            var targetSelector = refreshBtn ? String(refreshBtn.getAttribute('hx-target') || '') : '';
                            var targetCardId = explicitCardId || (
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
                            var active = document.activeElement;
                            if (active && typeof active.blur === 'function') active.blur();
                        }
                    });

                    document.body.addEventListener('htmx:afterSwap', function(event) {
                        if (!isLibraryMutation(event.detail)) return;
                        if (!event.detail || !event.detail.target) return;
                        var targetId = event.detail.target.id || '';

                        if (isMetadataRefreshRequest(event.detail)) {
                            var ctx = window.__libraryMetaRefreshContext || {};
                            var cardId = String(ctx.cardId || '').trim();
                            if (cardId && typeof window.openLibraryMetadata === 'function') {
                                var card = document.getElementById(cardId);
                                var opener = card ? card.querySelector('[data-payload]') : null;
                                var payload = opener && opener.dataset ? opener.dataset.payload : '';
                                if (payload) {
                                    window.openLibraryMetadata(payload);
                                }
                            }
                            window.__libraryMetaRefreshContext = null;
                        }

                        if (targetId !== 'app-main' && targetId !== 'library-page') return;
                        var appMain = document.getElementById('app-main');
                        if (!appMain) return;
                        var targetTop = Number(window.__libraryScrollTop);
                        if (!Number.isFinite(targetTop)) return;
                        window.requestAnimationFrame(function() {
                            appMain.scrollTop = Math.max(0, targetTop);
                        });
                    });
                }
            })();"""
        ),
    )
