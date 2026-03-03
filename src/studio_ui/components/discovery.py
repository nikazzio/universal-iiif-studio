"""Rendering helpers for the Discovery routes."""

import json
from urllib.parse import quote

from fasthtml.common import (
    H2,
    H3,
    A,
    Button,
    Div,
    Form,
    Img,
    Input,
    Label,
    Option,
    P,
    Script,
    Select,
    Span,
)

from studio_ui.common.title_utils import resolve_preferred_title, truncate_title
from studio_ui.library_options import library_options


def render_search_results_list(results: list) -> Div:
    """Render list of search results aligned with global app theme."""
    cards = []
    for item in results:
        title = str(item.get("title") or "Senza titolo")
        author = str(item.get("author") or "")
        date = str(item.get("date") or "")
        language = str(item.get("language") or "")
        publisher = str(item.get("publisher") or "")
        ark = str(item.get("ark") or "")
        library = str(item.get("library") or "Gallica")
        description = str(item.get("description") or "")
        thumb = item.get("thumbnail")
        doc_id = str(item.get("id") or "")
        manifest_url = str(item.get("manifest") or "")

        viewer_url = None
        if library == "Gallica" and ark:
            viewer_url = f"https://gallica.bnf.fr/{ark}"
        elif library == "Gallica" and doc_id:
            viewer_url = f"https://gallica.bnf.fr/ark:/12148/{doc_id}"
        elif library == "Vaticana" and doc_id:
            viewer_url = f"https://digi.vatlib.it/view/{doc_id}"
        elif library == "Institut de France" and doc_id:
            viewer_url = f"https://bibnum.institutdefrance.fr/viewer/{doc_id}"

        hx_vals = json.dumps({"manifest_url": manifest_url, "doc_id": doc_id, "library": library}, ensure_ascii=True)
        badge_id = f"pdf-badge-{(doc_id or 'item').replace(' ', '-').replace('/', '-')[:28]}"
        pdf_badge = Div(
            Div("PDF: n/d", id=badge_id, cls="app-chip app-chip-neutral text-[11px] tracking-wide"),
            Button(
                "Verifica PDF",
                type="button",
                hx_get=f"/api/discovery/pdf_capability?manifest_url={quote(manifest_url, safe='')}",
                hx_target=f"#{badge_id}",
                hx_swap="outerHTML",
                cls="app-btn app-btn-neutral text-[11px] px-2 py-1",
            ),
            cls="flex items-center gap-1.5",
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
    """Renderizza un messaggio di errore con stile coerente ai risultati Discovery."""
    return render_feedback_message(title, details, tone="danger")


def discovery_form() -> Div:
    """Form component for discovery searches."""
    libraries = library_options()

    return Div(
        H3("Ricerca", cls="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-1"),
        P(
            "Inserisci testo libero, segnatura, ID o URL. I filtri sono opzionali.",
            cls="text-sm text-slate-600 dark:text-slate-300 mb-4",
        ),
        Form(
            Div(
                Div(
                    Label(
                        "Cerca",
                        for_="shelf-input",
                        cls="app-label mb-1",
                    ),
                    Input(
                        type="text",
                        id="shelf-input",
                        name="shelfmark",
                        placeholder="es. Les voyages du seigneur de Villamont",
                        cls="app-field text-base py-3 px-3.5",
                    ),
                    cls="col-span-12 lg:col-span-8",
                ),
                Div(
                    Button(
                        "Analizza Documento",
                        type="submit",
                        cls="w-full app-btn app-btn-accent font-semibold py-3",
                    ),
                    cls="col-span-12 lg:col-span-4 flex items-end",
                ),
                Div(
                    Label(
                        "Biblioteca",
                        for_="lib-select",
                        cls="app-label mb-1",
                    ),
                    Select(
                        *[Option(label, value=value) for label, value in libraries],
                        id="lib-select",
                        name="library",
                        cls="app-field",
                    ),
                    cls="col-span-12 md:col-span-6 lg:col-span-4",
                ),
                Div(
                    Label(
                        "Filtro (Gallica)",
                        for_="gallica-type",
                        cls="app-label mb-1",
                    ),
                    Select(
                        Option("Tutti i materiali", value="all", selected=True),
                        Option("Solo manoscritti", value="manuscrit"),
                        Option("Solo libri a stampa", value="printed"),
                        id="gallica-type",
                        name="gallica_type",
                        cls="app-field",
                    ),
                    id="gallica-filter-wrap",
                    cls="col-span-12 md:col-span-6 lg:col-span-4",
                ),
                cls="grid grid-cols-12 gap-4",
            ),
            hx_post="/api/resolve_manifest",
            hx_target="#discovery-preview",
            hx_indicator="#resolve-spinner",
        ),
        Script(
            """
            (function () {
                const lib = document.getElementById('lib-select');
                const wrap = document.getElementById('gallica-filter-wrap');
                const select = document.getElementById('gallica-type');
                if (!lib || !wrap || !select) return;
                const sync = () => {
                    const isGallica = (lib.value || '').toLowerCase().includes('gallica');
                    wrap.style.display = isGallica ? '' : 'none';
                    select.disabled = !isGallica;
                    if (!isGallica) select.value = 'all';
                };
                lib.addEventListener('change', sync);
                sync();
            })();
            """
        ),
        # Spinner
        Div(
            Div(
                cls=(
                    "inline-block w-8 h-8 border-[3px] border-[rgba(var(--app-accent-rgb),0.55)] "
                    "border-t-transparent rounded-full animate-spin"
                )
            ),
            id="resolve-spinner",
            cls="htmx-indicator flex justify-center mt-6",
        ),
        cls=(
            "rounded-xl border border-slate-200/80 dark:border-slate-700 bg-white/90 dark:bg-slate-900/50 p-5 shadow-sm"
        ),
    )


def discovery_content(initial_preview=None, active_download_fragment=None) -> Div:
    """Top-level content block for the discovery page.

    Args:
        initial_preview: Optional fragment to render inside the preview area
            (replaces the default empty `#discovery-preview` div).
        active_download_fragment: Optional fragment to render in the dedicated
            downloads area (separate from search preview/result area).
    """
    preview_block = initial_preview if initial_preview is not None else Div(id="discovery-preview", cls="mt-8")
    downloads_block = (
        active_download_fragment if active_download_fragment is not None else Div(id="download-manager-area")
    )

    return Div(
        H2("Discovery", cls="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-5"),
        Div(
            Div(
                discovery_form(),
                preview_block,
                cls="w-full xl:w-[66%] xl:pr-4",
            ),
            Div(
                H3("Download Manager", cls="text-lg font-semibold text-slate-700 dark:text-slate-200 mb-2"),
                downloads_block,
                cls="w-full xl:w-[34%] xl:sticky xl:top-6 self-start",
            ),
            cls="flex flex-col xl:flex-row gap-6",
        ),
        cls="p-6 max-w-7xl mx-auto",
    )


def render_preview(data: dict) -> Div:
    """Render preview block for a manifest (unified style with search results)."""
    pages = int(data.get("pages", 0))
    doc_id = data.get("id", "")
    library = data.get("library", "")
    manifest_url = data.get("url", "")
    label = data.get("label", "Senza Titolo")
    description = data.get("description", "")
    thumbnail = data.get("thumbnail", "")
    has_native_pdf = data.get("has_native_pdf")

    # Warning se ci sono troppe pagine
    warning = None
    if pages > 500:
        warning = Div(
            f"⚠️ Questo manoscritto contiene molte pagine ({pages}). Il download richiederà tempo.",
            cls=(
                "text-xs text-amber-800 dark:text-amber-200 mb-4 bg-amber-50 "
                "dark:bg-amber-900/30 p-3 rounded border border-amber-200 dark:border-amber-700"
            ),
        )

    # Link al viewer originale
    viewer_url = None
    if library == "Gallica":
        viewer_url = f"https://gallica.bnf.fr/ark:/12148/{doc_id}"
    elif library == "Vaticana":
        viewer_url = f"https://digi.vatlib.it/view/{doc_id}"
    elif library == "Institut de France":
        viewer_url = f"https://bibnum.institutdefrance.fr/viewer/{doc_id}"
    elif library == "Bodleian":
        viewer_url = f"https://digital.bodleian.ox.ac.uk/objects/{doc_id}"

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

    # Thumbnail
    img_col = Div(
        Img(src=thumbnail, cls="w-32 h-32 object-cover rounded-lg border border-slate-600")
        if thumbnail
        else Div(
            "📜",
            cls="w-32 h-32 bg-slate-800 rounded-lg flex items-center justify-center text-4xl",
        ),
        cls="flex-shrink-0 mr-6",
    )

    # Metadata badges
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
            Div(
                Div(
                    "PDF: n/d",
                    id="preview-pdf-badge",
                    cls="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded",
                ),
                Button(
                    "Verifica PDF",
                    type="button",
                    hx_get=f"/api/discovery/pdf_capability?manifest_url={quote(str(manifest_url or ''), safe='')}",
                    hx_target="#preview-pdf-badge",
                    hx_swap="outerHTML",
                    cls="app-btn app-btn-neutral text-[11px] px-2 py-1",
                ),
                cls="inline-flex items-center gap-1.5",
            )
        )

    # ID badge
    id_badge = Span(
        doc_id,
        cls="text-xs bg-slate-700 text-slate-400 px-2 py-1 rounded font-mono",
    )

    # Content column
    txt_col = Div(
        H3(label, cls="text-xl font-bold text-slate-100 mb-2"),
        P(description[:200] + ("..." if len(description) > 200 else ""), cls="text-sm text-slate-400 mb-3 italic")
        if description
        else "",
        Div(*meta_items, id_badge, cls="flex flex-wrap gap-2 mb-3"),
        viewer_link if viewer_link else "",
        cls="flex-grow",
    )

    hx_vals = f'{{"manifest_url": "{manifest_url}", "doc_id": "{doc_id}", "library": "{library}"}}'
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


