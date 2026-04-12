"""Studio route handlers — public API consumed by routes/studio.py."""

from __future__ import annotations

import json
import time
from contextlib import suppress
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

from fasthtml.common import Div, Request, Script
from starlette.responses import Response

from studio_ui.common.htmx import history_refresh_script
from studio_ui.common.toasts import build_toast
from studio_ui.components.layout import base_layout
from studio_ui.components.studio.cropper import render_cropper_modal
from studio_ui.components.studio.export import (
    _thumbnail_card_id,
    render_export_pages_summary,
    render_export_thumbnail_card,
    render_export_thumbnails_panel,
    render_export_thumbs_poller,
    render_pdf_inventory_panel,
)
from studio_ui.components.studio.history import history_tab_content
from studio_ui.components.studio.transcription import transcription_tab_content
from studio_ui.config import get_api_key, get_snippets_dir
from studio_ui.ocr_state import OCR_JOBS_STATE, get_ocr_job_state, is_ocr_job_running
from studio_ui.pages.studio import studio_layout
from studio_ui.routes import export_handlers as export_monitor_handlers
from studio_ui.routes.discovery_helpers import start_downloader_thread
from universal_iiif_core.jobs import job_manager
from universal_iiif_core.logger import get_logger
from universal_iiif_core.services.export import list_item_pdf_files
from universal_iiif_core.services.export.service import parse_page_selection
from universal_iiif_core.services.ocr.processor import OCRProcessor
from universal_iiif_core.services.ocr.storage import OCRStorage
from universal_iiif_core.services.scan_optimize import optimize_local_scans
from universal_iiif_core.services.storage.vault_manager import VaultManager
from universal_iiif_core.thumbnail_utils import guess_available_pages

from ._studio.context import (
    _normalize_studio_tab,
    _normalized_studio_context,
    _render_studio_recent_hub,
    _safe_positive_int,
    _save_studio_context_best_effort,
    _studio_panel_refresh_script,
    _studio_recent_limit,
)
from ._studio.export_thumbnails import (
    _build_export_thumbnail_slice,
    _build_studio_export_fragment,
    _resolve_export_thumb_render_state,
)
from ._studio.manifest_helpers import _manifest_missing_response
from ._studio.page_job_prefs import (
    _load_highres_pref,
    _load_stitch_pref,
    _save_highres_pref,
    _save_stitch_pref,
)
from ._studio.page_source_prefs import _persist_optimized_page_source_pref
from ._studio.thumbnail_cache import (
    _is_export_job_active,
    _thumb_page_size,
    _thumb_page_size_options,
    _to_downloads_url,
)

# ---------------------------------------------------------------------------
# Helpers from _studio subpackage
# ---------------------------------------------------------------------------
from ._studio.ui_utils import _as_int, _is_truthy_flag, _toast_only, _with_toast
from ._studio.workspace import (
    _build_workspace_base_context,
    _resolve_workspace_manifest_context,
    build_studio_tab_content,
)

logger = get_logger(__name__)
_STUDIO_ALLOWED_TABS = ("transcription", "snippets", "history", "visual", "info", "images", "output", "jobs")


def studio_page(
    request: Request,
    doc_id: str = "",
    library: str = "",
    page: int = 1,
    tab: str = "transcription",
):
    """Render Main Studio Layout."""
    doc_id, library = _normalized_studio_context(doc_id, library)
    active_tab = _normalize_studio_tab(tab or request.query_params.get("tab"))
    is_hx = request.headers.get("HX-Request") == "true"

    if not doc_id or not library:
        return _render_studio_recent_hub(request=request, vault=VaultManager())

    try:
        requested_page = _safe_positive_int(page, 1)
        vault = VaultManager()
        workspace = _build_workspace_base_context(request, doc_id, library, vault)
        if workspace is None:
            return _render_studio_recent_hub(request=request, vault=vault)
        resolved = _resolve_workspace_manifest_context(
            request=request,
            workspace=workspace,
            requested_page=requested_page,
            active_tab=active_tab,
        )
        if resolved is None:
            return _manifest_missing_response(is_hx)

        content = studio_layout(
            workspace["title"],
            library,
            doc_id,
            int(resolved["safe_page"]),
            str(resolved["manifest_url"]),
            resolved["initial_canvas"],
            dict(resolved["manifest_json"]),
            int(workspace["total_pages"]),
            dict(resolved["meta"]),
            export_url=(
                f"/studio/partial/export?doc_id={workspace['doc_q']}&library={workspace['lib_q']}"
                f"&page={resolved['safe_page']}&tab={quote(active_tab, safe='')}"
            ),
            asset_status=str(workspace["ms_row"].get("asset_state") or workspace["ms_row"].get("status") or "unknown"),
            has_native_pdf=(
                bool(workspace["ms_row"].get("has_native_pdf"))
                if workspace["ms_row"].get("has_native_pdf") is not None
                else None
            ),
            pdf_local_available=bool(workspace["ms_row"].get("pdf_local_available")),
            local_pages_count=int(workspace["inventory"].local_pages_count),
            temp_pages_count=int(workspace["inventory"].temp_pages_count),
            manifest_total_pages=int(resolved["manifest_pages"]),
            read_source_mode=str(resolved["read_source_mode"]),
            mirador_enabled=not bool(resolved["should_gate_mirador"]),
            mirador_initial_page=resolved.get("mirador_initial_page"),
            mirador_override_url=str(resolved["mirador_override_url"]),
            active_tab=active_tab,
            source_notice_text=str(resolved.get("source_notice_text") or ""),
            source_notice_tone=str(resolved.get("source_notice_tone") or "info"),
        )
        _save_studio_context_best_effort(
            doc_id=doc_id,
            library=library,
            page=int(resolved["safe_page"]),
            tab=active_tab,
        )
        if is_hx:
            return content
        return base_layout(f"Studio - {workspace['title']}", content, active_page="studio")

    except Exception as e:
        logger.exception("Studio Error")
        message = "Errore caricamento Studio."
        if is_hx:
            return _with_toast(Div(message, cls="p-10"), f"{message} {e}", tone="danger")
        return base_layout("Errore Studio", Div(f"Errore caricamento: {e}", cls="p-10"), active_page="studio")


