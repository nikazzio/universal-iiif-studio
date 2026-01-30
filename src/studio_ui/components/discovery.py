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
    Input,
    Label,
    Option,
    P,
    Select,
    Span,
    Table,
    Tbody,
    Td,
    Th,
    Tr,
)


def render_error_message(title: str, details: str = "") -> Div:
    """Renderizza un messaggio di errore user-friendly (Rosso)."""
    return Div(
        Div(
            Span("⚠️", cls="text-2xl mr-3"),
            Div(
                P(title, cls="font-bold text-red-800 dark:text-red-200"),
                P(details, cls="text-sm text-red-600 dark:text-red-300 mt-1") if details else "",
            ),
            cls="flex items-start",
        ),
        cls=(
            "bg-red-50 dark:bg-red-900/30 border-l-4 border-red-500 p-4 rounded "
            "shadow-sm mt-6 animate-in fade-in slide-in-from-top-2"
        ),
    )


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
    """Render preview block for a manifest."""
    # Warning se ci sono troppe pagine
    pages = int(data.get("pages", 0))
    warning = ""
    if pages > 500:
        warning = Div(
            f"⚠️ Questo manoscritto contiene molte pagine ({pages}). Il download richiederà tempo.",
            cls=(
                "text-xs text-amber-800 dark:text-amber-200 mb-4 bg-amber-50 "
                "dark:bg-amber-900/30 p-3 rounded border border-amber-200"
            ),
        )

    return Div(
        H3(
            f"📖 {data['label']}",
            cls="text-xl font-bold text-gray-800 dark:text-gray-100 mb-2",
        ),
        P(
            data.get("description", ""),
            cls="text-gray-600 dark:text-gray-400 mb-4 italic line-clamp-3",
        ),
        Div(
            Table(
                Tbody(
                    Tr(
                        Th("ID", cls="text-left py-1 pr-4 font-medium text-gray-500"),
                        Td(data["id"], cls="dark:text-gray-300"),
                    ),
                    Tr(
                        Th("Library", cls="text-left py-1 pr-4 font-medium text-gray-500"),
                        Td(data["library"], cls="dark:text-gray-300"),
                    ),
                    Tr(
                        Th("Pagine", cls="text-left py-1 pr-4 font-medium text-gray-500"),
                        Td(str(data["pages"]), cls="dark:text-gray-300"),
                    ),
                    Tr(
                        Th("Manifest", cls="text-left py-1 pr-4 font-medium text-gray-500"),
                        Td(
                            data["url"],
                            cls="text-xs truncate max-w-sm text-blue-500",
                        ),
                    ),
                ),
                cls="w-full mb-6",
            ),
            warning,
            Form(
                Input(type="hidden", name="manifest_url", value=data["url"]),
                Input(type="hidden", name="doc_id", value=data["id"]),
                Input(type="hidden", name="library", value=data["library"]),
                Button(
                    Span("🚀 Avvia Download", cls="font-bold"),
                    type="submit",
                    cls=(
                        "w-full py-4 bg-green-600 hover:bg-green-700 text-white rounded-lg "
                        "transition-all shadow-lg hover:shadow-xl active:scale-95 flex items-center "
                        "justify-center gap-2"
                    ),
                ),
                hx_post="/api/start_download",
                hx_target="#discovery-preview",
                hx_swap="innerHTML",
            ),
            cls=(
                "bg-gray-50 dark:bg-gray-900 p-6 rounded-lg border-2 border-dashed "
                "border-indigo-200 dark:border-indigo-900"
            ),
        ),
        cls="animate-in fade-in slide-in-from-top-4 duration-300",
    )


