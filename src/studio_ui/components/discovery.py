"""Rendering helpers for the Discovery routes.

Gestisce la grafica della pagina di ricerca, le card di anteprima,
i messaggi di errore e la barra di avanzamento del download.
"""

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
    Select,
    Span,
)

from studio_ui.common.title_utils import resolve_preferred_title, truncate_title


def render_search_results_list(results: list) -> Div:
    """Renderizza una lista di risultati di ricerca con metadati estesi."""
    cards = []

    for item in results:
        # Estraiamo i dati
        title = item.get("title", "Senza titolo")
        author = item.get("author", "")
        date = item.get("date", "")
        language = item.get("language", "")
        publisher = item.get("publisher", "")
        ark = item.get("ark", "")
        library = item.get("library", "Gallica")

        # Tronchiamo la descrizione se troppo lunga
        desc_text = item.get("description", "") or ""
        desc = desc_text[:120] + "..." if len(desc_text) > 120 else desc_text

        thumb = item.get("thumbnail")
        doc_id = item.get("id")
        manifest_url = item.get("manifest")

        # Link al viewer originale
        viewer_url = None
        if library == "Gallica" and ark:
            viewer_url = f"https://gallica.bnf.fr/{ark}"
        elif library == "Gallica" and doc_id:
            viewer_url = f"https://gallica.bnf.fr/ark:/12148/{doc_id}"
        elif library == "Vaticana" and doc_id:
            viewer_url = f"https://digi.vatlib.it/view/{doc_id}"
        elif library == "Institut de France" and doc_id:
            viewer_url = f"https://bibnum.institutdefrance.fr/viewer/{doc_id}"

        # Azioni: salva in Libreria / salva+download
        hx_vals = f'{{"manifest_url": "{manifest_url}", "doc_id": "{doc_id}", "library": "{library}"}}'

        add_btn = Button(
            "➕ Aggiungi",
            cls="bg-slate-700 hover:bg-slate-600 text-white text-xs px-3 py-1 rounded transition-colors",
            hx_post="/api/discovery/add_to_library",
            hx_vals=hx_vals,
            hx_target="#download-manager-area",
            hx_swap="innerHTML",
        )
        add_dl_btn = Button(
            "⬇️ Aggiungi + Download",
            cls="bg-green-700 hover:bg-green-600 text-white text-xs px-3 py-1 rounded transition-colors",
            hx_post="/api/discovery/add_and_download",
            hx_vals=hx_vals,
            hx_target="#download-manager-area",
            hx_swap="innerHTML",
        )

        # Link esterno al viewer
        viewer_link = (
            A(
                "🔗 Viewer",
                href=viewer_url,
                target="_blank",
                cls="text-xs text-blue-400 hover:text-blue-300 underline ml-2",
            )
            if viewer_url
            else None
        )

        # Layout Card Orizzontale con più info
        img_col = Div(
            Img(src=thumb, cls="w-20 h-20 object-cover rounded border border-slate-600")
            if thumb
            else Div(
                "No IMG",
                cls="w-20 h-20 bg-slate-800 rounded flex items-center justify-center text-[10px] text-slate-500",
            ),
            cls="flex-shrink-0 mr-4",
        )

        # Metadati aggiuntivi in formato compatto
        meta_items = []
        if author and author != "Autore sconosciuto":
            meta_items.append(Span(f"👤 {author[:40]}", cls="text-xs text-slate-400"))
        if date:
            meta_items.append(Span(f"📅 {date}", cls="text-xs text-slate-500"))
        if language:
            meta_items.append(Span(f"🌐 {language.upper()}", cls="text-xs text-slate-500"))
        if publisher:
            meta_items.append(Span(f"📚 {publisher[:30]}", cls="text-xs text-slate-500"))

        meta_row = Div(*meta_items, cls="flex flex-wrap gap-x-3 gap-y-1 mb-1") if meta_items else None

        # ID badge
        id_badge = Span(
            doc_id[:20] + "..." if len(doc_id or "") > 20 else doc_id,
            cls="text-[10px] bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded font-mono",
        )
        badge_id = f"pdf-badge-{(doc_id or 'item').replace(' ', '-').replace('/', '-')[:28]}"
        pdf_badge = Div(
            "PDF: verifica...",
            id=badge_id,
            hx_get=f"/api/discovery/pdf_capability?manifest_url={quote(str(manifest_url or ''), safe='')}",
            hx_trigger="load",
            hx_swap="outerHTML",
            cls="text-[10px] bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded",
        )

        txt_col = Div(
            H3(
                title[:80] + ("..." if len(title) > 80 else ""),
                cls="text-sm font-bold text-slate-200 mb-1 leading-tight",
            ),
            meta_row if meta_row else "",
            P(desc, cls="text-xs text-slate-400 mb-2 line-clamp-2") if desc else "",
            Div(
                Div(id_badge, pdf_badge, cls="flex items-center gap-2"),
                Div(viewer_link if viewer_link else "", add_btn, add_dl_btn, cls="flex items-center gap-2"),
                cls="flex items-center gap-2 justify-between",
            ),
            cls="flex-grow min-w-0",
        )

        card = Div(
            img_col,
            txt_col,
            cls=(
                "flex items-start p-3 bg-slate-800/40 hover:bg-slate-800/80 rounded-lg border border-slate-700/50 "
                "hover:border-slate-600 transition-all mb-2"
            ),
        )
        cards.append(card)

    return Div(
        Div(
            H3(f"Trovati {len(results)} risultati", cls="text-md font-bold text-slate-100"),
            Span("Aggiungi in libreria o avvia download dalla card", cls="text-xs text-slate-500"),
            cls="flex justify-between items-baseline mb-4 border-b border-slate-700 pb-2",
        ),
        Div(*cards, cls="space-y-2 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar"),
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
    libraries = [
        ("Vaticana (BAV)", "Vaticana"),
        ("Gallica (BnF)", "Gallica"),
        ("Institut de France (Bibnum)", "Institut de France"),
        ("Bodleian (Oxford)", "Bodleian"),
        ("Altro / URL Diretto", "Unknown"),
    ]

    return Div(
        H3("🔎 Ricerca per Segnatura", cls="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4"),
        Form(
            Div(
                # Library selector
                Div(
                    Label(
                        "Biblioteca",
                        for_="lib-select",
                        cls="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1",
                    ),
                    Select(
                        *[Option(label, value=value) for label, value in libraries],
                        id="lib-select",
                        name="library",
                        cls=(
                            "w-full px-3 py-2 border border-gray-300 "
                            "dark:border-gray-600 rounded bg-white dark:bg-gray-800 "
                            "dark:text-white"
                        ),
                    ),
                    cls="w-1/3",
                ),
                # Input
                Div(
                    Label(
                        "Segnatura, ID o URL",
                        for_="shelf-input",
                        cls="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1",
                    ),
                    Input(
                        type="text",
                        id="shelf-input",
                        name="shelfmark",
                        placeholder="es. Urb.lat.1779 o btv1b10033406t",
                        cls=(
                            "w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white "
                            "dark:bg-gray-800 dark:text-white shadow-sm"
                        ),
                    ),
                    cls="w-2/3",
                ),
                cls="flex gap-4 mb-4",
            ),
            Button(
                "🔍 Analizza Documento",
                type="submit",
                cls=(
                    "w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-4 rounded "
                    "transition-all shadow-md active:scale-95"
                ),
            ),
            hx_post="/api/resolve_manifest",
            hx_target="#discovery-preview",
            hx_indicator="#resolve-spinner",
        ),
        # Spinner
        Div(
            Div(cls="inline-block w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"),
            id="resolve-spinner",
            cls="htmx-indicator flex justify-center mt-6",
        ),
        cls="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm",
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
        H2("🛰️ Discovery", cls="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-6"),
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
                "PDF: verifica...",
                id="preview-pdf-badge",
                hx_get=f"/api/discovery/pdf_capability?manifest_url={quote(str(manifest_url or ''), safe='')}",
                hx_trigger="load",
                hx_swap="outerHTML",
                cls="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded",
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

    # 1.b Cancelling state
    if status == "cancelling":
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
            P("Annullamento...", cls="text-sm text-red-400"),
            cls="flex items-center gap-4 mb-4",
        )

        progress_bar = Div(Div(Div(cls=progress_bar_cls, style=f"width: {percent}%"), cls=progress_bg_cls))

        body = Div(
            header, percent_block, progress_bar, P("Annullamento in corso...", cls="text-xs text-slate-500 italic")
        )

        return Div(
            body,
            hx_get=f"/api/download_status/{download_id}?doc_id={doc_id}&library={library}",
            hx_trigger="every 1s",
            hx_swap="outerHTML",
            cls=card_cls,
        )

    # 1. Caso Errore
    if "error" in status or error:
        return render_error_message("Errore durante il download", str(error or status))

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
        return Div("PDF nativo disponibile", cls="text-[10px] bg-emerald-800 text-emerald-100 px-1.5 py-0.5 rounded")
    return Div("Solo immagini", cls="text-[10px] bg-amber-800 text-amber-100 px-1.5 py-0.5 rounded")


def render_download_manager(jobs: list[dict]) -> Div:
    """Render the full download manager panel."""
    active_statuses = {"queued", "running", "cancelling", "pending", "starting"}
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

    if status in {"running", "queued", "cancelling"}:
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
    progress = Div(
        Div(
            Div(cls="h-2 rounded bg-indigo-500", style=f"width: {percent}%"),
            cls="w-full bg-slate-700 rounded h-2",
        ),
        P(f"{current}/{total} ({percent}%)", cls="text-[11px] text-slate-400 mt-1") if total > 0 else "",
        cls="mt-2",
    )
    if status == "queued":
        return Div(P("In attesa di uno slot libero...", cls="text-[11px] text-slate-400 mt-2"), cls="mt-1")
    if status == "paused":
        return Div(P("Download in pausa.", cls="text-[11px] text-violet-300 mt-2"), cls="mt-1")
    if status in {"error", "cancelled"} and error:
        return Div(P(error, cls="text-[11px] text-rose-300 mt-2"), cls="mt-1")
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
