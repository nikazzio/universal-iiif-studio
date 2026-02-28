"""Route handlers for the Export monitor and shared export job orchestration."""

from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fasthtml.common import Request, Response
from starlette.responses import FileResponse

from studio_ui.common.toasts import build_toast
from studio_ui.components.export import render_export_jobs_panel, render_export_page
from studio_ui.components.layout import base_layout
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.logger import get_logger
from universal_iiif_core.services.export.service import (
    ExportCancelledError,
    ExportFeatureNotAvailableError,
    execute_export_job,
    get_export_capabilities,
    is_destination_available,
    is_format_available,
    output_kind_for_format,
    parse_items_csv,
    parse_page_selection,
)
from universal_iiif_core.services.storage.vault_manager import VaultManager

logger = get_logger(__name__)


def _with_toast(fragment, message: str, tone: str = "info"):
    return [fragment, build_toast(message, tone=tone)]


def _should_cancel(job_id: str) -> bool:
    job = VaultManager().get_export_job(job_id) or {}
    return str(job.get("status") or "").lower() == "cancelled"


def _run_export_worker(
    *,
    job_id: str,
    items: list[dict[str, str]],
    export_format: str,
    selection_mode: str,
    selected_pages_raw: str,
    destination: str,
    compression: str,
    include_cover: bool,
    include_colophon: bool,
    cover_curator: str | None,
    cover_description: str | None,
    cover_logo_path: str | None,
) -> None:
    vm = VaultManager()
    total = max(1, len(items))
    vm.update_export_job(job_id, status="running", current_step=0, total_steps=total, error_message=None)

    def _progress(current: int, total_steps: int, _message: str):
        vm.update_export_job(
            job_id,
            status="running",
            current_step=max(0, int(current)),
            total_steps=max(1, int(total_steps)),
            error_message=None,
        )

    try:
        artifact = execute_export_job(
            job_id=job_id,
            items=items,
            export_format=export_format,
            selection_mode=selection_mode,
            selected_pages_raw=selected_pages_raw,
            destination=destination,
            progress_callback=_progress,
            should_cancel=lambda: _should_cancel(job_id),
            compression=compression,
            include_cover=include_cover,
            include_colophon=include_colophon,
            cover_curator=cover_curator,
            cover_description=cover_description,
            cover_logo_path=cover_logo_path,
        )
        if _should_cancel(job_id):
            vm.update_export_job(job_id, status="cancelled", error_message="Cancelled by user")
            return
        vm.update_export_job(
            job_id,
            status="completed",
            current_step=total,
            total_steps=total,
            output_path=str(artifact),
            error_message=None,
        )
    except ExportCancelledError:
        vm.update_export_job(job_id, status="cancelled", error_message="Cancelled by user")
    except Exception as exc:
        logger.exception("Export job failed: %s", job_id)
        vm.update_export_job(job_id, status="error", error_message=str(exc))


def _spawn_export_worker(**kwargs) -> None:
    thread = threading.Thread(target=_run_export_worker, kwargs=kwargs, daemon=True)
    thread.start()


def _item_exists(doc_id: str, library: str) -> bool:
    rows = VaultManager().get_all_manuscripts()
    for row in rows:
        if str(row.get("id") or "") == doc_id and str(row.get("library") or "") == library:
            return True
    return False


def _job_matches_item(job: dict[str, Any], doc_id: str, library: str) -> bool:
    if str(job.get("library") or "") == library:
        try:
            ids = json.loads(str(job.get("doc_ids_json") or "[]"))
            if isinstance(ids, list) and doc_id in [str(i) for i in ids]:
                return True
        except Exception:
            return False
    return False


def list_jobs_for_item(doc_id: str, library: str, *, limit: int = 50) -> list[dict[str, Any]]:
    jobs = VaultManager().list_export_jobs(limit=limit)
    return [job for job in jobs if _job_matches_item(job, doc_id, library)]


def jobs_fragment(*, limit: int = 50, panel_id: str = "export-jobs-panel"):
    jobs = VaultManager().list_export_jobs(limit=limit)
    return render_export_jobs_panel(jobs, polling=True, hx_url="/api/export/jobs", panel_id=panel_id)


def jobs_fragment_for_item(doc_id: str, library: str, *, panel_id: str = "studio-export-jobs"):
    jobs = list_jobs_for_item(doc_id, library, limit=50)
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    hx_url = f"/api/studio/export/jobs?doc_id={encoded_doc}&library={encoded_lib}"
    return render_export_jobs_panel(jobs, polling=True, hx_url=hx_url, panel_id=panel_id)