def get_studio_tabs(doc_id: str, library: str, page: int, tab: str = "transcription"):
    """Get Studio Tabs Content."""
    doc_id, library = unquote(doc_id), unquote(library)
    page_idx = _safe_positive_int(page, 1)
    active_tab = _normalize_studio_tab(tab)
    is_loading = is_ocr_job_running(doc_id, page_idx)
    return build_studio_tab_content(
        doc_id,
        library,
        page_idx,
        active_tab=active_tab,
        is_ocr_loading=is_loading,
    )


def get_history_tab(doc_id: str, library: str, page: int, info_message: str | None = None):
    """Get History Tab Content."""
    doc_id, library = unquote(doc_id), unquote(library)
    page_idx = int(page)
    return Div(
        *history_tab_content(doc_id, page_idx, library, info_message=info_message),
        cls="p-4",
    )


def get_export_tab(
    doc_id: str,
    library: str,
    page: int,
    tab: str = "transcription",
    subtab: str = "",
    thumb_page: int = 1,
    page_size: int = 0,
    selected_pages: str = "",
    build_subtab: str = "generate",
):
    """Get Studio Export tab content."""
    _ = _safe_positive_int(page, 1)
    safe_tab = _normalize_studio_tab(tab)
    safe_subtab = str(subtab or "").strip().lower()
    if safe_subtab not in {"pages", "build", "jobs"}:
        safe_subtab = {
            "images": "pages",
            "output": "build",
            "jobs": "jobs",
        }.get(safe_tab, "pages")
    safe_build_subtab = str(build_subtab or "generate").strip().lower()
    if safe_build_subtab not in {"generate", "files"}:
        safe_build_subtab = "generate"
    doc_id, library = unquote(doc_id), unquote(library)
    return _build_studio_export_fragment(
        doc_id,
        library,
        thumb_page=int(thumb_page or 1),
        page_size=int(page_size or 0),
        selected_pages_raw=selected_pages,
        selected_subtab=safe_subtab,
        selected_build_subtab=safe_build_subtab,
    )


def get_studio_export_jobs(doc_id: str, library: str):
    """Return per-item export jobs panel for polling."""
    doc_id, library = unquote(doc_id), unquote(library)
    return export_monitor_handlers.jobs_fragment_for_item(doc_id, library, panel_id="studio-export-jobs")


def get_studio_export_pdf_list(doc_id: str, library: str):
    """Return per-item PDF inventory panel for polling."""
    doc_id, library = unquote(doc_id), unquote(library)
    pdf_files = list_item_pdf_files(doc_id, library)
    for row in pdf_files:
        row["download_url"] = _to_downloads_url(Path(str(row.get("path") or "")))
    jobs = export_monitor_handlers.list_jobs_for_item(doc_id, library, limit=50)
    has_active_jobs = any(_is_export_job_active(job) for job in jobs)
    return render_pdf_inventory_panel(
        pdf_files,
        doc_id=doc_id,
        library=library,
        polling=has_active_jobs,
    )


