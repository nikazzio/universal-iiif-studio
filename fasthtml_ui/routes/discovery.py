"""Discovery Page - Search and download manuscripts.

Supports searching by shelfmark/URL and previewing manifest before download.
"""

import threading
from urllib.parse import unquote

from fasthtml.common import H2, H3, Button, Div, Form, Input, Label, Option, P, Select, Span, Table, Tbody, Td, Th, Tr

from fasthtml_ui.components.layout import base_layout
from iiif_downloader.config_manager import get_config_manager
from iiif_downloader.logger import get_logger
from iiif_downloader.logic import IIIFDownloader
from iiif_downloader.resolvers.discovery import resolve_shelfmark
from iiif_downloader.utils import get_json

logger = get_logger(__name__)

# Global dictionary to track download progress (simplified for now)
download_progress = {}

def setup_discovery_routes(app):
    """Register Discovery page routes.

    Args:
        app: FastHTML app instance
    """

    @app.get("/discovery")
    def discovery_page():
        """Render Discovery page."""
        content = Div(
            H2("🛰️ Discovery & Download", cls="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-6"),

            # Discovery form
            _discovery_form(),

            # Preview area (placeholder for HTMX)
            Div(id="discovery-preview", cls="mt-8"),

            cls="p-6 max-w-5xl mx-auto"
        )

        return base_layout(
            "Discovery & Download",
            content,
            active_page="discovery"
        )

    @app.post("/api/resolve_manifest")
    def resolve_manifest(library: str, shelfmark: str):
        """Resolve shelfmark/URL and return preview.
        
        HTMX endpoint.
        """
        try:
            logger.info(f"🔍 Resolving: {library} / {shelfmark}")
            manifest_url, doc_id_hint = resolve_shelfmark(library, shelfmark)

            if not manifest_url:
                return Div(
                    Span("⚠️", cls="text-xl mr-2"),
                    Span(doc_id_hint or "ID non risolvibile", cls="font-medium"),
                    cls="bg-yellow-100 dark:bg-yellow-900 border border-yellow-400 dark:border-yellow-600 text-yellow-700 dark:text-yellow-200 px-4 py-3 rounded mt-4"
                )

            # Analyze manifest
            m = get_json(manifest_url)
            label = m.get("label", "Senza Titolo")
            if isinstance(label, list): label = label[0]
            if isinstance(label, dict): label = label.get("it", label.get("en", list(label.values())[0]))

            desc = m.get("description", "")
            if isinstance(desc, list): desc = desc[0]

            # Count pages
            canvases = []
            if "sequences" in m: canvases = m["sequences"][0].get("canvases", [])
            elif "items" in m: canvases = m["items"]

            preview_data = {
                "url": manifest_url,
                "id": doc_id_hint,
                "label": str(label),
                "library": library,
                "description": str(desc)[:500],
                "pages": len(canvases)
            }

            return _render_preview(preview_data)

        except Exception as e:
            logger.exception(f"❌ Resolution error: {e}")
            return Div(
                Span("❌", cls="text-xl mr-2"),
                Span(f"Errore: {str(e)}", cls="font-medium"),
                cls="bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-600 text-red-700 dark:text-red-200 px-4 py-3 rounded mt-4"
            )

    @app.post("/api/start_download")
    def start_download(manifest_url: str, doc_id: str, library: str):
        """Start async download process.
        
        HTMX endpoint.
        """
        try:
            manifest_url = unquote(manifest_url)
            doc_id = unquote(doc_id)
            library = unquote(library)

            logger.info(f"🚀 Starting download: {doc_id} from {library}")

            # Track progress (simple shared state)
            download_id = f"{library}_{doc_id}"
            download_progress[download_id] = {"current": 0, "total": 0, "status": "initializing"}

            def progress_hook(curr, total):
                download_progress[download_id] = {"current": curr, "total": total, "status": "downloading"}

            def run_downloader():
                try:
                    downloader = IIIFDownloader(
                        manifest_url=manifest_url,
                        output_name=doc_id,
                        library=library,
                        progress_callback=progress_hook,
                        workers=int(get_config_manager().get_setting("system.download_workers", 4))
                    )
                    downloader.run()
                    download_progress[download_id]["status"] = "complete"
                except Exception as e:
                    logger.error(f"Download thread error: {e}")
                    download_progress[download_id]["status"] = f"error: {str(e)}"

            # Start in thread
            thread = threading.Thread(target=run_downloader, daemon=True)
            thread.start()

            # Return progress UI with polling
            return _render_download_status(download_id, doc_id)

        except Exception as e:
            logger.exception(f"❌ Start download error: {e}")
            return Div(f"Errore: {str(e)}", cls="text-red-600")

    @app.get("/api/download_status/{download_id}")
    def get_download_status(download_id: str):
        """Get current download status.
        
        HTMX polling endpoint.
        """
        status_data = download_progress.get(download_id, {"status": "unknown"})

        if status_data["status"] == "complete":
            return Div(
                Div(
                    Span("🎉", cls="text-2xl mr-2"),
                    Span("Download Completato!", cls="font-bold"),
                    cls="flex items-center text-green-600 dark:text-green-400 mb-2"
                ),
                P(f"Il documento '{download_id.split('_')[-1]}' è pronto nello Studio."),
                Button(
                    "Vai allo Studio →",
                    onclick=f"window.location.href='/studio?library={download_id.split('_')[0]}&doc_id={download_id.split('_')[-1]}'",
                    cls="bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 px-4 rounded mt-4 transition"
                ),
                cls="bg-green-100 dark:bg-green-900/30 p-4 rounded border border-green-400"
            )

        if "error" in status_data["status"]:
            return Div(
                Span("❌", cls="text-2xl mr-2"),
                Span(f"Errore Download: {status_data['status'].replace('error: ', '')}", cls="font-bold text-red-600"),
                cls="bg-red-100 dark:bg-red-900/30 p-4 rounded border border-red-400"
            )

        # Still downloading
        curr = status_data.get("current", 0)
        total = status_data.get("total", 0)
        percent = int((curr / total * 100) if total > 0 else 0)

        return Div(
            Div(
                Span("⏳", cls="animate-spin-slow text-xl mr-2"),
                Span(f"Scaricamento in corso: {curr}/{total}", cls="font-medium text-indigo-600 dark:text-indigo-400"),
                cls="flex items-center mb-2"
            ),
            # Progress bar
            Div(
                Div(style=f"width: {percent}%", cls="h-full bg-indigo-600 transition-all duration-300"),
                cls="w-full h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden"
            ),
            # Polling attributes
            hx_get=f"/api/download_status/{download_id}",
            hx_trigger="every 1.5s",
            hx_swap="outerHTML"
        )


