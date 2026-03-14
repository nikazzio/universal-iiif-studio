"""Discovery search results and preview renderers."""

import json
from urllib.parse import quote

from fasthtml.common import H3, A, Button, Div, Img, P, Span


def _provider_viewer_fallback(library: str, doc_id: str, ark: str = "") -> str:
    if library == "Gallica" and ark:
        return f"https://gallica.bnf.fr/{ark}"
    if library == "Gallica" and doc_id:
        return f"https://gallica.bnf.fr/ark:/12148/{doc_id}"
    if library == "Vaticana" and doc_id:
        return f"https://digi.vatlib.it/view/{doc_id}"
    if library == "Institut de France" and doc_id:
        return f"https://bibnum.institutdefrance.fr/viewer/{doc_id}"
    if library == "Bodleian" and doc_id:
        return f"https://digital.bodleian.ox.ac.uk/objects/{doc_id}"
    if library == "Archive.org" and doc_id:
        return f"https://archive.org/details/{doc_id}"
    return ""


def _resolve_viewer_url(data: dict) -> str:
    """Return the provider viewer URL from normalized result data."""
    viewer_url = str(data.get("viewer_url") or "").strip()
    raw = data.get("raw")
    if not viewer_url and isinstance(raw, dict):
        viewer_url = str(raw.get("viewer_url") or "").strip()
    if viewer_url:
        return viewer_url
    return _provider_viewer_fallback(
        str(data.get("library") or ""),
        str(data.get("id") or ""),
        str(data.get("ark") or ""),
    )


def _build_discovery_hx_vals(manifest_url: str, doc_id: str, library: str, result_title: str) -> str:
    return json.dumps(
        {
            "manifest_url": manifest_url,
            "doc_id": doc_id,
            "library": library,
            "result_title": result_title,
        },
        ensure_ascii=True,
    )


def _build_pdf_badge(manifest_url: str, badge_id: str, *, cls: str) -> Div:
    return Div(
        "PDF: verifica automatica…",
        id=badge_id,
        hx_get=f"/api/discovery/pdf_capability?manifest_url={quote(manifest_url, safe='')}",
        hx_trigger="load",
        hx_swap="outerHTML",
        cls=cls,
    )