def get_studio_export_thumbs(
    doc_id: str,
    library: str,
    thumb_page: int = 1,
    page_size: int = 0,
):
    """Return one thumbnails page slice for Studio Export tab."""
    doc_id, library = unquote(doc_id), unquote(library)
    thumb_render_state = _resolve_export_thumb_render_state(doc_id=doc_id, library=library)
    thumb_state = _build_export_thumbnail_slice(
        doc_id,
        library,
        thumb_page=int(thumb_page or 1),
        page_size=int(page_size or 0),
        page_delta_by_num=thumb_render_state["page_delta_by_num"],
        page_feedback_by_num=thumb_render_state["resolved_highres_feedback_by_num"],
        stitch_feedback_by_num=thumb_render_state["resolved_stitch_feedback_by_num"],
        optimize_feedback_by_num=thumb_render_state["resolved_opt_feedback_by_num"],
    )
    return render_export_thumbnails_panel(
        doc_id=doc_id,
        library=library,
        thumbnails=list(thumb_state.get("items") or []),
        thumb_page=int(thumb_state.get("thumb_page") or 1),
        thumb_page_count=int(thumb_state.get("thumb_page_count") or 1),
        total_pages=int(thumb_state.get("total_pages") or 0),
        page_size=int(thumb_state.get("page_size") or _thumb_page_size(doc_id=doc_id)),
        page_size_options=_thumb_page_size_options(),
        has_active_page_actions=bool(thumb_render_state["has_active_page_actions"]),
    )


def _render_export_thumb_card_fragment(
    *,
    doc_id: str,
    library: str,
    page_num: int,
    thumb_page: int,
    page_size: int,
    hx_swap_oob: str | None = None,
):
    thumb_render_state = _resolve_export_thumb_render_state(doc_id=doc_id, library=library)
    paths = OCRStorage().get_document_paths(doc_id, library)
    available_pages = guess_available_pages(Path(paths["scans"]))
    if page_num not in available_pages:
        attrs: dict[str, str] = {"id": _thumbnail_card_id(page_num), "cls": "hidden"}
        if hx_swap_oob:
            attrs["hx_swap_oob"] = hx_swap_oob
        return Div("", **attrs)
    single_thumb_page = available_pages.index(page_num) + 1
    thumb_state = _build_export_thumbnail_slice(
        doc_id,
        library,
        thumb_page=single_thumb_page,
        page_size=1,
        persist_page_size=False,
        page_delta_by_num=thumb_render_state["page_delta_by_num"],
        page_feedback_by_num=thumb_render_state["resolved_highres_feedback_by_num"],
        stitch_feedback_by_num=thumb_render_state["resolved_stitch_feedback_by_num"],
        optimize_feedback_by_num=thumb_render_state["resolved_opt_feedback_by_num"],
    )
    items = list(thumb_state.get("items") or [])
    if not items:
        attrs = {"id": _thumbnail_card_id(page_num), "cls": "hidden"}
        if hx_swap_oob:
            attrs["hx_swap_oob"] = hx_swap_oob
        return Div("", **attrs)
    return render_export_thumbnail_card(
        item=items[0],
        doc_id=doc_id,
        library=library,
        thumb_page=thumb_page,
        page_size=page_size,
        hx_swap_oob=hx_swap_oob,
    )


def get_studio_export_thumbs_live(
    doc_id: str,
    library: str,
    thumb_page: int = 1,
    page_size: int = 0,
):
    """Return out-of-band updates for visible thumbnail cards and poller state."""
    doc_id, library = unquote(doc_id), unquote(library)
    thumb_render_state = _resolve_export_thumb_render_state(doc_id=doc_id, library=library)
    thumb_state = _build_export_thumbnail_slice(
        doc_id,
        library,
        thumb_page=int(thumb_page or 1),
        page_size=int(page_size or 0),
        page_delta_by_num=thumb_render_state["page_delta_by_num"],
        page_feedback_by_num=thumb_render_state["resolved_highres_feedback_by_num"],
        stitch_feedback_by_num=thumb_render_state["resolved_stitch_feedback_by_num"],
        optimize_feedback_by_num=thumb_render_state["resolved_opt_feedback_by_num"],
    )
    fragments = [
        render_export_thumbnail_card(
            item=item,
            doc_id=doc_id,
            library=library,
            thumb_page=int(thumb_state.get("thumb_page") or 1),
            page_size=int(thumb_state.get("page_size") or _thumb_page_size(doc_id=doc_id)),
            hx_swap_oob=f"outerHTML:#{_thumbnail_card_id(int(item.get('page') or 0))}",
        )
        for item in list(thumb_state.get("items") or [])
    ]
    fragments.append(
        render_export_pages_summary(
            scan_summary=dict(thumb_state.get("scan_summary") or {}),
            thumb_total_pages=int(thumb_state.get("total_pages") or 0),
            thumb_page=int(thumb_state.get("thumb_page") or 1),
            thumb_page_count=int(thumb_state.get("thumb_page_count") or 1),
            thumb_page_size=int(thumb_state.get("page_size") or _thumb_page_size(doc_id=doc_id)),
            hx_swap_oob="outerHTML:#studio-export-pages-summary",
        )
    )
    fragments.append(
        render_export_thumbs_poller(
            doc_id=doc_id,
            library=library,
            thumb_page=int(thumb_state.get("thumb_page") or 1),
            page_size=int(thumb_state.get("page_size") or _thumb_page_size(doc_id=doc_id)),
            has_active_page_actions=bool(thumb_render_state["has_active_page_actions"]),
            hx_swap_oob="outerHTML:#studio-export-live-state-poller",
        )
    )
    return fragments