def render_download_status(download_id: str, doc_id: str, library: str, status_data: dict) -> Div:
    """Render the download status (Progress Bar or Success Card) - unified slate theme."""
    percent = status_data.get("percent", 0)
    status = status_data.get("status", "running")
    current = status_data.get("current", 0)
    total = status_data.get("total", 0)
    error = status_data.get("error")
    title = status_data.get("title") or doc_id

    # Common styles
    card_cls = "bg-slate-800/60 p-6 rounded-lg border border-slate-700 shadow-sm"
    header_title_cls = "text-lg font-bold text-slate-100"
    badge_cls = "text-xs bg-indigo-900/50 text-indigo-300 px-2 py-1 rounded ml-2"
    subtext_cls = "text-sm text-slate-400 mt-1"
    percent_cls = "text-3xl font-extrabold text-indigo-400"
    progress_bg_cls = "w-full bg-slate-700 rounded-full h-2.5 mb-2"
    progress_bar_cls = "bg-indigo-500 h-2.5 rounded-full transition-all duration-500 ease-out"

    # 1.b Stopping states
    if status in {"cancelling", "pausing"}:
        header = Div(
            Div(
                H3(title, cls=header_title_cls),
                Span(library, cls=badge_cls),
                cls="flex items-center justify-between",
            ),
            P(f"{current}/{total} pagine", cls=subtext_cls),
            cls="mb-4",
        )

        percent_block = Div(
            Div(f"{percent}%", cls=percent_cls),
            P(
                "Annullamento..." if status == "cancelling" else "Messa in pausa...",
                cls="text-sm text-red-400" if status == "cancelling" else "text-sm text-amber-300",
            ),
            cls="flex items-center gap-4 mb-4",
        )

        progress_bar = Div(Div(Div(cls=progress_bar_cls, style=f"width: {percent}%"), cls=progress_bg_cls))

        body = Div(
            header,
            percent_block,
            progress_bar,
            P(
                "Annullamento in corso..." if status == "cancelling" else "Pausa in corso...",
                cls="text-xs text-slate-500 italic",
            ),
        )

        return Div(
            body,
            hx_get=f"/api/download_status/{download_id}?doc_id={doc_id}&library={library}",
            hx_trigger="every 1s",
            hx_swap="outerHTML",
            cls=card_cls,
        )

    # 1. Caso Errore
    if status in {"error", "failed"}:
        return render_error_message("Errore durante il download", str(error or status))

    # 1.c Terminal stop states (must not keep polling)
    if status in {"paused", "cancelled"}:
        icon = "⏸️" if status == "paused" else "🛑"
        title_text = "Download in pausa" if status == "paused" else "Download annullato"
        detail_text = (
            f"Il download di '{doc_id}' è in pausa. Puoi riprenderlo dal Download Manager."
            if status == "paused"
            else f"Il download di '{doc_id}' è stato annullato."
        )
        return Div(
            Div(
                Span(icon, cls="text-4xl mb-4 block"),
                H3(title_text, cls="text-xl font-bold text-slate-100 mb-2"),
                P(detail_text, cls="text-slate-400 mb-2"),
                P(f"Stato finale: {status.upper()}", cls="text-xs text-slate-500"),
                cls="text-center",
            ),
            cls="bg-slate-900/40 border border-slate-700 p-8 rounded-lg shadow-sm",
        )

    # 2. Caso Completato
    if percent >= 100 or status == "completed":
        from urllib.parse import quote

        encoded_lib = quote(library)
        encoded_doc = quote(doc_id)

        return Div(
            Div(
                Span("✅", cls="text-4xl mb-4 block"),
                H3("Download Completato!", cls="text-xl font-bold text-green-400 mb-2"),
                P(
                    f"Il manoscritto '{doc_id}' è stato salvato correttamente.",
                    cls="text-slate-400 mb-6",
                ),
                A(
                    Button(
                        "📖 Apri nello Studio",
                        cls=(
                            "bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg shadow-md "
                            "transition-transform hover:scale-105"
                        ),
                    ),
                    href=f"/studio?library={encoded_lib}&doc_id={encoded_doc}",
                    cls="inline-block",
                ),
                cls="text-center",
            ),
            cls=("bg-green-900/20 border border-green-800 p-8 rounded-lg shadow-sm animate-in zoom-in duration-300"),
        )

    # 3. Caso In Corso
    controls = Div(
        Button(
            "⛔ Annulla",
            cls="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded-lg shadow-sm transition-all",
            hx_post=f"/api/cancel_download/{download_id}?doc_id={doc_id}&library={library}",
            hx_target="#discovery-preview",
            hx_swap="outerHTML",
        ),
        cls="mt-4 flex justify-end",
    )

    header = Div(
        Div(
            H3(title, cls=header_title_cls),
            Span(library, cls=badge_cls),
            cls="flex items-center justify-between",
        ),
        P(f"{current}/{total} pagine", cls=subtext_cls),
        cls="mb-4",
    )

    percent_block = Div(
        Div(f"{percent}%", cls=percent_cls),
        P("Scaricamento in corso...", cls="text-sm text-slate-500"),
        cls="flex items-center gap-4 mb-4",
    )

    progress_bar = Div(Div(Div(cls=progress_bar_cls, style=f"width: {percent}%"), cls=progress_bg_cls))

    body = Div(
        header,
        percent_block,
        progress_bar,
        P("Ottimizzazione immagini e salvataggio...", cls="text-xs text-slate-500 italic animate-pulse"),
    )

    return Div(
        body,
        controls,
        hx_get=f"/api/download_status/{download_id}?doc_id={doc_id}&library={library}",
        hx_trigger="every 1s",
        hx_swap="outerHTML",
        cls=card_cls,
    )


