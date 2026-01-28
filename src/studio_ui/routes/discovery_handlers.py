"""Route handlers for the Discovery page.

Handlers are top-level functions so `setup_discovery_routes` can remain
very small and satisfy ruff's complexity check.
"""

from typing import Any
from urllib.parse import unquote

from fasthtml.common import Request

# Importiamo i nuovi componenti grafici
from studio_ui.components.discovery import (
    discovery_content,
    render_download_status,
    render_error_message,
    render_preview,
)
from studio_ui.components.layout import base_layout
from studio_ui.routes.discovery_helpers import analyze_manifest, start_downloader_thread
from universal_iiif_core.logger import get_logger
from universal_iiif_core.resolvers.discovery import resolve_shelfmark

logger = get_logger(__name__)

# Shared progress store used by the polling endpoint
download_progress: dict[str, Any] = {}


def discovery_page(request: Request):
    """Render the Discovery page."""
    content = discovery_content()
    is_hx = request.headers.get("HX-Request") == "true"
    if is_hx:
        return content
    return base_layout("Discovery", content, active_page="discovery")


def resolve_manifest(library: str, shelfmark: str):
    """Resolve a shelfmark or URL and return a preview fragment."""
    try:
        # Controllo Input Vuoto
        if not shelfmark or not shelfmark.strip():
            return render_error_message("Input mancante", "Inserisci una segnatura (es. Urb.lat.1779) o un URL valido.")

        logger.info("Resolving: lib=%s shelf=%s", library, shelfmark)

        # 1. Risoluzione URL
        try:
            manifest_url, doc_id = resolve_shelfmark(library, shelfmark)
        except Exception as e:
            logger.error(f"Resolver error: {e}")
            return render_error_message("Errore nel Resolver", str(e))

        if not manifest_url:
            # Suggerimenti specifici in base alla biblioteca
            hint = "Verifica che la segnatura sia corretta."
            if library == "Vaticana":
                hint += " Prova formati come 'Urb.lat.1779' o 'Vat.gr.123'."
            elif library == "Gallica":
                hint += " Inserisci un ID ARK o cerca per titolo."

            return render_error_message(
                "Manoscritto non trovato", f"Impossibile risolvere '{shelfmark}' per la biblioteca {library}. {hint}"
            )

        # 2. Analisi del Manifest (Download leggero)
        try:
            manifest_info = analyze_manifest(manifest_url)
        except Exception as e:
            logger.error(f"Manifest analysis error: {e}")
            return render_error_message(
                "Errore lettura Manifest",
                "Il documento esiste ma il file Manifest IIIF sembra corrotto o irraggiungibile.",
            )

        # 3. Preparazione Dati Anteprima
        preview_data = {
            "id": doc_id or manifest_info.get("label", "Unknown"),
            "library": library,
            "url": manifest_url,
            "label": manifest_info.get("label", "Senza Titolo"),
            "description": manifest_info.get("description", "Nessuna descrizione disponibile."),
            "pages": manifest_info.get("canvases", 0),
        }

        return render_preview(preview_data)

    except Exception as e:
        logger.exception("Unexpected error in resolve_manifest")
        return render_error_message("Errore di Sistema Imprevisto", str(e))


def start_download(manifest_url: str, doc_id: str, library: str):
    """Start an asynchronous download job and return a polling fragment."""
    try:
        manifest_url = unquote(manifest_url)
        doc_id = unquote(doc_id)
        library = unquote(library)

        download_id = start_downloader_thread(manifest_url, doc_id, library, download_progress)

        # Ritorna subito il primo stato (0%) per avviare il polling
        initial_status = {"status": "starting", "current": 0, "total": 0, "percent": 0}
        return render_download_status(download_id, doc_id, library, initial_status)

    except Exception as e:
        logger.exception("Download start failed")
        return render_error_message("Impossibile avviare il download", str(e))


def get_download_status(download_id: str, doc_id: str = "", library: str = ""):
    """Return current download status for polling (HTMX endpoint)."""
    status_data = download_progress.get(download_id, {"status": "starting"})

    curr = status_data.get("current", 0)
    total = status_data.get("total", 0)

    # Calcolo percentuale sicuro
    percent = int((curr / total * 100) if total > 0 else 0)

    # Aggiorniamo i dati per il render
    status_data["percent"] = percent

    return render_download_status(download_id, doc_id, library, status_data)