def get_studio_export_live_state(
    doc_id: str,
    library: str,
    thumb_page: int = 1,
    page_size: int = 0,
    selected_pages: str = "",
    subtab: str = "pages",
    build_subtab: str = "generate",
):
    """Polling endpoint for in-place Studio Export state refresh."""
    doc_id, library = unquote(doc_id), unquote(library)
    safe_subtab = str(subtab or "pages").strip().lower()
    if safe_subtab not in {"pages", "build", "jobs"}:
        safe_subtab = "pages"
    safe_build_subtab = str(build_subtab or "generate").strip().lower()
    if safe_build_subtab not in {"generate", "files"}:
        safe_build_subtab = "generate"
    return _build_studio_export_fragment(
        doc_id,
        library,
        thumb_page=int(thumb_page or 1),
        page_size=int(page_size or 0),
        selected_pages_raw=selected_pages,
        selected_subtab=safe_subtab,
        selected_build_subtab=safe_build_subtab,
    )


def save_studio_context_api(
    doc_id: str = "",
    library: str = "",
    page: int = 1,
    tab: str = "transcription",
):
    """Persist current Studio context (page + active tab)."""
    doc = str(unquote(doc_id or "")).strip()
    lib = str(unquote(library or "")).strip()
    if not doc or not lib:
        return Response("Missing doc_id/library", status_code=400)
    safe_page = _safe_positive_int(page, 1)
    safe_tab = _normalize_studio_tab(tab)
    if str(tab or "").strip().lower() not in _STUDIO_ALLOWED_TABS:
        return Response("Invalid tab", status_code=400)
    try:
        VaultManager().save_studio_context(
            doc_id=doc,
            library=lib,
            page=safe_page,
            tab=safe_tab,
            max_recent=_studio_recent_limit(),
        )
    except Exception:
        logger.warning("Studio context save failed for %s/%s", lib, doc, exc_info=True)
    return Response(status_code=204)


def start_studio_export(
    doc_id: str,
    library: str,
    selection_mode: str = "all",
    selected_pages: str = "",
    thumb_page: int = 1,
    page_size: int = 0,
    export_format: str = "pdf_images",
    compression: str = "Standard",
    include_cover: str = "",
    include_colophon: str = "",
    cover_curator: str = "",
    cover_description: str = "",
    cover_logo_path: str = "",
    pdf_profile: str = "",
    image_source_mode: str = "",
    image_max_long_edge_px: int = 0,
    image_jpeg_quality: int = 0,
    force_remote_refetch: str = "",
    cleanup_temp_after_export: str = "",
    max_parallel_page_fetch: int = 0,
    subtab: str = "pages",
    build_subtab: str = "generate",
):
    """Start one export job from Studio for the current item."""
    doc_id, library = unquote(doc_id), unquote(library)
    include_cover_bool = _is_truthy_flag(include_cover)
    include_colophon_bool = _is_truthy_flag(include_colophon)
    selected_subtab = str(subtab or "pages").strip().lower()
    if selected_subtab not in {"pages", "build", "jobs"}:
        selected_subtab = "pages"
    selected_build_subtab = str(build_subtab or "generate").strip().lower()
    if selected_build_subtab not in {"generate", "files"}:
        selected_build_subtab = "generate"
    if include_cover == "":
        include_cover_bool = True
    if include_colophon == "":
        include_colophon_bool = True

    try:
        export_monitor_handlers.start_export_job(
            items=[{"doc_id": doc_id, "library": library}],
            export_format=export_format,
            selection_mode=selection_mode,
            selected_pages_raw=selected_pages,
            destination="local_filesystem",
            compression=compression,
            include_cover=include_cover_bool,
            include_colophon=include_colophon_bool,
            cover_curator=cover_curator or None,
            cover_description=cover_description or None,
            cover_logo_path=cover_logo_path or None,
            profile_name=pdf_profile or None,
            image_source_mode=image_source_mode or "local_balanced",
            image_max_long_edge_px=_as_int(image_max_long_edge_px, 0),
            image_jpeg_quality=_as_int(image_jpeg_quality, 82),
            force_remote_refetch=_is_truthy_flag(force_remote_refetch),
            cleanup_temp_after_export=_is_truthy_flag(cleanup_temp_after_export) or cleanup_temp_after_export == "",
            max_parallel_page_fetch=max(1, _as_int(max_parallel_page_fetch, 2)),
            capability_flags={"source": "studio-tab"},
        )
    except Exception as exc:
        return _with_toast(
            _build_studio_export_fragment(
                doc_id,
                library,
                thumb_page=int(thumb_page or 1),
                page_size=int(page_size or 0),
                selected_pages_raw=selected_pages,
                selected_subtab=selected_subtab,
                selected_build_subtab=selected_build_subtab,
            ),
            f"Errore avvio export: {exc}",
            tone="danger",
        )

    return _with_toast(
        _build_studio_export_fragment(
            doc_id,
            library,
            thumb_page=int(thumb_page or 1),
            page_size=int(page_size or 0),
            selected_pages_raw=selected_pages,
            selected_subtab=selected_subtab,
            selected_build_subtab=selected_build_subtab,
        ),
        "Export PDF avviato per l'item corrente.",
        tone="success",
    )