def render_search_results_list(results: list) -> Div:
    """Render list of search results aligned with global app theme."""
    cards = []
    for item in results:
        title = str(item.get("title") or "Senza titolo")
        author = str(item.get("author") or "")
        date = str(item.get("date") or "")
        language = str(item.get("language") or "")
        publisher = str(item.get("publisher") or "")
        library = str(item.get("library") or "Gallica")
        description = str(item.get("description") or "")
        thumb = item.get("thumbnail")
        doc_id = str(item.get("id") or "")
        manifest_url = str(item.get("manifest") or "")
        viewer_url = _resolve_viewer_url(item)
        hx_vals = _build_discovery_hx_vals(manifest_url, doc_id, library, title)
        badge_id = f"pdf-badge-{(doc_id or 'item').replace(' ', '-').replace('/', '-')[:28]}"
        pdf_badge = _build_pdf_badge(
            manifest_url,
            badge_id,
            cls="app-chip app-chip-neutral text-[11px] tracking-wide",
        )

        meta_line = []
        if author and author != "Autore sconosciuto":
            meta_line.append(Span(f"Autore: {author[:70]}", cls="text-xs text-slate-600 dark:text-slate-300"))
        if date:
            meta_line.append(Span(f"Data: {date}", cls="text-xs text-slate-600 dark:text-slate-300"))
        if language:
            meta_line.append(Span(f"Lingua: {language.upper()}", cls="text-xs text-slate-600 dark:text-slate-300"))
        if publisher:
            meta_line.append(Span(f"Fonte: {publisher[:80]}", cls="text-xs text-slate-600 dark:text-slate-300"))

        cards.append(
            Div(
                Div(
                    Img(
                        src=thumb,
                        cls="w-24 h-24 object-cover rounded-lg border border-slate-200 dark:border-slate-700",
                    )
                    if thumb
                    else Div(
                        "No preview",
                        cls=(
                            "w-24 h-24 rounded-lg border border-dashed border-slate-300 dark:border-slate-700 "
                            "text-[11px] text-slate-500 flex items-center justify-center"
                        ),
                    ),
                    cls="shrink-0",
                ),
                Div(
                    Div(
                        H3(title[:140], cls="text-base font-semibold text-slate-900 dark:text-slate-100 leading-tight"),
                        Div(
                            Span(library, cls="app-chip app-chip-primary text-[11px] tracking-wide"),
                            Span(
                                (doc_id[:40] + "...") if len(doc_id) > 40 else doc_id,
                                cls="app-chip app-chip-neutral text-[11px] font-mono",
                            ),
                            pdf_badge,
                            cls="flex flex-wrap items-center gap-2",
                        ),
                        cls="flex flex-col gap-2",
                    ),
                    P(
                        description[:220] + ("..." if len(description) > 220 else ""),
                        cls="text-sm text-slate-600 dark:text-slate-300",
                    )
                    if description
                    else "",
                    Div(*meta_line, cls="flex flex-wrap gap-x-4 gap-y-1") if meta_line else "",
                    Div(
                        A("Apri viewer", href=viewer_url, target="_blank", cls="app-btn app-btn-info text-xs")
                        if viewer_url
                        else "",
                        Button(
                            "Aggiungi",
                            cls="app-btn app-btn-neutral text-xs",
                            hx_post="/api/discovery/add_to_library",
                            hx_vals=hx_vals,
                            hx_target="#download-manager-area",
                            hx_swap="innerHTML",
                        ),
                        Button(
                            "Aggiungi + Download",
                            cls="app-btn app-btn-accent text-xs",
                            hx_post="/api/discovery/add_and_download",
                            hx_vals=hx_vals,
                            hx_target="#download-manager-area",
                            hx_swap="innerHTML",
                        ),
                        cls="flex flex-wrap items-center gap-2 pt-1",
                    ),
                    cls="min-w-0 flex-1 space-y-2",
                ),
                cls=(
                    "flex flex-col md:flex-row gap-4 rounded-xl border border-slate-200/80 dark:border-slate-700 "
                    "bg-white/90 dark:bg-slate-900/55 p-4 shadow-sm"
                ),
            )
        )

    return Div(
        Div(
            H3(f"Trovati {len(results)} risultati", cls="text-lg font-semibold text-slate-900 dark:text-slate-100"),
            Span(
                "Seleziona un risultato per aggiungerlo in Libreria o avviare il download.",
                cls="text-xs text-slate-500",
            ),
            cls=(
                "flex flex-col md:flex-row md:items-end md:justify-between gap-2 mb-4 pb-3 border-b "
                "border-slate-200 dark:border-slate-700"
            ),
        ),
        Div(*cards, cls="space-y-3 max-h-[640px] overflow-y-auto pr-1"),
        id="discovery-preview",
    )


_FEEDBACK_STYLES = {
    "success": {
        "icon": "✅",
        "card": "bg-emerald-950/25 border-emerald-500/45",
        "title": "text-emerald-200",
        "details": "text-emerald-100/90",
    },
    "info": {
        "icon": "ℹ️",
        "card": "bg-sky-950/25 border-sky-500/45",
        "title": "text-sky-200",
        "details": "text-sky-100/90",
    },
    "danger": {
        "icon": "⚠️",
        "card": "bg-rose-950/30 border-rose-500/45",
        "title": "text-rose-200",
        "details": "text-rose-100/90",
    },
}


def render_feedback_message(title: str, details: str = "", tone: str = "info") -> Div:
    """Render inline feedback styled consistently with Discovery result cards."""
    palette = _FEEDBACK_STYLES.get(tone, _FEEDBACK_STYLES["info"])
    return Div(
        Div(palette["icon"], cls="text-lg leading-none mt-0.5"),
        Div(
            P(title, cls=f"text-sm font-bold {palette['title']}"),
            P(details, cls=f"text-xs mt-1 {palette['details']}") if details else "",
        ),
        cls=(
            "flex items-start gap-3 p-3 rounded-lg border transition-all mb-2 "
            "shadow-sm " + palette["card"] + " hover:bg-slate-800/80"
        ),
    )


def render_error_message(title: str, details: str = "") -> Div:
    """Render error feedback with Discovery styling."""
    return render_feedback_message(title, details, tone="danger")