def render_pdf_capability_badge(has_pdf: bool) -> Div:
    """Render a compact badge for native PDF availability."""
    if has_pdf:
        return Div("PDF nativo disponibile", cls="app-chip app-chip-success text-[11px] tracking-wide")
    return Div("Solo immagini", cls="app-chip app-chip-warning text-[11px] tracking-wide")


def render_download_manager(jobs: list[dict]) -> Div:
    """Render the full download manager panel."""
    active_statuses = {"queued", "running", "cancelling", "pausing", "pending", "starting"}
    should_poll = any(str(job.get("status") or "").lower() in active_statuses for job in jobs)

    if not jobs:
        body = Div(
            P("Nessun download in coda.", cls="text-sm text-slate-400"),
            P("Puoi continuare a cercare mentre i download vengono eseguiti qui.", cls="text-xs text-slate-500 mt-1"),
            cls="bg-slate-900/40 border border-slate-700 rounded-lg p-4",
        )
    else:
        cards = [render_download_job_card(job) for job in jobs]
        body = Div(*cards, cls="space-y-3")

    attrs = {
        "id": "download-manager-area",
        "cls": "space-y-2",
    }
    if should_poll:
        attrs.update(
            {
                "hx_get": "/api/download_manager",
                "hx_trigger": "every 1s",
                "hx_swap": "outerHTML",
            }
        )

    return Div(body, **attrs)