def optimize_studio_export_scans(
    doc_id: str,
    library: str,
    thumb_page: int = 1,
    page_size: int = 0,
    selected_pages: str = "",
    optimize_scope: str = "all",
):
    """Optimize local scans for the current item from Studio Export."""
    doc_id, library = unquote(doc_id), unquote(library)
    scope = str(optimize_scope or "all").strip().lower()
    target_pages: set[int] | None = None
    if scope in {"selected", "selection"}:
        try:
            parsed = parse_page_selection(selected_pages or "")
        except ValueError as exc:
            return _with_toast(
                _build_studio_export_fragment(
                    doc_id,
                    library,
                    thumb_page=int(thumb_page or 1),
                    page_size=int(page_size or 0),
                    selected_pages_raw=selected_pages,
                    selected_subtab="pages",
                ),
                f"Selezione non valida: {exc}",
                tone="danger",
            )
        target_pages = {int(page) for page in parsed if int(page) > 0}
        if not target_pages:
            return _with_toast(
                _build_studio_export_fragment(
                    doc_id,
                    library,
                    thumb_page=int(thumb_page or 1),
                    page_size=int(page_size or 0),
                    selected_pages_raw=selected_pages,
                    selected_subtab="pages",
                ),
                "Nessuna pagina selezionata da ottimizzare.",
                tone="warning",
            )

    result = optimize_local_scans(doc_id, library, target_pages=target_pages)
    meta = dict(result.get("meta") or {})
    _persist_optimized_page_source_pref(doc_id, meta)

    optimize_feedback = {
        "optimized_pages": int(meta.get("optimized_pages") or 0),
        "skipped_pages": int(meta.get("skipped_pages") or 0),
        "errors": int(meta.get("errors") or 0),
        "bytes_before": int(meta.get("bytes_before") or 0),
        "bytes_after": int(meta.get("bytes_after") or 0),
        "bytes_saved": int(meta.get("bytes_saved") or 0),
        "savings_percent": float(meta.get("savings_percent") or 0.0),
        "optimized_at": str(meta.get("optimized_at") or ""),
        "scope": "selected" if target_pages else "all",
    }
    return _with_toast(
        _build_studio_export_fragment(
            doc_id,
            library,
            thumb_page=int(thumb_page or 1),
            page_size=int(page_size or 0),
            selected_pages_raw=selected_pages,
            selected_subtab="pages",
            optimize_feedback=optimize_feedback,
        ),
        str(result.get("message") or "Ottimizzazione completata."),
        tone=str(result.get("tone") or "info"),
    )


def optimize_studio_export_page(
    doc_id: str,
    library: str,
    page: int,
    thumb_page: int = 1,
    page_size: int = 0,
):
    """Optimize a single page and refresh only the affected thumbnail card."""
    doc_id, library = unquote(doc_id), unquote(library)
    page_num = max(1, int(page or 1))
    result = optimize_local_scans(doc_id, library, target_pages={page_num})
    meta = dict(result.get("meta") or {})
    _persist_optimized_page_source_pref(doc_id, meta)
    card = _render_export_thumb_card_fragment(
        doc_id=doc_id,
        library=library,
        page_num=page_num,
        thumb_page=int(thumb_page or 1),
        page_size=int(page_size or 0),
    )
    tone = str(result.get("tone") or "info")
    message = str(result.get("message") or "Ottimizzazione completata.")
    if tone == "danger":
        return _with_toast(card, message, tone="danger")
    return card


