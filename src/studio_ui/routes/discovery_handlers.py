"""Route handlers for the Discovery page.

Handlers are top-level functions so `setup_discovery_routes` can remain
very small and satisfy ruff's complexity check.
"""

from urllib.parse import unquote

from fasthtml.common import Div, Request

from studio_ui.common.toasts import build_toast

# Importiamo i nuovi componenti grafici
from studio_ui.components.discovery import (
    discovery_content,
    render_download_status,
    render_feedback_message,
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


def _toast_text(title: str, details: str = "") -> str:
    detail = (details or "").strip()
    return f"{title}: {detail}" if detail else title


def _with_feedback_toast(title: str, details: str = "", tone: str = "danger"):
    """Return Discovery inline feedback + global toast."""
    return [
        render_feedback_message(title, details, tone=tone),
        build_toast(_toast_text(title, details), tone=tone),
    ]


def _with_toast(fragment, message: str, tone: str = "info"):
    """Append a global toast to an existing fragment response."""
    return [fragment, build_toast(message, tone=tone)]


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


def _build_item_preview_data(item: dict, library: str, pages: int = 0) -> dict:
    """Build preview payload from a search result item."""
    return {
        "id": item.get("id"),
        "library": library,
        "url": item.get("manifest"),
        "label": item.get("title", "Senza Titolo"),
        "description": item.get("description", ""),
        "pages": pages,
        "thumbnail": item.get("thumbnail"),
    }


def _build_manifest_preview_data(manifest_info: dict, manifest_url: str, doc_id: str | None, library: str) -> dict:
    """Build preview payload from analyzed manifest metadata."""
    return {
        "id": doc_id or manifest_info.get("label", "Unknown"),
        "library": library,
        "url": manifest_url,
        "label": manifest_info.get("label", "Senza Titolo"),
        "description": manifest_info.get("description", "Nessuna descrizione."),
        "pages": manifest_info.get("canvases", 0),
    }


def _resolve_gallica_flow(shelfmark: str):
    try:
        results = smart_search(shelfmark)
    except ValueError as exc:
        return _with_feedback_toast("Errore Gallica", str(exc), tone="danger")
    except Exception:
        logger.exception("Gallica search failed for shelfmark: %s", shelfmark)
        return _with_feedback_toast(
            "Errore Gallica",
            "Ricerca temporaneamente non disponibile. Riprova più tardi.",
            tone="danger",
        )

    if not results:
        return _with_feedback_toast(
            "Nessun risultato",
            f"Nessun manoscritto trovato per '{shelfmark}' su Gallica.",
            tone="info",
        )

    first = results[0]
    is_direct = bool(first.get("raw", {}).get("_is_direct_match", False))
    if len(results) == 1 and is_direct:
        return render_preview(_build_item_preview_data(first, "Gallica", pages=0))
    return render_search_results_list(results)


def _resolve_manifest_direct(library: str, shelfmark: str) -> tuple[str | None, str | None]:
    try:
        return resolve_shelfmark(library, shelfmark)
    except Exception as exc:
        logger.debug("Direct resolution failed: %s", exc)
        return None, None


def _resolve_vatican_fallback(shelfmark: str):
    from universal_iiif_core.resolvers.discovery import search_vatican

    logger.info("Trying Vatican search for: %s", shelfmark)
    try:
        results = search_vatican(shelfmark, max_results=5)
    except Exception as exc:
        logger.warning("Vatican search failed: %s", exc)
        return None

    if not results:
        return None
    if len(results) == 1:
        first = results[0]
        pages = int(first.get("raw", {}).get("page_count", 0) or 0)
        return render_preview(_build_item_preview_data(first, "Vaticana", pages=pages))
    return render_search_results_list(results)


def _build_not_found_hint(library: str) -> str:
    hint = "Verifica la segnatura."
    if library == "Vaticana":
        hint += " Prova formati come 'Urb.lat.1779' o inserisci solo il numero (es. '1223')."
    return hint


def _analyze_manifest_safe(manifest_url: str):
    try:
        return analyze_manifest(manifest_url), None
    except ValueError as exc:
        return None, _with_feedback_toast("Errore Manifest", str(exc), tone="danger")
    except Exception:
        logger.exception("Manifest analysis failed for URL: %s", manifest_url)
        return None, _with_feedback_toast(
            "Errore Manifest",
            "Manifest IIIF non accessibile. Verifica l'URL o riprova più tardi.",
            tone="danger",
        )


def resolve_manifest(library: str, shelfmark: str):
    """Resolve a shelfmark or URL and return a preview fragment."""
    try:
        if not shelfmark or not shelfmark.strip():
            return _with_feedback_toast("Input mancante", "Inserisci una segnatura o una parola chiave.", tone="danger")

        logger.info("Resolving: lib=%s input=%s", library, shelfmark)

        if "Gallica" in library:
            return _resolve_gallica_flow(shelfmark)

        manifest_url, doc_id = _resolve_manifest_direct(library, shelfmark)
        if not manifest_url and library == "Vaticana" and (fallback_fragment := _resolve_vatican_fallback(shelfmark)):
            return fallback_fragment

        if not manifest_url:
            return _with_feedback_toast(
                "Manoscritto non trovato",
                f"Impossibile risolvere '{shelfmark}' per {library}. {_build_not_found_hint(library)}",
                tone="danger",
            )

        manifest_info, manifest_error = _analyze_manifest_safe(manifest_url)
        if manifest_error:
            return manifest_error
        return render_preview(_build_manifest_preview_data(manifest_info, manifest_url, doc_id, library))

    except ValueError as exc:
        logger.warning("Validation error in resolve_manifest: %s", exc)
        return _with_feedback_toast("Errore Input", str(exc), tone="danger")
    except Exception:
        logger.exception("Unexpected error in resolve_manifest")
        return _with_feedback_toast(
            "Errore Interno",
            "Si è verificato un errore imprevisto. Riprova più tardi.",
            tone="danger",
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
        return _with_toast(
            render_download_status(download_id, doc_id, library, initial_status),
            f"Download avviato per {doc_id}.",
            tone="info",
        )

    except ValueError as e:
        # Known validation errors: safe to expose
        logger.warning("Download validation error: %s", e)
        return _with_feedback_toast("Errore Input", str(e), tone="danger")
    except Exception:
        logger.exception("Download start failed")
        return _with_feedback_toast(
            "Errore Download",
            "Impossibile avviare il download. Riprova più tardi.",
            tone="danger",
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
    return _with_toast(
        render_download_status(download_id, doc_id, library, status_data),
        f"Annullamento richiesto per {doc_id}.",
        tone="info",
    )