def _download_job_badge(status: str, queue_position: int) -> tuple[str, str]:
    badge_map = {
        "running": "bg-indigo-800 text-indigo-100",
        "queued": "bg-slate-700 text-slate-100",
        "cancelling": "bg-amber-700 text-amber-100",
        "pausing": "bg-amber-700 text-amber-100",
        "paused": "bg-violet-800 text-violet-100",
        "completed": "bg-emerald-700 text-emerald-100",
        "cancelled": "bg-slate-700 text-slate-200",
        "error": "bg-rose-700 text-rose-100",
    }
    badge_cls = badge_map.get(status, "bg-slate-700 text-slate-100")
    badge_text = status.upper()
    if status == "queued" and queue_position > 0:
        badge_text = f"QUEUED #{queue_position}"
    return badge_cls, badge_text


def _download_job_actions(status: str, job_id: str, doc_id: str, library: str) -> tuple[list, list]:
    left_actions: list = []
    right_actions: list = []

    if status in {"running", "queued"}:
        left_actions.append(
            Button(
                "⏸️ Pausa",
                cls=(
                    "inline-flex items-center gap-1.5 text-xs font-semibold "
                    "bg-amber-700 hover:bg-amber-600 text-white px-3 py-1.5 rounded-md "
                    "border border-amber-500/60 shadow-sm transition-colors"
                ),
                hx_post=f"/api/download_manager/pause/{job_id}",
                hx_target="#download-manager-area",
                hx_swap="outerHTML",
            )
        )
    if status == "queued":
        left_actions.append(
            Button(
                "⬆️ Priorità",
                cls=(
                    "inline-flex items-center gap-1.5 text-xs font-semibold "
                    "bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded-md "
                    "border border-slate-500/60 shadow-sm transition-colors"
                ),
                hx_post=f"/api/download_manager/prioritize/{job_id}",
                hx_target="#download-manager-area",
                hx_swap="outerHTML",
            )
        )
    if status == "paused":
        left_actions.append(
            Button(
                "▶️ Riprendi",
                cls=(
                    "inline-flex items-center gap-1.5 text-xs font-semibold "
                    "bg-emerald-700 hover:bg-emerald-600 text-white px-3 py-1.5 rounded-md "
                    "border border-emerald-500/60 shadow-sm transition-colors"
                ),
                hx_post=f"/api/download_manager/resume/{job_id}",
                hx_target="#download-manager-area",
                hx_swap="outerHTML",
            )
        )
    if status in {"error", "cancelled"}:
        left_actions.append(
            Button(
                "🔁 Retry",
                cls=(
                    "inline-flex items-center gap-1.5 text-xs font-semibold "
                    "bg-emerald-700 hover:bg-emerald-600 text-white px-3 py-1.5 rounded-md "
                    "border border-emerald-500/60 shadow-sm transition-colors"
                ),
                hx_post=f"/api/download_manager/retry/{job_id}",
                hx_target="#download-manager-area",
                hx_swap="outerHTML",
            )
        )
    if status == "completed":
        left_actions.append(
            A(
                Button(
                    "📖 Vai allo Studio",
                    cls=(
                        "inline-flex items-center gap-1.5 text-xs font-semibold "
                        "bg-indigo-700 hover:bg-indigo-600 text-white px-3 py-1.5 rounded-md "
                        "border border-indigo-500/60 shadow-sm transition-colors"
                    ),
                ),
                href=f"/studio?doc_id={quote(doc_id)}&library={quote(library)}",
                cls="inline-block",
            )
        )

    if status in {"running", "queued", "cancelling", "pausing"}:
        right_actions.append(
            Button(
                "⛔ Annulla",
                cls=(
                    "inline-flex items-center gap-1.5 text-xs font-semibold "
                    "bg-rose-700 hover:bg-rose-600 text-white px-3 py-1.5 rounded-md "
                    "border border-rose-500/60 shadow-sm transition-colors"
                ),
                hx_post=f"/api/download_manager/cancel/{job_id}",
                hx_target="#download-manager-area",
                hx_swap="outerHTML",
            )
        )
    if status in {"error", "cancelled", "completed", "paused"}:
        right_actions.append(
            Button(
                "🗑️ Rimuovi",
                cls=(
                    "inline-flex items-center gap-1.5 text-xs font-semibold "
                    "bg-slate-800 hover:bg-slate-700 text-slate-100 px-3 py-1.5 rounded-md "
                    "border border-slate-600 shadow-sm transition-colors"
                ),
                hx_post=f"/api/download_manager/remove/{job_id}",
                hx_target="#download-manager-area",
                hx_swap="outerHTML",
            )
        )
    return left_actions, right_actions


