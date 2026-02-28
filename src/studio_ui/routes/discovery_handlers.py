"""Route handlers for the Discovery page and Download Manager.

Handlers are top-level functions so `setup_discovery_routes` can remain
very small and satisfy ruff's complexity check.
"""

from pathlib import Path
from urllib.parse import unquote

from fasthtml.common import Request

from studio_ui.common.toasts import build_toast

# Importiamo i nuovi componenti grafici
from studio_ui.components.discovery import (
    discovery_content,
    render_download_manager,
    render_download_status,
    render_feedback_message,
    render_pdf_capability_badge,
    render_preview,
    render_search_results_list,
)
from studio_ui.components.layout import base_layout
from studio_ui.routes.discovery_helpers import analyze_manifest, start_downloader_thread
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.iiif_logic import total_canvases
from universal_iiif_core.jobs import job_manager
from universal_iiif_core.logger import get_logger
from universal_iiif_core.resolvers.discovery import resolve_shelfmark, search_institut, smart_search
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


def _downloads_doc_path(library: str, doc_id: str) -> Path:
    cm = get_config_manager()
    return cm.get_downloads_dir() / library / doc_id


def _upsert_saved_entry(
    manifest_url: str,
    doc_id: str,
    library: str,
    *,
    label: str = "",
    description: str = "",
    pages: int = 0,
    has_native_pdf: bool | None = None,
    catalog_title: str = "",
    shelfmark: str = "",
    date_label: str = "",
    language_label: str = "",
    source_detail_url: str = "",
    reference_text: str = "",
    item_type: str = "non classificato",
    item_type_confidence: float = 0.0,
    item_type_reason: str = "",
    metadata_json: str = "{}",
) -> None:
    entry_label = (label or doc_id or "Senza Titolo").strip()
    total = int(pages or 0)
    v = VaultManager()
    v.upsert_manuscript(
        doc_id,
        display_title=entry_label,
        title=entry_label,
        catalog_title=(catalog_title or "").strip() or entry_label,
        library=library,
        manifest_url=manifest_url,
        local_path=str(_downloads_doc_path(library, doc_id)),
        status="saved",
        asset_state="saved",
        total_canvases=total,
        downloaded_canvases=0,
        has_native_pdf=1 if has_native_pdf else 0 if has_native_pdf is False else None,
        pdf_local_available=0,
        item_type=item_type or "non classificato",
        item_type_source="auto",
        item_type_confidence=float(item_type_confidence or 0.0),
        item_type_reason=item_type_reason or "",
        missing_pages_json="[]",
        shelfmark=shelfmark or "",
        date_label=date_label or "",
        language_label=language_label or "",
        source_detail_url=source_detail_url or "",
        reference_text=reference_text or "",
        metadata_json=metadata_json or "{}",
    )


def _download_manager_fragment(limit: int = 50):
    jobs = VaultManager().list_download_jobs(limit=limit)
    return render_download_manager(jobs)


def discovery_page(request: Request):
    """Render the Discovery page."""
    is_hx = request.headers.get("HX-Request") == "true"
    manager = _download_manager_fragment()
    if is_hx:
        return discovery_content(initial_preview=None, active_download_fragment=manager)
    content = discovery_content(initial_preview=None, active_download_fragment=manager)
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
        "has_native_pdf": item.get("has_native_pdf"),
    }