def render_download_status(download_id: str, doc_id: str, library: str, status_data: dict) -> Div:
    """Render the download status (Progress Bar or Success Card)."""
    percent = status_data.get("percent", 0)
    status = status_data.get("status", "running")
    current = status_data.get("current", 0)
    total = status_data.get("total", 0)
    error = status_data.get("error")
    title = status_data.get("title") or doc_id

    # 1.b Cancelling state: show immediate feedback but keep polling
    if status == "cancelling":
        header = Div(
            Div(
                H3(title, cls="text-lg font-bold text-gray-800 dark:text-gray-100"),
                Span(
                    library,
                    cls=(
                        "text-xs bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 "
                        " dark:text-indigo-300 px-2 py-1 rounded ml-2"
                    ),
                ),
                cls="flex items-center justify-between",
            ),
            P(f"{current}/{total} pagine", cls="text-sm text-gray-500 mt-1"),
            cls="mb-4",
        )

        percent_block = Div(
            Div(f"{percent}%", cls="text-3xl font-extrabold text-indigo-700 dark:text-indigo-300"),
            P("Cancelling…", cls="text-sm text-red-600"),
            cls="flex items-center gap-4 mb-4",
        )

        progress_bar = Div(
            Div(
                Div(
                    cls="bg-indigo-600 h-2.5 rounded-full transition-all duration-500 ease-out",
                    style=f"width: {percent}%",
                ),
                cls="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 mb-2",
            )
        )

        body = Div(
            header, percent_block, progress_bar, P("Annullamento in corso...", cls="text-xs text-gray-400 italic")
        )

        return Div(
            body,
            hx_get=f"/api/download_status/{download_id}?doc_id={doc_id}&library={library}",
            hx_trigger="every 1s",
            hx_swap="outerHTML",
            cls=(
                "bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 "
                "dark:border-gray-700 shadow-sm space-y-3"
            ),
        )

    # 1. Caso Errore
    if "error" in status or error:
        return render_error_message("Errore durante il download", str(error or status))

    # 2. Caso Completato (Mostra bottone per lo Studio)
    if percent >= 100 or status == "completed":
        from urllib.parse import quote

        encoded_lib = quote(library)
        encoded_doc = quote(doc_id)

        return Div(
            Div(
                Span("✅", cls="text-4xl mb-4 block"),
                H3("Download Completato!", cls="text-xl font-bold text-green-700 dark:text-green-300 mb-2"),
                P(
                    f"Il manoscritto '{doc_id}' è stato salvato correttamente.",
                    cls="text-gray-600 dark:text-gray-400 mb-6",
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
            cls=(
                "bg-green-50 dark:bg-green-900/20 border border-green-200 "
                "dark:border-green-800 p-8 rounded-lg shadow-sm animate-in zoom-in "
                "duration-300"
            ),
        )

    # 3. Caso In Corso (Barra di progresso + Polling)
    # Importante: passiamo doc_id e library nel polling per non perderli
    controls = Div(
        Button(
            "⛔ Annulla Download",
            cls=("bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-3 rounded-lg shadow-sm transition-all"),
            hx_post=f"/api/cancel_download/{download_id}?doc_id={doc_id}&library={library}",
            hx_target="#discovery-preview",
            hx_swap="outerHTML",
        ),
        cls="mt-4 flex justify-end",
    )
    # Enhanced header with title and library badge
    header = Div(
        Div(
            H3(title, cls="text-lg font-bold text-gray-800 dark:text-gray-100"),
            Span(
                library,
                cls=(
                    "text-xs bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 "
                    " dark:text-indigo-300 px-2 py-1 rounded ml-2"
                ),
            ),
            cls="flex items-center justify-between",
        ),
        P(f"{current}/{total} pagine", cls="text-sm text-gray-500 mt-1"),
        cls="mb-4",
    )

    # Large percent display
    percent_block = Div(
        Div(f"{percent}%", cls="text-3xl font-extrabold text-indigo-700 dark:text-indigo-300"),
        P("Processing…", cls="text-sm text-gray-500"),
        cls="flex items-center gap-4 mb-4",
    )

    progress_bar = Div(
        Div(
            Div(
                cls="bg-indigo-600 h-2.5 rounded-full transition-all duration-500 ease-out", style=f"width: {percent}%"
            ),
            cls="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 mb-2",
        )
    )

    body = Div(
        header,
        percent_block,
        progress_bar,
        P("Ottimizzazione immagini e salvataggio nel database...", cls="text-xs text-gray-400 italic animate-pulse"),
    )

    # Polling continuo ogni 1 secondo (omit when completed/error by returning different fragment)
    return Div(
        body,
        controls,
        hx_get=f"/api/download_status/{download_id}?doc_id={doc_id}&library={library}",
        hx_trigger="every 1s",
        hx_swap="outerHTML",
        cls=(
            "bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm space-y-3"
        ),
    )