def _download_job_progress(status: str, current: int, total: int, percent: int, error: str) -> Div:
    counts_line = P(f"{current}/{total} pagine", cls="text-[11px] text-slate-400 mt-1")
    progress = Div(
        Div(
            Div(cls="h-2 rounded bg-indigo-500", style=f"width: {percent}%"),
            cls="w-full bg-slate-700 rounded h-2",
        ),
        P(f"{current}/{total} ({percent}%)", cls="text-[11px] text-slate-400 mt-1") if total > 0 else counts_line,
        cls="mt-2",
    )
    if status == "queued":
        return Div(counts_line, P("In attesa di uno slot libero...", cls="text-[11px] text-slate-400 mt-2"), cls="mt-1")
    if status == "cancelling":
        return Div(
            counts_line,
            P("Richiesta di arresto in corso...", cls="text-[11px] text-amber-300 mt-2"),
            cls="mt-1",
        )
    if status == "pausing":
        return Div(counts_line, P("Messa in pausa in corso...", cls="text-[11px] text-amber-300 mt-2"), cls="mt-1")
    if status == "paused":
        return Div(counts_line, P("Download in pausa.", cls="text-[11px] text-violet-300 mt-2"), cls="mt-1")
    if status == "cancelled":
        return Div(
            counts_line,
            P("Download annullato dall'utente.", cls="text-[11px] text-slate-300 mt-2"),
            cls="mt-1",
        )
    if status == "error" and error:
        return Div(counts_line, P(error, cls="text-[11px] text-rose-300 mt-2"), cls="mt-1")
    return progress