def _thumbs_with_toast(
    *,
    doc_id: str,
    library: str,
    page_num: int,
    thumb_page: int,
    page_size: int,
    message: str,
    tone: str,
):
    card = _render_export_thumb_card_fragment(
        doc_id=doc_id,
        library=library,
        page_num=page_num,
        thumb_page=int(thumb_page or 1),
        page_size=int(page_size or 0),
    )
    thumb_render_state = _resolve_export_thumb_render_state(doc_id=doc_id, library=library)
    poller = render_export_thumbs_poller(
        doc_id=doc_id,
        library=library,
        thumb_page=int(thumb_page or 1),
        page_size=int(page_size or 0),
        has_active_page_actions=bool(thumb_render_state["has_active_page_actions"]),
        hx_swap_oob="outerHTML:#studio-export-live-state-poller",
    )
    return [card, poller, build_toast(message, tone=tone)]


def _queue_page_download_job(
    *,
    doc_id: str,
    library: str,
    page_num: int,
    thumb_page: int,
    page_size: int,
    pref_loader,
    pref_saver,
    action_error_text: str,
    start_kwargs: dict[str, Any],
):
    manifest_url = str((VaultManager().get_manuscript(doc_id) or {}).get("manifest_url") or "").strip()
    if not manifest_url:
        return _thumbs_with_toast(
            doc_id=doc_id,
            library=library,
            page_num=page_num,
            thumb_page=thumb_page,
            page_size=page_size,
            message="Manifest URL non disponibile per questo item.",
            tone="danger",
        )

    try:
        job_id = start_downloader_thread(
            manifest_url=manifest_url,
            doc_id=doc_id,
            library=library,
            target_pages={page_num},
            force_redownload=True,
            overwrite_existing_scans=True,
            job_origin="studio_export_page",
            **start_kwargs,
        )
    except Exception as exc:
        return _thumbs_with_toast(
            doc_id=doc_id,
            library=library,
            page_num=page_num,
            thumb_page=thumb_page,
            page_size=page_size,
            message=f"{action_error_text}: {exc}",
            tone="danger",
        )

    pref = pref_loader(doc_id)
    pref[page_num] = {"job_id": job_id, "state": "queued", "source_ts": ""}
    with suppress(Exception):
        pref_saver(doc_id, pref)

    card = _render_export_thumb_card_fragment(
        doc_id=doc_id,
        library=library,
        page_num=page_num,
        thumb_page=int(thumb_page or 1),
        page_size=int(page_size or 0),
    )
    poller = render_export_thumbs_poller(
        doc_id=doc_id,
        library=library,
        thumb_page=int(thumb_page or 1),
        page_size=int(page_size or 0),
        has_active_page_actions=True,
        hx_swap_oob="outerHTML:#studio-export-live-state-poller",
    )
    return [card, poller]


def download_highres_export_page(
    doc_id: str,
    library: str,
    page: int,
    thumb_page: int = 1,
    page_size: int = 0,
    selected_pages: str = "",
):
    """Queue a page-only high-resolution refresh for one local scan."""
    doc_id, library = unquote(doc_id), unquote(library)
    page_num = max(1, int(page or 1))
    _ = selected_pages
    return _queue_page_download_job(
        doc_id=doc_id,
        library=library,
        page_num=page_num,
        thumb_page=int(thumb_page or 1),
        page_size=int(page_size or 0),
        pref_loader=_load_highres_pref,
        pref_saver=_save_highres_pref,
        action_error_text=f"Errore download high-res pagina {page_num}",
        start_kwargs={"force_max_resolution": True, "stitch_mode": "direct_only"},
    )


def download_stitch_export_page(
    doc_id: str,
    library: str,
    page: int,
    thumb_page: int = 1,
    page_size: int = 0,
):
    """Queue a page-only refresh using the same strategy configured for normal volume downloads."""
    doc_id, library = unquote(doc_id), unquote(library)
    page_num = max(1, int(page or 1))
    return _queue_page_download_job(
        doc_id=doc_id,
        library=library,
        page_num=page_num,
        thumb_page=int(thumb_page or 1),
        page_size=int(page_size or 0),
        pref_loader=_load_stitch_pref,
        pref_saver=_save_stitch_pref,
        action_error_text=f"Errore strategia standard pagina {page_num}",
        start_kwargs={},
    )


