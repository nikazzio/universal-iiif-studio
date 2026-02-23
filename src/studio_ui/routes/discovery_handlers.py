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
    render_search_results_list,
)
from studio_ui.components.layout import base_layout
from studio_ui.routes.discovery_helpers import analyze_manifest, start_downloader_thread
from universal_iiif_core.logger import get_logger
from universal_iiif_core.resolvers.discovery import resolve_shelfmark, smart_search
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
            return render_error_message("Input mancante", "Inserisci una segnatura o una parola chiave.")

        logger.info("Resolving: lib=%s input=%s", library, shelfmark)

        # === RAMO A: GALLICA (Ricerca Smart o ID) ===
        if "Gallica" in library:
            try:
                # smart_search restituisce SEMPRE una lista (di 1 o N elementi)
                results = smart_search(shelfmark)
            except ValueError as e:
                # Known input validation errors: safe to expose
                return render_error_message("Errore Gallica", str(e))
            except Exception:
                # Unknown errors: log but don't expose details
                logger.exception("Gallica search failed for shelfmark: %s", shelfmark)
                return render_error_message(
                    "Errore Gallica",
                    "Ricerca temporaneamente non disponibile. Riprova più tardi."
                )

            if not results:
                return render_error_message(
                    "Nessun risultato", f"Nessun manoscritto trovato per '{shelfmark}' su Gallica."
                )

            # CASO 1: ID DIRETTO (Lista con 1 elemento flaggato come match esatto)
            # Se è un URL specifico o un ID, smart_search restituisce 1 risultato con i dettagli completi
            is_direct = results[0].get("raw", {}).get("_is_direct_match", False)

            if len(results) == 1 and is_direct:
                # È un manoscritto singolo: usiamo la vista standard di anteprima
                item = results[0]
                preview_data = {
                    "id": item.get("id"),
                    "library": "Gallica",
                    "url": item.get("manifest"),
                    "label": item.get("title", "Senza Titolo"),
                    "description": item.get("description", ""),
                    "pages": 0,  # Gallica SRU a volte non dà il conteggio pagine, ma va bene
                    "thumbnail": item.get("thumbnail"),
                }
                return render_preview(preview_data)

            # CASO 2: RISULTATI DI RICERCA (Lista di N elementi)
            # Se smart_search restituisce più risultati o non è un match diretto
            return render_search_results_list(results)

        # === RAMO B: VATICANA / OXFORD (Logica Classica + Ricerca) ===

        # 1. Risoluzione URL diretta
        try:
            manifest_url, doc_id = resolve_shelfmark(library, shelfmark)
        except Exception as e:
            logger.debug(f"Direct resolution failed: {e}")
            manifest_url, doc_id = None, None

        # 2. Se risoluzione diretta fallisce per Vaticana, prova ricerca per varianti
        if not manifest_url and library == "Vaticana":
            from universal_iiif_core.resolvers.discovery import search_vatican

            logger.info("Trying Vatican search for: %s", shelfmark)
            try:
                results = search_vatican(shelfmark, max_results=5)
                if results:
                    # Se c'è un solo risultato, mostra preview diretto
                    if len(results) == 1:
                        item = results[0]
                        preview_data = {
                            "id": item.get("id"),
                            "library": "Vaticana",
                            "url": item.get("manifest"),
                            "label": item.get("title", "Senza Titolo"),
                            "description": item.get("description", ""),
                            "pages": item.get("raw", {}).get("page_count", 0),
                            "thumbnail": item.get("thumbnail"),
                        }
                        return render_preview(preview_data)
                    # Altrimenti mostra lista risultati
                    return render_search_results_list(results)
            except Exception as e:
                logger.warning("Vatican search failed: %s", e)

        if not manifest_url:
            hint = "Verifica la segnatura."
            if library == "Vaticana":
                hint += " Prova formati come 'Urb.lat.1779' o inserisci solo il numero (es. '1223')."

            return render_error_message(
                "Manoscritto non trovato", f"Impossibile risolvere '{shelfmark}' per {library}. {hint}"
            )

        # 3. Analisi del Manifest (Download leggero)
        try:
            manifest_info = analyze_manifest(manifest_url)
        except ValueError as e:
            # Known validation errors (empty manifest, parse errors): safe to expose
            return render_error_message("Errore Manifest", str(e))
        except Exception:
            logger.exception("Manifest analysis failed for URL: %s", manifest_url)
            return render_error_message(
                "Errore Manifest",
                "Manifest IIIF non accessibile. Verifica l'URL o riprova più tardi."
            )

        # 4. Preparazione Dati Anteprima
        preview_data = {
            "id": doc_id or manifest_info.get("label", "Unknown"),
            "library": library,
            "url": manifest_url,
            "label": manifest_info.get("label", "Senza Titolo"),
            "description": manifest_info.get("description", "Nessuna descrizione."),
            "pages": manifest_info.get("canvases", 0),
        }

        return render_preview(preview_data)

    except ValueError as e:
        # Known input validation errors: safe to expose
        logger.warning("Validation error in resolve_manifest: %s", e)
        return render_error_message("Errore Input", str(e))
    except Exception:
        logger.exception("Unexpected error in resolve_manifest")
        return render_error_message(
            "Errore Interno",
            "Si è verificato un errore imprevisto. Riprova più tardi."
        )


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

    except ValueError as e:
        # Known validation errors: safe to expose
        logger.warning("Download validation error: %s", e)
        return render_error_message("Errore Input", str(e))
    except Exception:
        logger.exception("Download start failed")
        return render_error_message(
            "Errore Download",
            "Impossibile avviare il download. Riprova più tardi."
        )


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