def start_export_job(
    *,
    items: list[dict[str, str]],
    export_format: str,
    selection_mode: str,
    selected_pages_raw: str,
    destination: str,
    compression: str = "Standard",
    include_cover: bool = True,
    include_colophon: bool = True,
    cover_curator: str | None = None,
    cover_description: str | None = None,
    cover_logo_path: str | None = None,
    capability_flags: dict[str, Any] | None = None,
) -> str:
    """Create one export job row and spawn worker thread; returns job_id."""
    fmt = (export_format or "").strip().lower()
    dst = (destination or "").strip().lower()
    mode = (selection_mode or "all").strip().lower()

    if not items:
        raise ValueError("Nessun item selezionato per export.")
    if not is_format_available(fmt):
        raise ExportFeatureNotAvailableError(f"Formato non disponibile: {fmt}")
    if not is_destination_available(dst):
        raise ExportFeatureNotAvailableError(f"Destinazione non disponibile: {dst}")
    if mode not in {"all", "custom"}:
        raise ValueError("Modalita selezione non valida")
    if mode == "custom":
        parse_page_selection(selected_pages_raw)

    validated_items: list[dict[str, str]] = []
    for item in items:
        doc = str(item.get("doc_id") or "").strip()
        lib = str(item.get("library") or "").strip()
        if not doc or not lib:
            continue
        if not _item_exists(doc, lib):
            raise ValueError(f"Item non presente in Libreria: {lib}::{doc}")
        validated_items.append({"doc_id": doc, "library": lib})

    if not validated_items:
        raise ValueError("Nessun item valido selezionato")

    job_id = f"exp_{uuid.uuid4().hex[:8]}"
    selected_pages_json = "[]"
    if mode == "custom":
        selected_pages_json = json.dumps(parse_page_selection(selected_pages_raw))

    vm = VaultManager()
    vm.create_export_job(
        job_id,
        scope_type="single" if len(validated_items) == 1 else "batch",
        doc_ids_json=json.dumps([item["doc_id"] for item in validated_items]),
        library=validated_items[0]["library"] if len(validated_items) == 1 else "",
        export_format=fmt,
        output_kind=output_kind_for_format(fmt),
        selection_mode=mode,
        selected_pages_json=selected_pages_json,
        destination=dst,
        destination_payload_json="{}",
        capability_flags_json=json.dumps(capability_flags or {"source": "export"}),
        total_steps=len(validated_items),
    )

    _spawn_export_worker(
        job_id=job_id,
        items=validated_items,
        export_format=fmt,
        selection_mode=mode,
        selected_pages_raw=(selected_pages_raw or "").strip(),
        destination=dst,
        compression=(compression or "Standard"),
        include_cover=bool(include_cover),
        include_colophon=bool(include_colophon),
        cover_curator=cover_curator,
        cover_description=cover_description,
        cover_logo_path=cover_logo_path,
    )
    return job_id


def export_page(request: Request):
    """Render monitor-only export page."""
    jobs = VaultManager().list_export_jobs(limit=50)
    capabilities = get_export_capabilities()
    content = render_export_page(jobs, capabilities)
    if request.headers.get("HX-Request") == "true":
        return content
    return base_layout("Export", content, active_page="export")


def export_jobs():
    """Return live export jobs panel for HTMX polling."""
    return jobs_fragment(limit=50)


def export_capabilities():
    """Expose export capabilities including planned-but-disabled items."""
    return get_export_capabilities()


def start_export(
    items_csv: str = "",
    export_format: str = "pdf_images",
    selection_mode: str = "all",
    selected_pages: str = "",
    destination: str = "local_filesystem",
    compression: str = "Standard",
    include_cover: str = "1",
    include_colophon: str = "1",
):
    """Compatibility endpoint for starting jobs from non-Studio contexts."""
    items = parse_items_csv(items_csv)
    try:
        start_export_job(
            items=items,
            export_format=export_format,
            selection_mode=selection_mode,
            selected_pages_raw=selected_pages,
            destination=destination,
            compression=compression,
            include_cover=include_cover != "0",
            include_colophon=include_colophon != "0",
            capability_flags={"source": "export-page"},
        )
    except ExportFeatureNotAvailableError as exc:
        return _with_toast(jobs_fragment(), str(exc), tone="danger")
    except Exception as exc:
        return _with_toast(jobs_fragment(), f"Errore avvio export: {exc}", tone="danger")
    return _with_toast(jobs_fragment(), "Export avviato.", tone="success")


def cancel_export(job_id: str):
    """Cancel one running/queued export job."""
    vm = VaultManager()
    job = vm.get_export_job(job_id)
    if not job:
        return _with_toast(jobs_fragment(), "Job export non trovato.", tone="info")

    status = str(job.get("status") or "").lower()
    if status in {"completed", "error", "cancelled"}:
        return _with_toast(jobs_fragment(), "Job gia terminale.", tone="info")

    vm.update_export_job(job_id, status="cancelled", error_message="Cancelled by user")
    return _with_toast(jobs_fragment(), f"Annullamento richiesto per {job_id}.", tone="info")


def remove_export(job_id: str):
    """Remove one export job from the panel/history."""
    deleted = VaultManager().delete_export_job(job_id)
    if not deleted:
        return _with_toast(jobs_fragment(), "Job export non trovato.", tone="info")
    return _with_toast(jobs_fragment(), f"Job {job_id} rimosso.", tone="success")


def _is_path_allowed(candidate: Path) -> bool:
    cm = get_config_manager()
    allowed_roots = [
        cm.get_exports_dir().resolve(),
        cm.get_downloads_dir().resolve(),
    ]
    for root in allowed_roots:
        if candidate == root or root in candidate.parents:
            return True
    return False


def download_export(job_id: str):
    """Download one completed export artifact by job id."""
    job = VaultManager().get_export_job(job_id) or {}
    output_path = str(job.get("output_path") or "").strip()
    status = str(job.get("status") or "").strip().lower()
    if not output_path or status != "completed":
        return Response("404 Not Found", status_code=404)

    try:
        artifact = Path(output_path).resolve()
    except Exception:
        return Response("404 Not Found", status_code=404)

    if not artifact.exists() or not artifact.is_file():
        return Response("404 Not Found", status_code=404)
    if not _is_path_allowed(artifact):
        return Response("403 Forbidden", status_code=403)

    media_type = "application/octet-stream"
    suffix = artifact.suffix.lower()
    if suffix == ".pdf":
        media_type = "application/pdf"
    elif suffix == ".zip":
        media_type = "application/zip"
    elif suffix == ".txt":
        media_type = "text/plain"
    elif suffix == ".md":
        media_type = "text/markdown"

    return FileResponse(str(artifact), media_type=media_type, filename=artifact.name)