def _discovery_form() -> Div:
    """Generate the discovery search form."""
    libraries = [
        ("Vaticana (BAV)", "Vaticana"),
        ("Gallica (BnF)", "Gallica"),
        ("Bodleian (Oxford)", "Bodleian"),
        ("Altro / URL Diretto", "Unknown")
    ]

    return Div(
        H3("🔎 Ricerca per Segnatura", cls="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4"),

        Form(
            Div(
                # Library selector
                Div(
                    Label("Biblioteca", for_="lib-select", cls="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"),
                    Select(
                        *[Option(label, value=value) for label, value in libraries],
                        id="lib-select", name="library",
                        cls="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 dark:text-white"
                    ),
                    cls="w-1/3"
                ),

                # Input
                Div(
                    Label("Segnatura, ID o URL", for_="shelf-input", cls="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"),
                    Input(
                        type="text", id="shelf-input", name="shelfmark",
                        placeholder="es. Urb.lat.1779 o btv1b10033406t",
                        cls="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 dark:text-white shadow-sm"
                    ),
                    cls="w-2/3"
                ),

                cls="flex gap-4 mb-4"
            ),

            Button(
                "🔍 Analizza Documento",
                type="submit",
                cls="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-4 rounded transition-all shadow-md active:scale-95"
            ),

            hx_post="/api/resolve_manifest",
            hx_target="#discovery-preview",
            hx_indicator="#resolve-spinner"
        ),

        # Spinner
        Div(
            Div(cls="inline-block w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"),
            id="resolve-spinner",
            cls="htmx-indicator flex justify-center mt-6"
        ),

        cls="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm"
    )

def _render_preview(data: dict) -> Div:
    """Render the manifest preview."""
    return Div(
        H3(f"📖 {data['label']}", cls="text-xl font-bold text-gray-800 dark:text-gray-100 mb-2"),

        P(data.get("description", ""), cls="text-gray-600 dark:text-gray-400 mb-4 italic line-clamp-3"),

        Div(
            # Metadata table
            Table(
                Tbody(
                    Tr(Th("ID", cls="text-left py-1 pr-4 font-medium text-gray-500"), Td(data["id"], cls="dark:text-gray-300")),
                    Tr(Th("Library", cls="text-left py-1 pr-4 font-medium text-gray-500"), Td(data["library"], cls="dark:text-gray-300")),
                    Tr(Th("Pagine", cls="text-left py-1 pr-4 font-medium text-gray-500"), Td(str(data["pages"]), cls="dark:text-gray-300")),
                    Tr(Th("Manifest", cls="text-left py-1 pr-4 font-medium text-gray-500"), Td(data["url"], cls="text-xs truncate max-w-sm text-blue-500")),
                ),
                cls="w-full mb-6"
            ),

            # Action button
            Form(
                Input(type="hidden", name="manifest_url", value=data["url"]),
                Input(type="hidden", name="doc_id", value=data["id"]),
                Input(type="hidden", name="library", value=data["library"]),

                Button(
                    Span("🚀 Avvia Download", cls="font-bold"),
                    type="submit",
                    cls="w-full py-4 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-all shadow-lg hover:shadow-xl active:scale-95 flex items-center justify-center gap-2"
                ),

                hx_post="/api/start_download",
                hx_target="#discovery-preview",
                hx_swap="innerHTML"
            ),

            cls="bg-gray-50 dark:bg-gray-900 p-6 rounded-lg border-2 border-dashed border-indigo-200 dark:border-indigo-900"
        ),

        cls="animate-in fade-in slide-in-from-top-4 duration-300"
    )

def _render_download_status(download_id, doc_id) -> Div:
    """Initial download status rendering."""
    return Div(
        Div(
            Span("🚀", cls="text-2xl mr-2"),
            Span(f"Download di '{doc_id}' avviato...", cls="font-bold"),
            cls="flex items-center text-indigo-600 dark:text-indigo-400 mb-2"
        ),
        # Polling placeholder
        Div(
            "Inizializzazione worker...",
            hx_get=f"/api/download_status/{download_id}",
            hx_trigger="every 1s",
            hx_swap="outerHTML"
        ),
        cls="bg-indigo-50 dark:bg-indigo-950 p-6 rounded-lg border border-indigo-200 dark:border-indigo-800"
    )
