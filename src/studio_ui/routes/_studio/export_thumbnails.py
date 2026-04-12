"""Export thumbnail helpers — build thumbnail items & slices for Studio Export tab."""

from __future__ import annotations

import math
from contextlib import suppress
from pathlib import Path
from typing import Any

from studio_ui.components.studio.export import render_studio_export_tab
from studio_ui.routes import export_handlers as export_monitor_handlers
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.logger import get_logger
from universal_iiif_core.services.export import list_item_pdf_files
from universal_iiif_core.services.ocr.storage import OCRStorage
from universal_iiif_core.services.scan_optimize import summarize_scan_folder
from universal_iiif_core.services.storage.vault_manager import VaultManager
from universal_iiif_core.thumbnail_utils import ensure_thumbnail, guess_available_pages
from universal_iiif_core.utils import load_json, save_json

from .download_feedback import (
    _merge_page_feedback,
    _optimize_feedback_from_deltas,
    _resolve_current_image_feedback,
    _resolve_highres_page_feedback,
    _resolve_stitch_page_feedback,
)
from .page_job_prefs import _load_last_optimization_meta, _page_delta_map
from .page_source_prefs import _load_page_source_pref
from .scan_resolution import (
    _local_scan_info,
    _resolve_remote_dims,
    _stats_download_method_map,
    _stats_page_meta_map,
    _verified_direct_dims,
)
from .thumbnail_cache import (
    _export_tab_defaults,
    _is_export_job_active,
    _normalize_remote_cache,
    _prune_remote_cache,
    _prune_stale_thumbnails,
    _remote_cache_limits,
    _thumb_page_size,
    _thumb_page_size_options,
    _to_downloads_url,
)

logger = get_logger(__name__)


def _build_thumbnail_item(
    *,
    page_num: int,
    scans_dir: Path,
    thumbnails_dir: Path,
    max_px: int,
    quality: int,
    manifest_json: dict,
    remote_cache: dict[str, dict],
    remote_probe_enabled: bool,
    page_delta_by_num: dict[int, dict[str, Any]],
    page_feedback_by_num: dict[int, dict[str, str]],
    stitch_feedback_by_num: dict[int, dict[str, str]],
    optimize_feedback_by_num: dict[int, dict[str, str]],
    download_method_by_num: dict[int, str],
    stats_by_num: dict[int, dict[str, Any]],
    force_remote_refresh: bool = False,
) -> tuple[dict[str, Any], int]:
    thumb_path = ensure_thumbnail(
        scans_dir=scans_dir,
        thumbnails_dir=thumbnails_dir,
        page_num_1_based=page_num,
        max_long_edge_px=max_px,
        jpeg_quality=quality,
    )
    thumb_url = _to_downloads_url(thumb_path) if thumb_path else ""
    scan_path = scans_dir / f"pag_{page_num - 1:04d}.jpg"
    local_w, local_h, local_bytes = _local_scan_info(scan_path)
    remote_w, remote_h, remote_service = _resolve_remote_dims(
        page_num=page_num,
        manifest_json=manifest_json,
        remote_cache=remote_cache,
        remote_probe_enabled=remote_probe_enabled,
        force_refresh=force_remote_refresh,
    )
    verified_w, verified_h = _verified_direct_dims(
        page_num=page_num,
        stats_by_num=stats_by_num,
        remote_cache=remote_cache,
    )
    delta_entry = page_delta_by_num.get(page_num) or {}
    delta_saved = 0
    if delta_entry:
        with suppress(Exception):
            delta_saved = int(delta_entry.get("bytes_saved") or 0)
    highres_feedback = page_feedback_by_num.get(page_num) or {}
    stitch_feedback = stitch_feedback_by_num.get(page_num) or {}
    optimize_feedback = optimize_feedback_by_num.get(page_num) or {}
    return (
        {
            "page": page_num,
            "thumb_url": thumb_url,
            "local_width": local_w,
            "local_height": local_h,
            "local_bytes": int(local_bytes),
            "iiif_declared_width": remote_w,
            "iiif_declared_height": remote_h,
            "iiif_service_url": remote_service,
            "verified_direct_width": verified_w,
            "verified_direct_height": verified_h,
            "download_method": str(download_method_by_num.get(page_num) or ""),
            "delta_saved_bytes": int(max(delta_saved, 0)),
            "action_feedback": highres_feedback,
            "highres_feedback": highres_feedback,
            "stitch_feedback": stitch_feedback,
            "optimize_feedback": optimize_feedback,
        },
        int(local_bytes),
    )