def _build_manifest_preview_data(manifest_info: dict, manifest_url: str, doc_id: str | None, library: str) -> dict:
    """Build preview payload from analyzed manifest metadata."""
    return {
        "id": doc_id or manifest_info.get("label", "Unknown"),
        "library": library,
        "url": manifest_url,
        "label": manifest_info.get("catalog_title") or manifest_info.get("label", "Senza Titolo"),
        "description": manifest_info.get("description", "Nessuna descrizione."),
        "pages": manifest_info.get("pages", 0),
        "thumbnail": manifest_info.get("thumbnail"),
        "has_native_pdf": manifest_info.get("has_native_pdf"),
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
        pages = _page_count_from_result(first)
        return render_preview(_build_item_preview_data(first, "Vaticana", pages=pages))
    return render_search_results_list(results)


def _page_count_from_result(item: dict) -> int:
    raw = item.get("raw")
    if not isinstance(raw, dict):
        return 0

    explicit = raw.get("page_count")
    if explicit is not None:
        try:
            return int(explicit or 0)
        except (TypeError, ValueError):
            logger.debug("Invalid page_count in search result raw payload: %r", explicit, exc_info=True)

    try:
        return int(total_canvases(raw))
    except Exception:
        logger.debug("Failed to derive page count from manifest payload", exc_info=True)
        return 0


def _resolve_institut_fallback(shelfmark: str):
    logger.info("Trying Institut de France search for: %s", shelfmark)
    try:
        results = search_institut(shelfmark, max_results=10)
    except Exception as exc:
        logger.warning("Institut search failed: %s", exc)
        return None

    if not results:
        return None
    if len(results) == 1:
        first = results[0]
        pages = _page_count_from_result(first)
        return render_preview(_build_item_preview_data(first, "Institut de France", pages=pages))
    return render_search_results_list(results)


def _build_not_found_hint(library: str) -> str:
    hint = "Verifica la segnatura."
    if library == "Vaticana":
        hint += " Prova formati come 'Urb.lat.1779' o inserisci solo il numero (es. '1223')."
    if library == "Institut de France":
        hint += " Usa ID numerico (es. '17837'), URL viewer o una ricerca testuale."
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
        if (
            not manifest_url
            and library == "Institut de France"
            and (fallback_fragment := _resolve_institut_fallback(shelfmark))
        ):
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


def add_to_library(manifest_url: str, doc_id: str, library: str):
    """Persist a manuscript in Library without starting a download."""
    try:
        manifest_url = unquote(manifest_url)
        doc_id = unquote(doc_id)
        library = unquote(library)
        if not manifest_url or not doc_id or not library:
            return _with_feedback_toast("Dati mancanti", "Manifest, ID e biblioteca sono obbligatori.", tone="danger")

        info, _err = _analyze_manifest_safe(manifest_url)
        info = info or {}
        _upsert_saved_entry(
            manifest_url,
            doc_id,
            library,
            label=info.get("label", doc_id),
            description=info.get("description", ""),
            pages=int(info.get("pages", 0) or 0),
            has_native_pdf=info.get("has_native_pdf"),
            catalog_title=info.get("catalog_title", ""),
            shelfmark=info.get("shelfmark", ""),
            date_label=info.get("date_label", ""),
            language_label=info.get("language_label", ""),
            source_detail_url=info.get("source_detail_url", ""),
            reference_text=info.get("reference_text", ""),
            item_type=info.get("item_type", "non classificato"),
            item_type_confidence=float(info.get("item_type_confidence", 0.0) or 0.0),
            item_type_reason=info.get("item_type_reason", ""),
            metadata_json=info.get("metadata_json", "{}"),
        )
        return _with_toast(
            _download_manager_fragment(),
            f"Aggiunto in Libreria: {doc_id}",
            tone="success",
        )
    except Exception:
        logger.exception("Add to library failed")
        return _with_feedback_toast("Errore Libreria", "Impossibile salvare l'entry in Libreria.", tone="danger")


def add_and_download(manifest_url: str, doc_id: str, library: str):
    """Persist a manuscript and enqueue download."""
    try:
        manifest_url = unquote(manifest_url)
        doc_id = unquote(doc_id)
        library = unquote(library)
        if not manifest_url or not doc_id or not library:
            return _with_feedback_toast("Dati mancanti", "Manifest, ID e biblioteca sono obbligatori.", tone="danger")

        info, _err = _analyze_manifest_safe(manifest_url)
        info = info or {}
        _upsert_saved_entry(
            manifest_url,
            doc_id,
            library,
            label=info.get("label", doc_id),
            description=info.get("description", ""),
            pages=int(info.get("pages", 0) or 0),
            has_native_pdf=info.get("has_native_pdf"),
            catalog_title=info.get("catalog_title", ""),
            shelfmark=info.get("shelfmark", ""),
            date_label=info.get("date_label", ""),
            language_label=info.get("language_label", ""),
            source_detail_url=info.get("source_detail_url", ""),
            reference_text=info.get("reference_text", ""),
            item_type=info.get("item_type", "non classificato"),
            item_type_confidence=float(info.get("item_type_confidence", 0.0) or 0.0),
            item_type_reason=info.get("item_type_reason", ""),
            metadata_json=info.get("metadata_json", "{}"),
        )

        download_id = start_downloader_thread(manifest_url, doc_id, library)

        return _with_toast(
            _download_manager_fragment(),
            f"Download accodato per {doc_id} (job: {download_id[:12]}...).",
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


def start_download(manifest_url: str, doc_id: str, library: str):
    """Backward-compatible endpoint kept for legacy callers."""
    return add_and_download(manifest_url, doc_id, library)


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


def download_manager():
    """Polling endpoint for the right-side Download Manager panel."""
    return _download_manager_fragment()


def cancel_download(download_id: str, doc_id: str = "", library: str = ""):
    """Cancel a queued/running download job."""
    vault = VaultManager()
    job = vault.get_download_job(download_id) or {}
    if not doc_id:
        doc_id = str(job.get("doc_id") or "")
    if not library:
        library = str(job.get("library") or "")
    curr = job.get("current", 0)
    total = job.get("total", 0)
    try:
        # Mark as cancelling first so UI shows immediate feedback
        vault.update_download_job(download_id, current=curr, total=total, status="cancelling", error="Cancelling")
    except Exception:
        logger.debug("Failed to mark job cancelled", exc_info=True)

    try:
        job_manager.request_cancel(download_id)
    except Exception:
        logger.debug("Failed to request job cancellation from JobManager", exc_info=True)

    return _with_toast(
        _download_manager_fragment(),
        f"Annullamento richiesto per {doc_id}.",
        tone="info",
    )


def pause_download(download_id: str):
    """Pause a queued/running download job."""
    vault = VaultManager()
    job = vault.get_download_job(download_id) or {}
    if not job:
        return _with_feedback_toast("Job non trovato", "Il download selezionato non esiste.", tone="info")

    status = str(job.get("status") or "").lower()
    doc_id = str(job.get("doc_id") or download_id)
    curr = int(job.get("current") or 0)
    total = int(job.get("total") or 0)

    if status == "paused":
        return _with_feedback_toast("Già in pausa", "Questo job è già in pausa.", tone="info")
    if status not in {"queued", "running", "cancelling"}:
        return _with_feedback_toast("Pausa non disponibile", "Il job non è in uno stato pausabile.", tone="info")

    if status == "running":
        try:
            vault.update_download_job(download_id, current=curr, total=total, status="cancelling", error="Pausing")
        except Exception:
            logger.debug("Failed to mark job as pausing", exc_info=True)

    paused = False
    try:
        paused = bool(job_manager.request_pause(download_id))
    except Exception:
        logger.debug("Failed to request job pause", exc_info=True)

    # Fallback for queued jobs not tracked in memory after app restarts.
    if not paused and status == "queued":
        try:
            vault.update_download_job(download_id, current=curr, total=total, status="paused", error="Paused by user")
            paused = True
        except Exception:
            logger.debug("Fallback pause update failed", exc_info=True)

    if not paused:
        return _with_feedback_toast(
            "Pausa non disponibile",
            "Non è stato possibile mettere in pausa il job selezionato.",
            tone="danger",
        )

    return _with_toast(_download_manager_fragment(), f"Pausa richiesta per {doc_id}.", tone="info")


def resume_download(download_id: str):
    """Resume a paused download job by re-queuing a new run."""
    vault = VaultManager()
    job = vault.get_download_job(download_id) or {}
    if not job:
        return _with_feedback_toast("Job non trovato", "Il download selezionato non esiste.", tone="info")

    status = str(job.get("status") or "").lower()
    if status != "paused":
        return _with_feedback_toast("Resume non disponibile", "Il job non è in pausa.", tone="info")

    manifest_url = str(job.get("manifest_url") or "")
    doc_id = str(job.get("doc_id") or "")
    library = str(job.get("library") or "")
    if not manifest_url or not doc_id or not library:
        return _with_feedback_toast("Resume non disponibile", "Dati job insufficienti.", tone="danger")

    try:
        new_download_id = start_downloader_thread(manifest_url, doc_id, library)
        if new_download_id and new_download_id != download_id:
            vault.delete_download_job(download_id)
        return _with_toast(_download_manager_fragment(), f"Resume avviato per {doc_id}.", tone="success")
    except Exception:
        logger.exception("Resume failed for paused job %s", download_id)
        return _with_feedback_toast("Errore Resume", "Impossibile riprendere il download.", tone="danger")


def retry_download(download_id: str):
    """Retry a failed/cancelled job using its stored manifest/doc/library."""
    vault = VaultManager()
    job = vault.get_download_job(download_id) or {}
    manifest_url = str(job.get("manifest_url") or "")
    doc_id = str(job.get("doc_id") or "")
    library = str(job.get("library") or "")
    if not manifest_url or not doc_id or not library:
        return _with_feedback_toast("Retry non disponibile", "Dati job insufficienti.", tone="danger")
    try:
        start_downloader_thread(manifest_url, doc_id, library)
        return _with_toast(_download_manager_fragment(), f"Retry accodato per {doc_id}.", tone="info")
    except Exception:
        logger.exception("Retry enqueue failed for job %s", download_id)
        return _with_feedback_toast("Errore Retry", "Impossibile accodare il retry.", tone="danger")


def remove_download(download_id: str):
    """Remove a terminal download job from the Download Manager."""
    vault = VaultManager()
    job = vault.get_download_job(download_id) or {}
    status = str(job.get("status") or "").lower()
    doc_id = str(job.get("doc_id") or download_id)
    if not job:
        return _with_feedback_toast("Job non trovato", "Il download selezionato non esiste.", tone="info")

    if status in {"queued", "running", "cancelling", "pending", "starting"}:
        return _with_feedback_toast("Rimozione non disponibile", "Annulla prima il download attivo.", tone="info")

    if not vault.delete_download_job(download_id):
        return _with_feedback_toast("Rimozione non riuscita", "Non è stato possibile rimuovere il job.", tone="danger")

    return _with_toast(_download_manager_fragment(), f"Job rimosso: {doc_id}.", tone="success")


def prioritize_download(download_id: str):
    """Move a queued job to queue head."""
    if not job_manager.prioritize_download(download_id):
        return _with_feedback_toast("Priorità non applicata", "Il job non è in coda o non esiste.", tone="info")
    return _with_toast(_download_manager_fragment(), "Job portato in cima alla coda.", tone="success")


def pdf_capability(manifest_url: str):
    """Return a tiny badge with native-PDF capability (lazy-loaded per result card)."""
    manifest_url = unquote(manifest_url or "")
    if not manifest_url:
        return render_pdf_capability_badge(False)
    try:
        info = analyze_manifest(manifest_url)
        has_pdf = bool(info.get("has_native_pdf"))
        return render_pdf_capability_badge(has_pdf)
    except Exception:
        return render_pdf_capability_badge(False)
