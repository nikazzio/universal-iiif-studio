"""Library page components for local assets management."""

from __future__ import annotations

from urllib.parse import quote

from fasthtml.common import H2, H3, A, Button, Div, Form, Input, Option, P, Select, Span

_STATUS_CLASSES = {
    "saved": "bg-slate-700 text-slate-100",
    "queued": "bg-slate-700 text-slate-100",
    "downloading": "bg-indigo-700 text-indigo-100",
    "running": "bg-indigo-700 text-indigo-100",
    "partial": "bg-amber-700 text-amber-100",
    "complete": "bg-emerald-700 text-emerald-100",
    "error": "bg-rose-700 text-rose-100",
}


def _status_badge(state: str) -> Span:
    key = (state or "saved").lower()
    cls = _STATUS_CLASSES.get(key, "bg-slate-700 text-slate-100")
    return Span(key.upper(), cls=f"text-[10px] px-2 py-1 rounded {cls}")


def _pdf_badges(doc: dict) -> Div:
    has_native = doc.get("has_native_pdf")
    has_local = bool(doc.get("pdf_local_available"))
    badges = []
    if has_native is True:
        badges.append(Span("PDF nativo", cls="text-[10px] px-2 py-1 rounded bg-emerald-900 text-emerald-100"))
    elif has_native is False:
        badges.append(Span("Solo immagini", cls="text-[10px] px-2 py-1 rounded bg-amber-900 text-amber-100"))
    if has_local:
        badges.append(Span("PDF locale", cls="text-[10px] px-2 py-1 rounded bg-indigo-900 text-indigo-100"))
    return Div(*badges, cls="flex gap-1 flex-wrap")


def _doc_actions(doc: dict) -> Div:
    doc_id = quote(str(doc.get("id") or ""), safe="")
    library = quote(str(doc.get("library") or "Unknown"), safe="")
    state = (doc.get("asset_state") or doc.get("status") or "saved").lower()

    actions = [
        A(
            "📖 Studio",
            href=f"/studio?doc_id={doc_id}&library={library}",
            cls="text-xs text-indigo-300 hover:text-indigo-200 underline",
        ),
        Button(
            "🧹 Clean partial",
            cls="text-xs bg-amber-700 hover:bg-amber-600 text-white px-2 py-1 rounded",
            hx_post=f"/api/library/cleanup_partial?doc_id={doc_id}&library={library}",
            hx_target="#library-content",
            hx_swap="innerHTML",
        ),
        Button(
            "🔁 Retry missing",
            cls="text-xs bg-emerald-700 hover:bg-emerald-600 text-white px-2 py-1 rounded",
            hx_post=f"/api/library/retry_missing?doc_id={doc_id}&library={library}",
            hx_target="#library-content",
            hx_swap="innerHTML",
        ),
        Button(
            "🗑️ Delete",
            cls="text-xs bg-rose-700 hover:bg-rose-600 text-white px-2 py-1 rounded",
            hx_post=f"/api/library/delete?doc_id={doc_id}&library={library}",
            hx_confirm="Confermi eliminazione completa del manoscritto locale?",
            hx_target="#library-content",
            hx_swap="innerHTML",
        ),
    ]
    if state in {"saved", "partial", "error"}:
        actions.insert(
            1,
            Button(
                "⬇️ Download",
                cls="text-xs bg-green-700 hover:bg-green-600 text-white px-2 py-1 rounded",
                hx_post=f"/api/library/start_download?doc_id={doc_id}&library={library}",
                hx_target="#library-content",
                hx_swap="innerHTML",
            ),
        )
    return Div(*actions, cls="flex gap-2 flex-wrap")


