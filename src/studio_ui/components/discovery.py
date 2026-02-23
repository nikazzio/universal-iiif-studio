"""Rendering helpers for the Discovery routes.

Gestisce la grafica della pagina di ricerca, le card di anteprima,
i messaggi di errore e la barra di avanzamento del download.
"""

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

        # Azione: Avvia Download
        hx_vals = f'{{"manifest_url": "{manifest_url}", "doc_id": "{doc_id}", "library": "{library}"}}'

        btn = Button(
            "⬇️ Scarica",
            cls="bg-slate-700 hover:bg-slate-600 text-white text-xs px-3 py-1 rounded transition-colors",
            hx_post="/api/start_download",
            hx_vals=hx_vals,
            hx_target="#download-status-area",
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

        txt_col = Div(
            H3(
                title[:80] + ("..." if len(title) > 80 else ""),
                cls="text-sm font-bold text-slate-200 mb-1 leading-tight",
            ),
            meta_row if meta_row else "",
            P(desc, cls="text-xs text-slate-400 mb-2 line-clamp-2") if desc else "",
            Div(id_badge, viewer_link if viewer_link else "", btn, cls="flex items-center gap-2 justify-between"),
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
            Span("Clicca su scarica per importare", cls="text-xs text-slate-500"),
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
        active_download_fragment if active_download_fragment is not None else Div(id="download-status-area", cls="mb-6")
    )

    return Div(
        H2("🛰️ Discovery & Download", cls="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-6"),
        discovery_form(),
        # Downloads area separate from search preview
        Div(
            H3("Download in corso", cls="text-lg font-semibold text-slate-700 dark:text-slate-200 mb-2"),
            downloads_block,
            cls="mb-8",
        ),
        preview_block,
        cls="p-6 max-w-5xl mx-auto",
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

    # Download form
    download_form = Form(
        Input(type="hidden", name="manifest_url", value=manifest_url),
        Input(type="hidden", name="doc_id", value=doc_id),
        Input(type="hidden", name="library", value=library),
        Button(
            Span("🚀 Avvia Download", cls="font-bold"),
            type="submit",
            cls=(
                "w-full py-4 bg-green-600 hover:bg-green-700 text-white rounded-lg "
                "transition-all shadow-lg hover:shadow-xl active:scale-95 flex items-center "
                "justify-center gap-2 text-lg"
            ),
        ),
        hx_post="/api/start_download",
        hx_target="#download-status-area",
        hx_swap="innerHTML",
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
