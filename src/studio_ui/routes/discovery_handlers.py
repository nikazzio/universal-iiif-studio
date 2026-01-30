"""Route handlers for the Discovery page.

Handlers are top-level functions so `setup_discovery_routes` can remain
very small and satisfy ruff's complexity check.
"""

from urllib.parse import unquote

from fasthtml.common import Div, Request

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
from universal_iiif_core.services.storage.vault_manager import VaultManager

logger = get_logger(__name__)

# No in-memory progress store: UI reads progress from DB


def discovery_page(request: Request):
    """Render the Discovery page."""
    vault = VaultManager()
    active_list = vault.get_active_downloads()

    is_hx = request.headers.get("HX-Request") == "true"

    # HTMX fragment request: return the discovery content only (with downloads area)
    if is_hx:
        active_frag = None
        if active_list:
            cards = []
            for active in active_list:
                job_id = str(active.get("job_id") or "")
                doc_id = str(active.get("doc_id") or "")
                library = str(active.get("library") or "")

                curr = int(active.get("current", 0))
                total = int(active.get("total", 0))
                percent = int((curr / total * 100) if total > 0 else 0)

                status_data = {
                    "status": str(active.get("status", "running")),
                    "current": curr,
                    "total": total,
                    "percent": percent,
                    "error": active.get("error"),
                }
                try:
                    ms = vault.get_manuscript(doc_id) or {}
                    status_data["title"] = ms.get("title") or doc_id
                except Exception:
                    status_data["title"] = doc_id

                cards.append(render_download_status(job_id, doc_id, library, status_data))

            active_frag = Div(*cards, id="download-status-area")

        return discovery_content(initial_preview=None, active_download_fragment=active_frag)

    # Full-page request: wrap in base layout and include downloads area (all active downloads)
    active_frag = None
    if active_list:
        cards = []
        for active in active_list:
            job_id = str(active.get("job_id") or "")
            doc_id = str(active.get("doc_id") or "")
            library = str(active.get("library") or "")

            curr = int(active.get("current", 0))
            total = int(active.get("total", 0))
            percent = int((curr / total * 100) if total > 0 else 0)

            status_data = {
                "status": str(active.get("status", "running")),
                "current": curr,
                "total": total,
                "percent": percent,
                "error": active.get("error"),
            }
            try:
                ms = vault.get_manuscript(doc_id) or {}
                status_data["title"] = ms.get("title") or doc_id
            except Exception:
                status_data["title"] = doc_id

            cards.append(render_download_status(job_id, doc_id, library, status_data))

        active_frag = Div(*cards, id="download-status-area")

    content = discovery_content(initial_preview=None, active_download_fragment=active_frag)
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

        download_id = start_downloader_thread(manifest_url, doc_id, library)

        # Return initial DB-backed status fragment to start polling
        initial_status = {"status": "starting", "current": 0, "total": 0, "percent": 0}
        return render_download_status(download_id, doc_id, library, initial_status)

    except Exception as e:
        logger.exception("Download start failed")
        return render_error_message("Impossibile avviare il download", str(e))


def get_download_status(download_id: str, doc_id: str = "", library: str = ""):
    """Return current download status for polling (HTMX endpoint)."""
    vault = VaultManager()
    job = vault.get_download_job(download_id) or {}

    curr = job.get("current", 0)
    total = job.get("total", 0)
    status = job.get("status", "starting")
    error = job.get("error")

    percent = int((curr / total * 100) if total > 0 else 0)

    status_data = {"status": status, "current": curr, "total": total, "percent": percent, "error": error}

    return render_download_status(download_id, doc_id, library, status_data)


def cancel_download(download_id: str, doc_id: str = "", library: str = ""):
    """Cancel a running download job (UI action).

    Marks the job as errored/cancelled in the DB and returns the
    updated status fragment for the preview area.
    """
    vault = VaultManager()
    job = vault.get_download_job(download_id) or {}
    curr = job.get("current", 0)
    total = job.get("total", 0)
    try:
        # Mark as cancelling first so UI shows immediate feedback
        vault.update_download_job(download_id, current=curr, total=total, status="cancelling", error="Cancelling")
    except Exception:
        logger.debug("Failed to mark job cancelled", exc_info=True)

    # Also inform in-process JobManager to request cooperative cancellation
    try:
        from universal_iiif_core.jobs import job_manager

        job_manager.request_cancel(download_id)
    except Exception:
        logger.debug("Failed to request job cancellation from JobManager", exc_info=True)

    status_data = {
        "status": "cancelling",
        "current": curr,
        "total": total,
        "percent": int((curr / total * 100) if total else 0),
        "error": "Cancelling",
    }
    return render_download_status(download_id, doc_id, library, status_data)