def _doc_card(doc: dict, *, compact: bool = False) -> Div:
    state = (doc.get("asset_state") or doc.get("status") or "saved").lower()
    total = int(doc.get("total_canvases") or 0)
    downloaded = int(doc.get("downloaded_canvases") or 0)
    item_type = str(doc.get("item_type") or "altro")
    title = str(doc.get("display_title") or doc.get("title") or doc.get("id") or "-")
    subtitle = f"{doc.get('library', 'Unknown')} · {item_type}"
    prog = f"{downloaded}/{total}" if total > 0 else "0/0"

    details = Div(
        H3(title, cls="text-sm font-bold text-slate-100"),
        P(subtitle, cls="text-xs text-slate-400"),
        Div(_status_badge(state), Span(prog, cls="text-[11px] text-slate-300"), cls="mt-2 flex items-center gap-2"),
        _pdf_badges(doc),
        P(str(doc.get("id") or "-"), cls="text-[10px] text-slate-500 font-mono mt-1"),
        _doc_actions(doc),
        cls="space-y-2",
    )
    if compact:
        return Div(details, cls="bg-slate-900/40 border border-slate-700 rounded-lg p-3")
    return Div(details, cls="bg-slate-900/50 border border-slate-700 rounded-lg p-4")


def render_library_list(docs: list[dict], view: str = "grid") -> Div:
    """Render grouped library entries in grid/list mode."""
    if not docs:
        return Div(P("Nessun asset locale trovato.", cls="text-sm text-slate-400"), id="library-content")

    grouped: dict[str, dict[str, list[dict]]] = {}
    for d in docs:
        lib = str(d.get("library") or "Unknown")
        typ = str(d.get("item_type") or "altro")
        grouped.setdefault(lib, {}).setdefault(typ, []).append(d)

    sections = []
    for lib in sorted(grouped.keys()):
        type_blocks = []
        for typ in sorted(grouped[lib].keys()):
            entries = grouped[lib][typ]
            cards = [_doc_card(doc, compact=view == "list") for doc in entries]
            grid_cls = "space-y-3" if view == "list" else "grid sm:grid-cols-2 xl:grid-cols-2 gap-3"
            type_blocks.append(
                Div(
                    H3(f"{typ.title()} ({len(entries)})", cls="text-sm font-semibold text-slate-200 mb-2"),
                    Div(*cards, cls=grid_cls),
                    cls="mb-5",
                )
            )
        sections.append(
            Div(
                H2(lib, cls="text-xl font-bold text-slate-100 mb-3"),
                Div(*type_blocks),
                cls="mb-8",
            )
        )
    return Div(*sections, id="library-content")


def render_library_page(docs: list[dict], *, view: str = "grid", q: str = "", state: str = "") -> Div:
    """Render the full Local Library page."""
    return Div(
        H2("📚 Libreria Locale", cls="text-2xl font-bold text-slate-100 mb-4"),
        Form(
            Div(
                Input(
                    type="text",
                    name="q",
                    value=q,
                    placeholder="Cerca titolo / id / biblioteca",
                    cls="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-100 text-sm",
                ),
                Select(
                    Option("Tutti gli stati", value=""),
                    Option("Saved", value="saved", selected=state == "saved"),
                    Option("Queued", value="queued", selected=state == "queued"),
                    Option("Downloading", value="downloading", selected=state == "downloading"),
                    Option("Partial", value="partial", selected=state == "partial"),
                    Option("Complete", value="complete", selected=state == "complete"),
                    Option("Error", value="error", selected=state == "error"),
                    name="state",
                    cls="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-100 text-sm",
                ),
                Select(
                    Option("Grid", value="grid", selected=view == "grid"),
                    Option("List", value="list", selected=view == "list"),
                    name="view",
                    cls="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-100 text-sm",
                ),
                Button(
                    "Applica",
                    cls="px-4 py-2 bg-indigo-700 hover:bg-indigo-600 text-white rounded text-sm",
                    type="submit",
                ),
                cls="flex flex-wrap gap-2",
            ),
            hx_get="/library",
            hx_target="#app-main",
            hx_swap="innerHTML",
            hx_push_url="true",
            cls="mb-6",
        ),
        render_library_list(docs, view=view),
        cls="p-6 max-w-7xl mx-auto",
    )