def run_ocr_async(doc_id: str, library: str, page: int, engine: str, model: str | None = None):
    """Run OCR asynchronously on a document page."""
    logger.info(
        "🔥 [API] run_ocr_async RECEIVED: doc=%s lib=%s pag=%s eng=%s mod=%s", doc_id, library, page, engine, model
    )
    doc_id, library = unquote(doc_id), unquote(library)
    logger.debug("🔓 [API] Unquoted: doc=%s lib=%s", doc_id, library)
    page_idx = int(page)
    OCR_JOBS_STATE[(doc_id, page_idx)] = {
        "status": "running",
        "timestamp": time.time(),
    }

    def _ocr_worker():
        try:
            storage = OCRStorage()
            paths = storage.get_document_paths(doc_id, library)
            image_path = Path(paths["scans"]) / f"pag_{page_idx - 1:04d}.jpg"

            logger.info("🧵 OCR Worker started for %s [Page %s] using %s", doc_id, page_idx, engine)

            from PIL import Image

            if not image_path.exists():
                logger.error("❌ Image not found for OCR: %s", image_path)
                OCR_JOBS_STATE[(doc_id, page_idx)] = {
                    "status": "error",
                    "message": f"Immagine non trovata: {image_path.name}",
                    "timestamp": time.time(),
                }
                return

            with Image.open(str(image_path)) as img:
                logger.debug("📸 Image loaded successfully: %s (%s)", image_path, img.size)

                # Instantiate processor with all keys
                processor = OCRProcessor(
                    openai_api_key=get_api_key("openai"),
                    anthropic_api_key=get_api_key("anthropic"),
                    google_api_key=get_api_key("google_vision"),
                    hf_token=get_api_key("huggingface"),
                )

                logger.debug("🚀 Dispatching OCR request to processor...")

                # Use unified entry point
                res = processor.process_page(img, engine=engine, model=model)

            if res.get("error"):
                logger.error("❌ OCR Error for %s p%s: %s", doc_id, page_idx, res["error"])
                OCR_JOBS_STATE[(doc_id, page_idx)] = {
                    "status": "error",
                    "message": str(res["error"]),
                    "timestamp": time.time(),
                }
            else:
                storage.save_transcription(doc_id, page_idx, res, library)
                logger.info("✅ Async OCR success & auto-saved: %s p%s", doc_id, page_idx)
                OCR_JOBS_STATE[(doc_id, page_idx)] = {
                    "status": "completed",
                    "message": f"OCR completato e salvato (pag. {page_idx}).",
                    "timestamp": time.time(),
                }

        except Exception as e:
            err_msg = str(e)
            logger.exception("💥 Critical Failure in Async OCR worker for %s p%s", doc_id, page_idx)
            OCR_JOBS_STATE[(doc_id, page_idx)] = {
                "status": "error",
                "message": f"Critical Error: {err_msg}",
                "timestamp": time.time(),
            }

    def _ocr_task(progress_callback=None, **_kwargs):
        _ocr_worker()
        return None

    job_manager.submit_job(_ocr_task, job_type="ocr")

    # Return the tab in loading state
    return transcription_tab_content(doc_id, library, page_idx, is_loading=True)


def check_ocr_status(doc_id: str, library: str, page: int):
    """Check OCR job status for a document page."""
    doc_id, library = unquote(doc_id), unquote(library)
    page_idx = int(page)
    logger.debug("🔎 Checking OCR poll status for %s doc=%s lib=%s", page_idx, doc_id, library)

    job_state = get_ocr_job_state(doc_id, page_idx)
    error_msg = None
    toast = None
    if job_state and job_state.get("status") == "error":
        logger.warning("📍 Polling detected error for %s p%s: %s", doc_id, page_idx, job_state["message"])
        error_msg = job_state.get("message")
        toast = build_toast(f"OCR fallito (pag. {page_idx}): {error_msg}", tone="danger")

    is_loading = is_ocr_job_running(doc_id, page_idx)
    if is_loading:
        logger.debug("⌛ OCR still processing for %s p%s; continuing spinner", doc_id, page_idx)
    else:
        logger.info("📡 Polling resolved or idle for %s p%s; refreshing panel", doc_id, page_idx)
        if job_state and job_state.get("status") == "completed":
            completion_message = job_state.get("message") or f"OCR completato (pag. {page_idx})."
            toast = build_toast(completion_message, tone="success")

    if job_state and not is_loading and job_state.get("status") in {"completed", "error"}:
        OCR_JOBS_STATE.pop((doc_id, page_idx), None)

    # While loading: return spinner overlay that continues polling
    if is_loading:
        panel = Div(
            build_studio_tab_content(
                doc_id,
                library,
                page_idx,
                is_ocr_loading=True,
                ocr_error=error_msg,
                history_message=error_msg,
            ),
            id="studio-right-panel",
            cls="flex-1 overflow-hidden h-full",
        )
        return [panel, toast] if toast else panel

    # Completed or error: use HX-Redirect to reload the Studio page cleanly.
    # This ensures SimpleMDE and all JS re-initialise properly.
    from starlette.responses import Response

    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    redirect_url = f"/studio?doc_id={encoded_doc}&library={encoded_lib}&page={page_idx}&tab=transcription"

    headers = {"HX-Redirect": redirect_url}
    if toast:
        # Can't send OOB toast with redirect, but the page reload will show fresh state
        pass
    return Response(status_code=200, content="", headers=headers)