def render_download_job_card(job: dict) -> Div:
    """Render a single card inside the Download Manager list."""
    status = str(job.get("status") or "queued")
    doc_id = str(job.get("doc_id") or "-")
    library = str(job.get("library") or "-")
    job_id = str(job.get("job_id") or "")
    current = int(job.get("current", 0) or 0)
    total = int(job.get("total", 0) or 0)
    queue_position = int(job.get("queue_position", 0) or 0)
    error = str(job.get("error") or "")
    title = truncate_title(resolve_preferred_title(job, fallback_doc_id=doc_id), max_len=70, suffix="[...]")
    percent = int((current / total * 100) if total > 0 else 0)

    badge_cls, badge_text = _download_job_badge(status, queue_position)
    left_actions, right_actions = _download_job_actions(status, job_id, doc_id, library)
    progress = _download_job_progress(status, current, total, percent, error)

    return Div(
        Div(
            H3(title, cls="text-sm font-bold text-slate-100 truncate"),
            Span(badge_text, cls=f"text-[10px] px-2 py-1 rounded {badge_cls}"),
            cls="flex items-start justify-between gap-2",
        ),
        P(library, cls="text-xs text-slate-400"),
        progress,
        Div(
            Div(*left_actions, cls="flex flex-wrap gap-2"),
            Div(*right_actions, cls="flex flex-wrap gap-2 ml-auto"),
            cls="mt-2 flex items-start gap-2",
        ),
        cls="bg-slate-900/50 border border-slate-700 rounded-lg p-3",
    )