def _build_export_thumbnail_slice(
    doc_id: str,
    library: str,
    *,
    thumb_page: int = 1,
    page_size: int | None = None,
    persist_page_size: bool = True,
    include_items: bool = True,
    page_delta_by_num: dict[int, dict[str, Any]] | None = None,
    page_feedback_by_num: dict[int, dict[str, str]] | None = None,
    stitch_feedback_by_num: dict[int, dict[str, str]] | None = None,
    optimize_feedback_by_num: dict[int, dict[str, str]] | None = None,
) -> dict[str, object]:
    storage = OCRStorage()
    paths = storage.get_document_paths(doc_id, library)
    scans_dir = Path(paths["scans"])
    thumbnails_dir = Path(paths["thumbnails"])
    cm = get_config_manager()
    studio_max_px = int(
        cm.get_setting(
            "thumbnails.studio_max_long_edge_px",
            cm.get_setting("thumbnails.max_long_edge_px", 640),
        )
        or 640
    )
    max_px = max(640, min(studio_max_px, 2400))
    studio_quality = int(
        cm.get_setting(
            "thumbnails.studio_jpeg_quality",
            cm.get_setting("thumbnails.jpeg_quality", 86),
        )
        or 86
    )
    quality = max(60, min(studio_quality, 95))
    thumbs_retention = int(cm.get_setting("storage.thumbnails_retention_days", 14) or 14)
    _prune_stale_thumbnails(thumbnails_dir, thumbs_retention)
    safe_page_size = _thumb_page_size(page_size, doc_id=doc_id)
    if persist_page_size and page_size not in {None, 0}:
        try:
            VaultManager().set_manuscript_ui_pref(doc_id, "studio_export_thumb_page_size", safe_page_size)
        except Exception:
            logger.debug("Unable to persist thumbnail page size preference for %s", doc_id, exc_info=True)
    available_pages = guess_available_pages(scans_dir)
    total_pages = len(available_pages)
    page_delta_by_num = page_delta_by_num or {}
    page_feedback_by_num = page_feedback_by_num or {}
    stitch_feedback_by_num = stitch_feedback_by_num or {}
    optimize_feedback_by_num = optimize_feedback_by_num or {}

    if total_pages <= 0:
        scan_summary = summarize_scan_folder(scans_dir)
        return {
            "items": [],
            "available_pages": [],
            "thumb_page": 1,
            "thumb_page_count": 1,
            "total_pages": 0,
            "page_size": safe_page_size,
            "scan_summary": scan_summary,
        }

    thumb_page_count = max(1, math.ceil(total_pages / safe_page_size))
    safe_thumb_page = max(1, min(int(thumb_page or 1), thumb_page_count))
    start = (safe_thumb_page - 1) * safe_page_size
    stop = start + safe_page_size
    page_slice = available_pages[start:stop]
    scan_summary = summarize_scan_folder(scans_dir)

    if not include_items:
        return {
            "items": [],
            "available_pages": available_pages,
            "thumb_page": safe_thumb_page,
            "thumb_page_count": thumb_page_count,
            "total_pages": total_pages,
            "page_size": safe_page_size,
            "scan_summary": scan_summary,
        }

    manifest_json = load_json(paths["manifest"]) or {}
    stats_payload = load_json(paths["stats"]) or {}
    remote_cache_path = Path(paths["data"]) / "remote_resolution_cache.json"
    cache_max_bytes, cache_retention_hours, cache_max_items = _remote_cache_limits(cm)
    remote_cache = _normalize_remote_cache(load_json(remote_cache_path) or {})

    remote_probe_enabled = bool(cm.get_setting("images.probe_remote_max_resolution", True))
    download_method_by_num = _stats_download_method_map(stats_payload)
    stats_by_num = _stats_page_meta_map(stats_payload)
    items: list[dict] = []
    total_bytes = 0
    bytes_min = 0
    bytes_max = 0
    for page_num in page_slice:
        feedback_hint = page_feedback_by_num.get(page_num) or {}
        should_refresh_remote = str(feedback_hint.get("state") or "").strip().lower() in {"queued", "running"}
        item, local_bytes = _build_thumbnail_item(
            page_num=page_num,
            scans_dir=scans_dir,
            thumbnails_dir=thumbnails_dir,
            max_px=max_px,
            quality=quality,
            manifest_json=manifest_json,
            remote_cache=remote_cache,
            remote_probe_enabled=remote_probe_enabled,
            page_delta_by_num=page_delta_by_num,
            page_feedback_by_num=page_feedback_by_num,
            stitch_feedback_by_num=stitch_feedback_by_num,
            optimize_feedback_by_num=optimize_feedback_by_num,
            download_method_by_num=download_method_by_num,
            stats_by_num=stats_by_num,
            force_remote_refresh=should_refresh_remote,
        )
        if local_bytes > 0:
            total_bytes += local_bytes
            bytes_min = local_bytes if bytes_min <= 0 else min(bytes_min, local_bytes)
            bytes_max = max(bytes_max, local_bytes)
        items.append(item)

    remote_cache = _prune_remote_cache(
        remote_cache,
        max_bytes=cache_max_bytes,
        retention_hours=cache_retention_hours,
        max_items=cache_max_items,
    )
    with suppress(Exception):
        save_json(remote_cache_path, remote_cache)

    if total_bytes > 0:
        scan_summary.update(
            {
                "slice_bytes_total": int(total_bytes),
                "slice_bytes_avg": int(total_bytes // max(len(page_slice), 1)),
                "slice_bytes_min": int(bytes_min),
                "slice_bytes_max": int(bytes_max),
            }
        )
    return {
        "items": items,
        "available_pages": available_pages,
        "thumb_page": safe_thumb_page,
        "thumb_page_count": thumb_page_count,
        "total_pages": total_pages,
        "page_size": safe_page_size,
        "scan_summary": scan_summary,
    }


def _build_studio_export_fragment(
    doc_id: str,
    library: str,
    *,
    thumb_page: int = 1,
    page_size: int | None = None,
    selected_pages_raw: str = "",
    selected_subtab: str = "pages",
    selected_build_subtab: str = "generate",
    page_feedback_by_num: dict[int, dict[str, str]] | None = None,
    optimize_feedback: dict[str, Any] | None = None,
):
    thumb_render_state = _resolve_export_thumb_render_state(
        doc_id=doc_id,
        library=library,
        page_feedback_by_num=page_feedback_by_num,
    )
    thumb_state = _build_export_thumbnail_slice(
        doc_id,
        library,
        thumb_page=thumb_page,
        page_size=page_size,
        include_items=False,
        page_delta_by_num=thumb_render_state["page_delta_by_num"],
        page_feedback_by_num=thumb_render_state["resolved_highres_feedback_by_num"],
        stitch_feedback_by_num=thumb_render_state["resolved_stitch_feedback_by_num"],
        optimize_feedback_by_num=thumb_render_state["resolved_opt_feedback_by_num"],
    )
    pdf_files = list_item_pdf_files(doc_id, library)
    for row in pdf_files:
        row["download_url"] = _to_downloads_url(Path(str(row.get("path") or "")))
    jobs = export_monitor_handlers.list_jobs_for_item(doc_id, library, limit=50)
    has_active_jobs = any(_is_export_job_active(job) for job in jobs)
    return render_studio_export_tab(
        doc_id=doc_id,
        library=library,
        thumbnails=list(thumb_state.get("items") or []),
        thumb_page=int(thumb_state.get("thumb_page") or 1),
        thumb_page_count=int(thumb_state.get("thumb_page_count") or 1),
        thumb_total_pages=int(thumb_state.get("total_pages") or 0),
        thumb_page_size=int(thumb_state.get("page_size") or _thumb_page_size(doc_id=doc_id)),
        thumb_page_size_options=_thumb_page_size_options(),
        available_pages=list(thumb_state.get("available_pages") or []),
        selected_pages_raw=(selected_pages_raw or "").strip(),
        pdf_files=pdf_files,
        jobs=jobs,
        has_active_jobs=has_active_jobs,
        export_defaults=_export_tab_defaults(doc_id, library),
        selected_subtab=selected_subtab,
        selected_build_subtab=selected_build_subtab,
        scan_summary=dict(thumb_state.get("scan_summary") or {}),
        optimization_meta=thumb_render_state["optimization_meta"],
        optimize_feedback=optimize_feedback or {},
        has_active_page_actions=bool(thumb_render_state["has_active_page_actions"]),
        defer_thumbs_load=True,
    )


def _resolve_export_thumb_render_state(
    *,
    doc_id: str,
    library: str,
    page_feedback_by_num: dict[int, dict[str, str]] | None = None,
) -> dict[str, Any]:
    optimization_meta = _load_last_optimization_meta(doc_id)
    page_delta_by_num = _page_delta_map(optimization_meta)
    optimize_feedback_by_num = _optimize_feedback_from_deltas(
        page_delta_by_num,
        optimized_at=str(optimization_meta.get("optimized_at") or ""),
    )
    highres_feedback_by_num, has_active_highres_jobs = _resolve_highres_page_feedback(doc_id, library)
    stitch_feedback_by_num, has_active_stitch_jobs = _resolve_stitch_page_feedback(doc_id, library)
    page_source_pref = _load_page_source_pref(doc_id)
    merged_feedback_by_num = _merge_page_feedback(highres_feedback_by_num, page_feedback_by_num)
    resolved_highres_feedback_by_num, resolved_stitch_feedback_by_num, resolved_opt_feedback_by_num = (
        _resolve_current_image_feedback(
            merged_feedback_by_num,
            stitch_feedback_by_num,
            optimize_feedback_by_num,
            page_source_pref,
        )
    )
    return {
        "optimization_meta": optimization_meta,
        "page_delta_by_num": page_delta_by_num,
        "resolved_highres_feedback_by_num": resolved_highres_feedback_by_num,
        "resolved_stitch_feedback_by_num": resolved_stitch_feedback_by_num,
        "resolved_opt_feedback_by_num": resolved_opt_feedback_by_num,
        "has_active_page_actions": (has_active_highres_jobs or has_active_stitch_jobs),
    }