def restore_transcription(doc_id: str, library: str, page: int, timestamp: str):
    """Restore a previous transcription version from history."""
    doc_id, library = unquote(doc_id), unquote(library)
    page_idx = int(page)
    storage = OCRStorage()
    history_items = storage.load_history(doc_id, page_idx, library)
    entry = next((e for e in history_items if e.get("timestamp") == timestamp), None)
    message = "Versione non trovata."

    if entry:
        restored_entry = {
            "full_text": entry.get("full_text", ""),
            "rich_text": entry.get("rich_text"),
            "lines": entry.get("lines"),
            "engine": "history",
            "status": "restored",
            "average_confidence": entry.get("average_confidence", 0.0),
            "is_manual": True,
            "restored_from": timestamp,
        }
        storage.save_transcription(doc_id, page_idx, restored_entry, library)
        logger.info("🔄 Restored transcription for %s p%s from %s", doc_id, page_idx, timestamp)
        message = f"Versione del {timestamp} ripristinata."

    return [
        Div(
            build_studio_tab_content(
                doc_id,
                library,
                page_idx,
                history_message=message,
            ),
            id="studio-right-panel",
            cls="flex-1 overflow-hidden h-full",
        ),
        build_toast(message, tone="success" if entry else "danger"),
        history_refresh_script(doc_id, library, page_idx, info_message=message),
    ]


def get_cropper(doc_id: str, library: str, page: int):
    """Render Cropper Modal Content."""
    doc_id, library = unquote(doc_id), unquote(library)
    lib_q, doc_q = quote(library, safe=""), quote(doc_id, safe="")
    img_url = f"/iiif/image/{lib_q}/{doc_q}/{page}/full/max/0/default.jpg"
    return render_cropper_modal(doc_id, library, int(page), img_url)


def save_snippet_api(doc_id: str, library: str, page: int, crop_data: str, transcription: str = ""):
    """Save a cropped snippet from the cropper tool."""
    doc_id, library = unquote(doc_id), unquote(library)
    try:
        data = json.loads(crop_data)
        storage = OCRStorage()
        vault = storage.vault
        paths = storage.get_document_paths(doc_id, library)
        image_path = Path(paths["scans"]) / f"pag_{int(page) - 1:04d}.jpg"

        coords = (data["x"], data["y"], data["x"] + data["width"], data["y"] + data["height"])
        crop_bytes = vault.extract_image_snippet(str(image_path), coords)

        if not crop_bytes:
            return build_toast("Impossibile creare il ritaglio richiesto.", tone="danger")

        filename = f"{doc_id}_p{int(page):04d}_{int(time.time())}.png"
        snippet_path = get_snippets_dir() / filename

        with snippet_path.open("wb") as f:
            f.write(crop_bytes)

        vault.save_snippet(
            doc_id, int(page), str(snippet_path), category="Manual", transcription=transcription, coords=data
        )

        return [
            Script(
                "document.getElementById('cropper-modal-container').innerHTML = ''; "
                "htmx.trigger('#tab-snippets', 'click');"
            ),
            build_toast("Snippet salvato correttamente.", tone="success"),
        ]

    except Exception as e:
        logger.exception("Snippet Save Error")
        return build_toast(f"Errore salvataggio snippet: {e}", tone="danger")


def save_transcription(doc_id: str, library: str, page: int, text: str, tab: str = "transcription"):
    """Save manual transcription edits from the Studio."""
    try:
        doc_id, library = unquote(doc_id), unquote(library)
        storage = OCRStorage()
        page_idx = int(page)
        active_tab = _normalize_studio_tab(tab)
        existing = storage.load_transcription(doc_id, page_idx, library)
        normalized_existing = (existing.get("full_text") if existing else "") or ""
        normalized_new = text or ""

        if normalized_existing == normalized_new:
            return [
                Div("", cls="hidden"),
                build_toast("Nessuna modifica rilevata; il testo è identico all'ultima versione.", tone="info"),
                _studio_panel_refresh_script(doc_id, library, page_idx, active_tab),
            ]

        # Save the transcription
        storage.save_transcription(
            doc_id,
            page_idx,
            {"full_text": text, "is_manual": True},
            library,
        )

        return [
            Div("", cls="hidden"),
            build_toast("Modifiche salvate con successo nello storico.", tone="success"),
            _studio_panel_refresh_script(doc_id, library, page_idx, active_tab),
        ]
    except Exception as e:
        return [
            Div("", cls="hidden"),
            build_toast(f"Errore durante il salvataggio: {e}", tone="danger"),
        ]


def delete_snippet(snippet_id: int):
    """Delete a snippet by ID."""
    try:
        OCRStorage().vault.delete_snippet(snippet_id)
        return _toast_only("Snippet eliminato correttamente.", tone="success")
    except Exception as exc:
        logger.exception("Snippet delete error for id=%s", snippet_id)
        return _toast_only(f"Errore durante l'eliminazione dello snippet: {exc}", tone="danger")