def render_preview(data: dict) -> Div:
    """Render preview block for a manifest."""
    pages = int(data.get("pages", 0))
    doc_id = data.get("id", "")
    library = data.get("library", "")
    manifest_url = data.get("url", "")
    label = data.get("label", "Senza Titolo")
    description = data.get("description", "")
    thumbnail = data.get("thumbnail", "")
    has_native_pdf = data.get("has_native_pdf")
    result_title = str(data.get("result_title") or label or "")

    warning = None
    if pages > 500:
        warning = Div(
            f"⚠️ Questo manoscritto contiene molte pagine ({pages}). Il download richiederà tempo.",
            cls=(
                "text-xs text-amber-800 dark:text-amber-200 mb-4 bg-amber-50 "
                "dark:bg-amber-900/30 p-3 rounded border border-amber-200 dark:border-amber-700"
            ),
        )

    viewer_url = _resolve_viewer_url(data)
    viewer_link = (
        A(
            "🔗 Apri nel viewer originale",
            href=viewer_url,
            target="_blank",
            cls="text-sm text-blue-400 hover:text-blue-300 underline",
        )
        if viewer_url
        else None
    )

    img_col = Div(
        Img(src=thumbnail, cls="w-32 h-32 object-cover rounded-lg border border-slate-600")
        if thumbnail
        else Div(
            "📜",
            cls="w-32 h-32 bg-slate-800 rounded-lg flex items-center justify-center text-4xl",
        ),
        cls="flex-shrink-0 mr-6",
    )

    meta_items = [
        Span(f"📚 {library}", cls="text-xs bg-indigo-900/50 text-indigo-300 px-2 py-1 rounded"),
        Span(f"📄 {pages} pagine", cls="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded"),
    ]
    if has_native_pdf is True:
        meta_items.append(
            Span(
                "PDF nativo disponibile",
                cls="text-xs bg-emerald-800 text-emerald-100 px-2 py-1 rounded",
            )
        )
    elif has_native_pdf is False:
        meta_items.append(Span("Solo immagini", cls="text-xs bg-amber-800 text-amber-100 px-2 py-1 rounded"))
    else:
        meta_items.append(
            _build_pdf_badge(
                str(manifest_url or ""),
                "preview-pdf-badge",
                cls="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded",
            )
        )

    id_badge = Span(
        doc_id,
        cls="text-xs bg-slate-700 text-slate-400 px-2 py-1 rounded font-mono",
    )

    txt_col = Div(
        H3(label, cls="text-xl font-bold text-slate-100 mb-2"),
        P(description[:200] + ("..." if len(description) > 200 else ""), cls="text-sm text-slate-400 mb-3 italic")
        if description
        else "",
        Div(*meta_items, id_badge, cls="flex flex-wrap gap-2 mb-3"),
        viewer_link if viewer_link else "",
        cls="flex-grow",
    )

    hx_vals = _build_discovery_hx_vals(
        str(manifest_url or ""),
        str(doc_id or ""),
        str(library or ""),
        result_title,
    )
    download_form = Div(
        Button(
            Span("➕ Aggiungi a Libreria", cls="font-bold"),
            cls=(
                "w-full py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg "
                "transition-all shadow-lg hover:shadow-xl active:scale-95 "
                "flex items-center justify-center gap-2 text-sm"
            ),
            hx_post="/api/discovery/add_to_library",
            hx_vals=hx_vals,
            hx_target="#download-manager-area",
            hx_swap="innerHTML",
        ),
        Button(
            Span("🚀 Aggiungi + Download", cls="font-bold"),
            cls=(
                "w-full py-4 bg-green-600 hover:bg-green-700 text-white rounded-lg "
                "transition-all shadow-lg hover:shadow-xl active:scale-95 "
                "flex items-center justify-center gap-2 text-lg"
            ),
            hx_post="/api/discovery/add_and_download",
            hx_vals=hx_vals,
            hx_target="#download-manager-area",
            hx_swap="innerHTML",
        ),
        cls="grid gap-3",
    )

    return Div(
        warning if warning else "",
        Div(
            img_col,
            txt_col,
            cls="flex items-start mb-6",
        ),
        download_form,
        id="discovery-preview",
        cls=(
            "bg-slate-800/60 p-6 rounded-lg border border-slate-700 animate-in fade-in slide-in-from-top-4 duration-300"
        ),
    )


def render_pdf_capability_badge(has_pdf: bool) -> Div:
    """Render a compact badge for native PDF availability."""
    if has_pdf:
        return Div("PDF nativo disponibile", cls="app-chip app-chip-success text-[11px] tracking-wide")
    return Div("Solo immagini", cls="app-chip app-chip-warning text-[11px] tracking-wide")

