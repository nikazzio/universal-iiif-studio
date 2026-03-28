"""Studio route handlers moved out of the routes registration module.

This module contains the logic-heavy request handlers and helpers.
"""

import json
import math
import time
from contextlib import suppress
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

from fasthtml.common import H2, A, Div, P, Request, Script, Span
from starlette.responses import Response

from studio_ui.common.htmx import history_refresh_script
from studio_ui.common.page_inventory import resolve_page_inventory
from studio_ui.common.title_utils import resolve_preferred_title, truncate_title
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
    render_studio_export_tab,
)
from studio_ui.components.studio.history import history_tab_content
from studio_ui.components.studio.tabs import render_studio_tabs
from studio_ui.components.studio.transcription import transcription_tab_content
from studio_ui.config import get_api_key, get_snippets_dir
from studio_ui.ocr_state import OCR_JOBS_STATE, get_ocr_job_state, is_ocr_job_running
from studio_ui.pages.studio import studio_layout
from studio_ui.routes import export_handlers as export_monitor_handlers
from studio_ui.routes.discovery_helpers import start_downloader_thread
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.http_client import get_http_client
from universal_iiif_core.iiif_logic import total_canvases as manifest_total_canvases
from universal_iiif_core.iiif_resolution import probe_remote_max_dimensions
from universal_iiif_core.jobs import job_manager
from universal_iiif_core.logger import get_logger
from universal_iiif_core.pdf_profiles import (
    list_profiles,
    resolve_effective_profile,
)
from universal_iiif_core.services.export import list_item_pdf_files
from universal_iiif_core.services.export.service import parse_page_selection
from universal_iiif_core.services.ocr.processor import OCRProcessor
from universal_iiif_core.services.ocr.storage import OCRStorage
from universal_iiif_core.services.scan_optimize import optimize_local_scans, summarize_scan_folder
from universal_iiif_core.services.storage.vault_manager import VaultManager
from universal_iiif_core.thumbnail_utils import ensure_thumbnail, guess_available_pages
from universal_iiif_core.utils import load_json, save_json

logger = get_logger(__name__)
_STUDIO_ALLOWED_TABS = ("transcription", "snippets", "history", "visual", "info", "images", "output", "jobs")


def _with_toast(fragment, message: str, tone: str = "info"):
    """Append a global toast to a standard fragment response."""
    return [fragment, build_toast(message, tone=tone)]


def _toast_only(message: str, tone: str = "info"):
    """Return a noop target payload plus a global toast for HTMX requests."""
    return _with_toast(Div("", cls="hidden"), message, tone=tone)


def _manifest_canvas_items(manifest_json: dict) -> list[dict]:
    if "sequences" in manifest_json:
        return (manifest_json.get("sequences") or [{}])[0].get("canvases", [])
    return manifest_json.get("items", [])


def _resolve_initial_canvas(manifest_json: dict, page: int) -> str | None:
    items = _manifest_canvas_items(manifest_json)
    target_idx = int(page) - 1
    if 0 <= target_idx < len(items):
        return items[target_idx].get("@id") or items[target_idx].get("id")
    return None


def _load_manifest_payload(manifest_path: Path, page: int) -> tuple[dict, str | None]:
    """Load manifest JSON from disk and resolve initial canvas."""
    with manifest_path.open(encoding="utf-8") as f:
        manifest_json = json.load(f)
    return manifest_json, _resolve_initial_canvas(manifest_json, page)


def _studio_panel_refresh_script(doc_id: str, library: str, page_idx: int, tab: str = "transcription") -> Script:
    """Trigger a targeted refresh of the right Studio panel."""
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    encoded_tab = quote(_normalize_studio_tab(tab), safe="")
    hx_url = f"/studio/partial/tabs?doc_id={encoded_doc}&library={encoded_lib}&page={page_idx}&tab={encoded_tab}"
    return Script(
        "(function(){"
        "setTimeout(function(){"
        "try{ htmx.ajax('GET', '" + hx_url + "', {target:'#studio-right-panel', swap:'innerHTML'}); }"
        "catch(e){ console.error('refresh-err', e); }"
        "}, 50);"
        "})();"
    )


def _normalized_studio_context(doc_id: str, library: str) -> tuple[str, str]:
    """Normalize doc and library query params from URL-encoded values."""
    return unquote(doc_id) if doc_id else "", unquote(library) if library else ""


def _normalize_studio_tab(raw_tab: str | None) -> str:
    value = str(raw_tab or "").strip().lower()
    if value == "export":
        return "images"
    return value if value in _STUDIO_ALLOWED_TABS else "transcription"


def _safe_positive_int(raw: int | str | None, default: int = 1) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return max(1, int(default))
    return max(1, value)


def _studio_recent_limit() -> int:
    raw = get_config_manager().get_setting("ui.studio_recent_max_items", 8)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 8
    return max(1, min(value, 20))


def _save_studio_context_best_effort(doc_id: str, library: str, page: int, tab: str) -> None:
    try:
        VaultManager().save_studio_context(
            doc_id=doc_id,
            library=library,
            page=int(page),
            tab=_normalize_studio_tab(tab),
            max_recent=_studio_recent_limit(),
        )
    except Exception:
        logger.debug("Studio context persistence skipped for %s/%s", library, doc_id, exc_info=True)


def _studio_open_url(doc_id: str, library: str, page: int, tab: str) -> str:
    return (
        f"/studio?doc_id={quote(doc_id, safe='')}"
        f"&library={quote(library, safe='')}"
        f"&page={int(page)}"
        f"&tab={quote(_normalize_studio_tab(tab), safe='')}"
    )


def _resolve_recent_title(context: dict[str, Any], row: dict[str, Any]) -> str:
    doc_id = str(context.get("doc_id") or "")
    fallback = str(row.get("display_title") or row.get("title") or row.get("catalog_title") or doc_id).strip()
    return resolve_preferred_title(row, fallback_doc_id=doc_id).strip() or fallback or doc_id


def _render_studio_recent_hub(*, request: Request, vault: VaultManager):
    limit = _studio_recent_limit()
    last_context = vault.get_studio_last_context() or {}
    contexts = vault.list_studio_recent_contexts(limit=limit)
    items = []
    for context in contexts:
        doc_id = str(context.get("doc_id") or "").strip()
        library = str(context.get("library") or "").strip()
        if not doc_id or not library:
            continue
        row = vault.get_manuscript(doc_id) or {}
        if row and str(row.get("library") or "").strip() not in {"", library}:
            continue
        title = _resolve_recent_title(context, row)
        page = _safe_positive_int(context.get("page"), 1)
        tab = _normalize_studio_tab(str(context.get("tab") or "transcription"))
        updated_at = str(context.get("updated_at") or "").strip() or "n/d"
        items.append(
            Div(
                Div(
                    Span(title, cls="text-sm font-semibold text-slate-900 dark:text-slate-100"),
                    Span(f"{library} · pagina {page} · tab {tab}", cls="text-xs text-slate-500 dark:text-slate-400"),
                    Span(f"Aggiornato: {updated_at}", cls="text-[11px] text-slate-400 dark:text-slate-500"),
                    cls="flex flex-col gap-1 min-w-0",
                ),
                A(
                    "Apri Studio",
                    href=_studio_open_url(doc_id, library, page, tab),
                    cls="app-btn app-btn-primary text-xs whitespace-nowrap",
                ),
                cls=(
                    "flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between "
                    "border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-3"
                ),
            )
        )

    has_last = bool(last_context.get("doc_id")) and bool(last_context.get("library"))
    last_url = (
        _studio_open_url(
            str(last_context.get("doc_id") or ""),
            str(last_context.get("library") or ""),
            _safe_positive_int(last_context.get("page"), 1),
            _normalize_studio_tab(str(last_context.get("tab") or "transcription")),
        )
        if has_last
        else "/library"
    )
    content = Div(
        Div(
            H2("Riprendi lavoro", cls="text-2xl font-black tracking-tight text-slate-900 dark:text-slate-100"),
            P(
                "Riapri velocemente gli ultimi documenti Studio con pagina e tab persistiti lato server.",
                cls="text-sm text-slate-600 dark:text-slate-400",
            ),
            cls="flex flex-col gap-2",
        ),
        Div(
            A(
                "Riprendi ultimo",
                href=last_url,
                cls="app-btn app-btn-primary",
            ),
            A("Apri Libreria", href="/library", cls="app-btn app-btn-secondary"),
            cls="flex flex-wrap gap-2",
        ),
        (
            Div(*items, cls="grid grid-cols-1 gap-3")
            if items
            else Div(
                P("Nessun contesto recente disponibile.", cls="text-sm text-slate-500 dark:text-slate-400"),
                A("Vai in Libreria", href="/library", cls="app-btn app-btn-secondary w-fit"),
                cls=(
                    "rounded-lg border border-dashed border-slate-300 dark:border-slate-600 "
                    "bg-white dark:bg-slate-900/50 p-4 flex flex-col gap-2"
                ),
            )
        ),
        cls="p-6 flex flex-col gap-4",
    )
    if request.headers.get("HX-Request") == "true":
        return content
    return base_layout("Studio", content, active_page="studio")


def _resolve_studio_title(doc_id: str, meta: dict, ms_row: dict) -> tuple[str, str]:
    """Return `(full_title, truncated_title)` for Studio header/info usage."""
    fallback_title = str(meta.get("title") or meta.get("label") or doc_id).strip()
    full_title = resolve_preferred_title(ms_row, fallback_doc_id=doc_id).strip()
    if not full_title or full_title == doc_id:
        full_title = fallback_title or doc_id
    return full_title, truncate_title(full_title, max_len=70, suffix="[...]")


def _manifest_total_pages(manifest_json: dict, ms_row: dict | None = None) -> int:
    """Resolve expected page count from manifest with DB fallback."""
    with suppress(Exception):
        total = int(manifest_total_canvases(manifest_json or {}))
        if total > 0:
            return total
    fallback = int((ms_row or {}).get("total_canvases") or 0)
    return max(fallback, 0)


def _to_downloads_url(path: Path) -> str:
    downloads_dir = get_config_manager().get_downloads_dir().resolve()
    try:
        rel = path.resolve().relative_to(downloads_dir)
    except Exception:
        return ""
    encoded = "/".join(quote(part, safe="") for part in rel.parts)
    return f"/downloads/{encoded}"


def _export_tab_defaults(doc_id: str, library: str) -> dict[str, Any]:
    cm = get_config_manager()
    cover = cm.get_setting("pdf.cover", {})
    export_cfg = cm.get_setting("pdf.export", {})
    profile_name, profile = resolve_effective_profile(cm)
    profiles_catalog = list_profiles(cm)

    if not isinstance(cover, dict):
        cover = {}
    if not isinstance(export_cfg, dict):
        export_cfg = {}

    return {
        "curator": str(cover.get("curator") or ""),
        "description": str(cover.get("description") or ""),
        "logo_path": str(cover.get("logo_path") or ""),
        "format": str(export_cfg.get("default_format") or "pdf_images"),
        "compression": str(profile.get("compression") or export_cfg.get("default_compression") or "Standard"),
        "include_cover": bool(profile.get("include_cover", export_cfg.get("include_cover", True))),
        "include_colophon": bool(profile.get("include_colophon", export_cfg.get("include_colophon", True))),
        "description_rows": int(export_cfg.get("description_rows", 3) or 3),
        "profile_name": profile_name,
        "profile_catalog": profiles_catalog,
        "image_source_mode": str(profile.get("image_source_mode") or "local_balanced"),
        "image_max_long_edge_px": int(profile.get("image_max_long_edge_px") or 0),
        "jpeg_quality": int(profile.get("jpeg_quality") or 82),
        "force_remote_refetch": bool(profile.get("force_remote_refetch", False)),
        "cleanup_temp_after_export": bool(profile.get("cleanup_temp_after_export", True)),
        "max_parallel_page_fetch": int(profile.get("max_parallel_page_fetch") or 2),
    }


def _thumb_page_size(raw_page_size: int | None = None, *, doc_id: str = "") -> int:
    cm = get_config_manager()
    default_size = int(cm.get_setting("thumbnails.page_size", 48) or 48)
    max_size = int(cm.get_setting("thumbnails.studio_page_size_max", 72) or 72)
    max_size = max(12, min(max_size, 120))
    candidate = default_size
    if raw_page_size not in {None, 0}:
        candidate = int(raw_page_size)
    elif doc_id:
        try:
            saved = VaultManager().get_manuscript_ui_pref(doc_id, "studio_export_thumb_page_size", default_size)
            candidate = int(saved or default_size)
        except Exception:
            candidate = default_size
    return max(1, min(candidate, max_size))


def _is_export_job_active(job: dict) -> bool:
    return str(job.get("status") or "").lower() in {"queued", "running"}


def _thumb_page_size_options() -> list[int]:
    cm = get_config_manager()
    raw_options = cm.get_setting("thumbnails.page_size_options", [24, 48, 72, 96])
    max_size = int(cm.get_setting("thumbnails.studio_page_size_max", 72) or 72)
    max_size = max(12, min(max_size, 120))
    options: list[int] = []
    if isinstance(raw_options, list):
        for raw in raw_options:
            try:
                value = int(raw)
            except (TypeError, ValueError):
                continue
            if 1 <= value <= max_size and value not in options:
                options.append(value)
    default_size = _thumb_page_size()
    if default_size not in options:
        options.append(default_size)
    return sorted(options)


def _prune_stale_thumbnails(thumbnails_dir: Path, retention_days: int) -> None:
    cutoff = time.time() - (max(1, int(retention_days or 1)) * 86400)
    if not thumbnails_dir.exists():
        return
    for thumb in thumbnails_dir.glob("*.jpg"):
        with suppress(OSError):
            if thumb.stat().st_mtime < cutoff:
                thumb.unlink()


def _remote_cache_limits(cm) -> tuple[int, int, int]:
    max_bytes = int(cm.get_setting("storage.remote_cache.max_bytes", 104857600) or 104857600)
    retention_hours = int(cm.get_setting("storage.remote_cache.retention_hours", 72) or 72)
    max_items = int(cm.get_setting("storage.remote_cache.max_items", 2000) or 2000)
    return (
        max(1024 * 1024, min(max_bytes, 20 * 1024**3)),
        max(1, min(retention_hours, 24 * 365)),
        max(100, min(max_items, 100000)),
    )


def _cache_payload_size(cache: dict[str, dict]) -> int:
    return len(json.dumps(cache, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _normalize_remote_cache(raw_cache: object) -> dict[str, dict]:
    if not isinstance(raw_cache, dict):
        return {}
    normalized: dict[str, dict] = {}
    now_ts = int(time.time())
    for key, value in raw_cache.items():
        if not isinstance(value, dict):
            continue
        page_key = str(key).strip()
        if not page_key:
            continue
        entry = {
            "width": value.get("width"),
            "height": value.get("height"),
            "service_url": value.get("service_url"),
            "verified_direct_width": value.get("verified_direct_width"),
            "verified_direct_height": value.get("verified_direct_height"),
            "verified_direct_ts": int(value.get("verified_direct_ts") or value.get("updated_ts") or now_ts),
            "last_access_ts": int(value.get("last_access_ts") or value.get("updated_ts") or now_ts),
            "updated_ts": int(value.get("updated_ts") or value.get("last_access_ts") or now_ts),
        }
        normalized[page_key] = entry
    return normalized


def _prune_remote_cache(
    cache: dict[str, dict],
    *,
    max_bytes: int,
    retention_hours: int,
    max_items: int,
) -> dict[str, dict]:
    now_ts = int(time.time())
    min_ts = now_ts - (int(retention_hours) * 3600)

    kept = {
        key: value
        for key, value in cache.items()
        if int(value.get("last_access_ts") or value.get("updated_ts") or 0) >= min_ts
    }
    if len(kept) > max_items:
        ordered = sorted(
            kept.items(),
            key=lambda item: int(item[1].get("last_access_ts") or item[1].get("updated_ts") or 0),
            reverse=True,
        )
        kept = dict(ordered[:max_items])

    if _cache_payload_size(kept) <= max_bytes:
        return kept

    ordered_oldest = sorted(
        kept.items(),
        key=lambda item: int(item[1].get("last_access_ts") or item[1].get("updated_ts") or 0),
    )
    for page_key, _entry in ordered_oldest:
        kept.pop(page_key, None)
        if _cache_payload_size(kept) <= max_bytes:
            break
    return kept


def _load_last_optimization_meta(doc_id: str) -> dict[str, Any]:
    row = VaultManager().get_manuscript(doc_id) or {}
    raw = str(row.get("local_optimization_meta_json") or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _page_delta_map(meta: dict[str, Any]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for item in meta.get("page_deltas") or []:
        if not isinstance(item, dict):
            continue
        try:
            page = int(item.get("page") or 0)
        except (TypeError, ValueError):
            continue
        if page <= 0:
            continue
        out[page] = item
    return out


_STUDIO_EXPORT_HIGHRES_PREF_KEY = "studio_export_highres_jobs"
_STUDIO_EXPORT_STITCH_PREF_KEY = "studio_export_stitch_jobs"
_STUDIO_EXPORT_PAGE_SOURCE_PREF_KEY = "studio_export_page_sources"
_ACTIVE_DOWNLOAD_STATES = {"queued", "running", "cancelling", "pausing"}


def _normalize_page_job_pref(raw_pref: Any) -> dict[int, dict[str, Any]]:
    if not isinstance(raw_pref, dict):
        return {}
    normalized: dict[int, dict[str, Any]] = {}
    for raw_page, payload in raw_pref.items():
        try:
            page_num = int(raw_page)
        except (TypeError, ValueError):
            continue
        if page_num <= 0:
            continue
        if isinstance(payload, dict):
            job_id = str(payload.get("job_id") or "").strip()
            state = str(payload.get("state") or "").strip().lower()
            source_ts = str(payload.get("source_ts") or "").strip()
        else:
            job_id = str(payload or "").strip()
            state = ""
            source_ts = ""
        if not job_id:
            continue
        normalized[page_num] = {"job_id": job_id, "state": state, "source_ts": source_ts}
    return normalized


def _load_page_job_pref(doc_id: str, pref_key: str) -> dict[int, dict[str, Any]]:
    raw_pref = VaultManager().get_manuscript_ui_pref(doc_id, pref_key, {})
    return _normalize_page_job_pref(raw_pref)


def _save_page_job_pref(doc_id: str, pref_key: str, page_jobs: dict[int, dict[str, Any]]) -> None:
    payload = {
        str(int(page)): {
            "job_id": str((entry or {}).get("job_id") or ""),
            "state": str((entry or {}).get("state") or ""),
            "source_ts": str((entry or {}).get("source_ts") or ""),
        }
        for page, entry in page_jobs.items()
        if int(page) > 0 and str((entry or {}).get("job_id") or "").strip()
    }
    VaultManager().set_manuscript_ui_pref(doc_id, pref_key, payload)


def _load_highres_pref(doc_id: str) -> dict[int, dict[str, Any]]:
    return _load_page_job_pref(doc_id, _STUDIO_EXPORT_HIGHRES_PREF_KEY)


def _save_highres_pref(doc_id: str, page_jobs: dict[int, dict[str, Any]]) -> None:
    _save_page_job_pref(doc_id, _STUDIO_EXPORT_HIGHRES_PREF_KEY, page_jobs)


def _load_stitch_pref(doc_id: str) -> dict[int, dict[str, Any]]:
    return _load_page_job_pref(doc_id, _STUDIO_EXPORT_STITCH_PREF_KEY)


def _save_stitch_pref(doc_id: str, page_jobs: dict[int, dict[str, Any]]) -> None:
    _save_page_job_pref(doc_id, _STUDIO_EXPORT_STITCH_PREF_KEY, page_jobs)


def _normalize_page_source_pref(raw_pref: Any) -> dict[int, dict[str, str]]:
    if not isinstance(raw_pref, dict):
        return {}
    normalized: dict[int, dict[str, str]] = {}
    for raw_page, payload in raw_pref.items():
        try:
            page_num = int(raw_page)
        except (TypeError, ValueError):
            continue
        if page_num <= 0 or not isinstance(payload, dict):
            continue
        source = str(payload.get("source") or "").strip().lower()
        source_ts = str(payload.get("source_ts") or "").strip()
        if source not in {"highres", "optimized", "stitched"}:
            continue
        normalized[page_num] = {"source": source, "source_ts": source_ts}
    return normalized


def _load_page_source_pref(doc_id: str) -> dict[int, dict[str, str]]:
    raw_pref = VaultManager().get_manuscript_ui_pref(doc_id, _STUDIO_EXPORT_PAGE_SOURCE_PREF_KEY, {})
    return _normalize_page_source_pref(raw_pref)


def _save_page_source_pref(doc_id: str, page_source_map: dict[int, dict[str, str]]) -> None:
    payload = {
        str(int(page)): {
            "source": str((entry or {}).get("source") or ""),
            "source_ts": str((entry or {}).get("source_ts") or ""),
        }
        for page, entry in page_source_map.items()
        if int(page) > 0 and str((entry or {}).get("source") or "").strip() in {"highres", "optimized", "stitched"}
    }
    VaultManager().set_manuscript_ui_pref(doc_id, _STUDIO_EXPORT_PAGE_SOURCE_PREF_KEY, payload)


def _merge_page_source_pref(
    existing: dict[int, dict[str, str]],
    updates: dict[int, dict[str, str]],
) -> dict[int, dict[str, str]]:
    merged = {int(page): dict(payload or {}) for page, payload in (existing or {}).items() if int(page) > 0}
    for raw_page, payload in (updates or {}).items():
        try:
            page = int(raw_page)
        except (TypeError, ValueError):
            continue
        if page <= 0:
            continue
        source = str((payload or {}).get("source") or "").strip().lower()
        source_ts = str((payload or {}).get("source_ts") or "").strip()
        if source not in {"highres", "optimized", "stitched"}:
            continue
        merged[page] = {"source": source, "source_ts": source_ts}
    return merged


def _normalize_feedback_map(raw_map: dict[int, dict[str, str]] | None) -> dict[int, dict[str, str]]:
    normalized: dict[int, dict[str, str]] = {}
    for raw_page, payload in (raw_map or {}).items():
        try:
            page = int(raw_page)
        except (TypeError, ValueError):
            continue
        if page <= 0:
            continue
        normalized[page] = dict(payload or {})
    return normalized


def _set_idle_feedback(feedback: dict[str, str], *, label: str, tone: str = "info") -> dict[str, str]:
    feedback["state"] = "idle"
    feedback["progress_percent"] = "0"
    feedback["tone"] = tone
    feedback["label"] = label
    return feedback


def _force_done_feedback(feedback: dict[str, str], *, label: str) -> dict[str, str]:
    out = dict(feedback or {})
    out["state"] = "done"
    out["progress_percent"] = "100"
    out["tone"] = str(out.get("tone") or "success")
    out["label"] = label
    return out


def _apply_single_preferred_source(
    *,
    preferred_source: str,
    preferred_feedback: dict[str, str],
    preferred_label: str,
    other_feedbacks: list[tuple[dict[str, str], str]],
) -> tuple[dict[str, str], list[dict[str, str]]]:
    preferred_state = str(preferred_feedback.get("state") or "").strip().lower()
    if preferred_state not in {"queued", "running"}:
        preferred_feedback = _force_done_feedback(preferred_feedback, label=preferred_label)
    updated_others: list[dict[str, str]] = []
    for payload, label in other_feedbacks:
        if str(payload.get("state") or "").strip().lower() == "done":
            payload = _set_idle_feedback(payload, label=label)
        updated_others.append(payload)
    return preferred_feedback, updated_others


def _apply_preferred_source_to_feedback(
    *,
    highres_feedback: dict[str, str],
    stitch_feedback: dict[str, str],
    optimize_feedback: dict[str, str],
    preferred_source: str,
) -> tuple[dict[str, str], dict[str, str], dict[str, str], bool]:
    if preferred_source == "highres":
        highres_feedback, others = _apply_single_preferred_source(
            preferred_source=preferred_source,
            preferred_feedback=highres_feedback,
            preferred_label="High-Res",
            other_feedbacks=[(stitch_feedback, "Strategia standard"), (optimize_feedback, "Ottimizza")],
        )
        stitch_feedback, optimize_feedback = others
        return highres_feedback, stitch_feedback, optimize_feedback, True
    if preferred_source == "stitched":
        stitch_feedback, others = _apply_single_preferred_source(
            preferred_source=preferred_source,
            preferred_feedback=stitch_feedback,
            preferred_label="Strategia standard",
            other_feedbacks=[(highres_feedback, "High-Res"), (optimize_feedback, "Ottimizza")],
        )
        highres_feedback, optimize_feedback = others
        return highres_feedback, stitch_feedback, optimize_feedback, True
    if preferred_source == "optimized":
        optimize_feedback, others = _apply_single_preferred_source(
            preferred_source=preferred_source,
            preferred_feedback=optimize_feedback,
            preferred_label="Ottimizzata",
            other_feedbacks=[(highres_feedback, "High-Res"), (stitch_feedback, "Strategia standard")],
        )
        highres_feedback, stitch_feedback = others
        return highres_feedback, stitch_feedback, optimize_feedback, True
    return highres_feedback, stitch_feedback, optimize_feedback, False


def _should_mark_highres_source_update(prev_state: str, current_state: str) -> bool:
    prev = str(prev_state or "").strip().lower()
    now = str(current_state or "").strip().lower()
    if prev == "completed":
        prev = "done"
    return now == "done" and prev != "done"


def _download_feedback_row(
    *,
    status: str,
    current: int,
    total: int,
    source_ts: str = "",
    idle_label: str,
    queued_label: str,
    running_label: str,
    done_label: str,
    error_label: str,
    interrupted_label: str,
) -> dict[str, str]:
    status_key = str(status or "").strip().lower()
    source_value = str(source_ts or "").strip()
    percent = 0
    if total > 0:
        percent = int(max(0, min(100, (max(0, int(current)) / max(1, int(total))) * 100)))
    if status_key == "queued":
        return {"state": "queued", "tone": "info", "label": queued_label, "progress_percent": "0"}
    if status_key in {"running", "cancelling", "pausing"}:
        return {
            "state": "running",
            "tone": "warning",
            "label": running_label,
            "progress_percent": str(percent),
        }
    if status_key == "completed":
        return {
            "state": "done",
            "tone": "success",
            "label": done_label,
            "progress_percent": "100",
            "source_ts": source_value,
        }
    if status_key in {"error", "failed"}:
        return {
            "state": "error",
            "tone": "danger",
            "label": error_label,
            "progress_percent": "100",
            "source_ts": source_value,
        }
    if status_key in {"cancelled", "paused"}:
        return {
            "state": "error",
            "tone": "warning",
            "label": interrupted_label,
            "progress_percent": "100",
            "source_ts": source_value,
        }
    return {"state": "idle", "tone": "info", "label": idle_label, "progress_percent": "0"}


def _resolve_page_download_feedback(
    doc_id: str,
    library: str,
    *,
    pref_key: str,
    success_source: str,
    idle_label: str,
    queued_label: str,
    running_label: str,
    done_label: str,
    error_label: str,
    interrupted_label: str,
) -> tuple[dict[int, dict[str, str]], bool]:
    pref = _load_page_job_pref(doc_id, pref_key)
    if not pref:
        return {}, False

    existing_source_pref = _load_page_source_pref(doc_id)
    vm = VaultManager()
    updated_pref: dict[int, dict[str, Any]] = {}
    source_updates: dict[int, dict[str, str]] = {}
    feedback_by_page: dict[int, dict[str, str]] = {}
    has_active = False

    for page_num, entry in pref.items():
        job_id = str(entry.get("job_id") or "").strip()
        if not job_id:
            continue
        job = vm.get_download_job(job_id) or {}
        job_doc_id = str(job.get("doc_id") or "").strip()
        job_library = str(job.get("library") or "").strip()
        if job and (job_doc_id != doc_id or job_library != library):
            continue

        status = str(job.get("status") or entry.get("state") or "").strip().lower()
        current = int(job.get("current") or 0)
        total = int(job.get("total") or 0)
        source_ts = str(job.get("finished_at") or job.get("updated_at") or entry.get("source_ts") or "").strip()
        feedback = _download_feedback_row(
            status=status,
            current=current,
            total=total,
            source_ts=source_ts,
            idle_label=idle_label,
            queued_label=queued_label,
            running_label=running_label,
            done_label=done_label,
            error_label=error_label,
            interrupted_label=interrupted_label,
        )
        feedback["job_id"] = job_id
        feedback_by_page[page_num] = feedback

        state = str(feedback.get("state") or "").strip().lower()
        if state == "done" and (
            _should_mark_highres_source_update(str(entry.get("state") or ""), state)
            or (page_num not in existing_source_pref and bool(job))
        ):
            source_updates[page_num] = {"source": success_source, "source_ts": str(int(time.time() * 1000))}
        if status in _ACTIVE_DOWNLOAD_STATES or state in {"queued", "running"}:
            has_active = True
            updated_pref[page_num] = {"job_id": job_id, "state": status or state, "source_ts": source_ts}
        else:
            updated_pref[page_num] = {"job_id": job_id, "state": state, "source_ts": source_ts}

    if updated_pref != pref:
        with suppress(Exception):
            _save_page_job_pref(doc_id, pref_key, updated_pref)
    if source_updates:
        with suppress(Exception):
            merged_source_pref = _merge_page_source_pref(existing_source_pref, source_updates)
            if merged_source_pref != existing_source_pref:
                _save_page_source_pref(doc_id, merged_source_pref)
    return feedback_by_page, has_active


def _resolve_highres_page_feedback(doc_id: str, library: str) -> tuple[dict[int, dict[str, str]], bool]:
    return _resolve_page_download_feedback(
        doc_id,
        library,
        pref_key=_STUDIO_EXPORT_HIGHRES_PREF_KEY,
        success_source="highres",
        idle_label="High-Res",
        queued_label="High-Res in coda",
        running_label="High-Res in corso",
        done_label="High-Res completato",
        error_label="Errore High-Res",
        interrupted_label="High-Res interrotto",
    )


def _resolve_stitch_page_feedback(doc_id: str, library: str) -> tuple[dict[int, dict[str, str]], bool]:
    return _resolve_page_download_feedback(
        doc_id,
        library,
        pref_key=_STUDIO_EXPORT_STITCH_PREF_KEY,
        success_source="stitched",
        idle_label="Strategia standard",
        queued_label="Strategia standard in coda",
        running_label="Strategia standard in corso",
        done_label="Strategia standard completata",
        error_label="Errore strategia standard",
        interrupted_label="Strategia standard interrotta",
    )


def _merge_page_feedback(
    base: dict[int, dict[str, str]],
    override: dict[int, dict[str, str]] | None = None,
) -> dict[int, dict[str, str]]:
    merged: dict[int, dict[str, str]] = {}
    for page, payload in (base or {}).items():
        try:
            page_num = int(page)
        except (TypeError, ValueError):
            continue
        if page_num <= 0:
            continue
        merged[page_num] = dict(payload or {})
    for page, payload in (override or {}).items():
        try:
            page_num = int(page)
        except (TypeError, ValueError):
            continue
        if page_num <= 0:
            continue
        next_payload = dict(payload or {})
        if not next_payload:
            continue
        merged[page_num] = {**merged.get(page_num, {}), **next_payload}
    return merged


def _optimize_feedback_from_deltas(
    page_delta_by_num: dict[int, dict[str, Any]],
    *,
    optimized_at: str = "",
) -> dict[int, dict[str, str]]:
    optimize_ts = str(optimized_at or "").strip()
    feedback_by_page: dict[int, dict[str, str]] = {}
    for page_num, payload in (page_delta_by_num or {}).items():
        try:
            page = int(page_num)
        except (TypeError, ValueError):
            continue
        if page <= 0:
            continue
        status = str((payload or {}).get("status") or "").strip().lower()
        if status == "ok":
            feedback_by_page[page] = {
                "state": "done",
                "tone": "success",
                "label": "Ottimizzata",
                "progress_percent": "100",
                "source_ts": optimize_ts,
            }
            continue
        if status == "error":
            feedback_by_page[page] = {
                "state": "error",
                "tone": "danger",
                "label": "Errore ottimizzazione",
                "progress_percent": "100",
                "source_ts": optimize_ts,
            }
    return feedback_by_page


def _resolve_current_image_feedback(
    highres_feedback_by_num: dict[int, dict[str, str]],
    stitch_feedback_by_num: dict[int, dict[str, str]],
    optimize_feedback_by_num: dict[int, dict[str, str]],
    preferred_source_by_page: dict[int, dict[str, str]] | None = None,
) -> tuple[dict[int, dict[str, str]], dict[int, dict[str, str]], dict[int, dict[str, str]]]:
    resolved_highres = _normalize_feedback_map(highres_feedback_by_num)
    resolved_stitch = _normalize_feedback_map(stitch_feedback_by_num)
    resolved_opt = _normalize_feedback_map(optimize_feedback_by_num)
    preferred = _normalize_feedback_map(preferred_source_by_page)
    pages = (
        set(resolved_highres.keys()) | set(resolved_stitch.keys()) | set(resolved_opt.keys()) | set(preferred.keys())
    )
    done_priority = {"highres": 0, "stitched": 1, "optimized": 2}
    labels = {"highres": "High-Res", "stitched": "Strategia standard", "optimized": "Ottimizza"}
    for page in pages:
        hi = resolved_highres.get(page) or {}
        stitch = resolved_stitch.get(page) or {}
        opt = resolved_opt.get(page) or {}
        preferred_source = str((preferred.get(page) or {}).get("source") or "").strip().lower()
        hi, stitch, opt, consumed = _apply_preferred_source_to_feedback(
            highres_feedback=hi,
            stitch_feedback=stitch,
            optimize_feedback=opt,
            preferred_source=preferred_source,
        )
        resolved_highres[page] = hi
        resolved_stitch[page] = stitch
        resolved_opt[page] = opt
        if consumed:
            continue
        all_feedback = {
            "highres": hi,
            "stitched": stitch,
            "optimized": opt,
        }
        done_sources = [
            source
            for source, payload in all_feedback.items()
            if str(payload.get("state") or "").strip().lower() == "done"
        ]
        if not done_sources:
            continue
        preferred_done = max(
            done_sources,
            key=lambda source: (
                str(all_feedback[source].get("source_ts") or ""),
                -done_priority[source],
            ),
        )
        for source, payload in all_feedback.items():
            if source == preferred_done:
                continue
            if str(payload.get("state") or "").strip().lower() == "done":
                all_feedback[source] = _set_idle_feedback(payload, label=labels[source])
        resolved_highres[page] = all_feedback["highres"]
        resolved_stitch[page] = all_feedback["stitched"]
        resolved_opt[page] = all_feedback["optimized"]

    return resolved_highres, resolved_stitch, resolved_opt


def _persist_optimized_page_source_pref(doc_id: str, meta: dict[str, Any]) -> None:
    optimize_ts = str(int(time.time() * 1000))
    optimized_source_updates: dict[int, dict[str, str]] = {}
    for delta in meta.get("page_deltas") or []:
        if not isinstance(delta, dict):
            continue
        try:
            page_num = int(delta.get("page") or 0)
        except (TypeError, ValueError):
            continue
        if page_num <= 0:
            continue
        if str(delta.get("status") or "").strip().lower() != "ok":
            continue
        optimized_source_updates[page_num] = {"source": "optimized", "source_ts": optimize_ts}
    if not optimized_source_updates:
        return
    with suppress(Exception):
        existing_source_pref = _load_page_source_pref(doc_id)
        merged_source_pref = _merge_page_source_pref(existing_source_pref, optimized_source_updates)
        if merged_source_pref != existing_source_pref:
            _save_page_source_pref(doc_id, merged_source_pref)


def _local_scan_info(scan_path: Path) -> tuple[int | None, int | None, int]:
    local_w = None
    local_h = None
    local_bytes = 0
    if scan_path.exists():
        with suppress(Exception):
            from PIL import Image

            with Image.open(scan_path) as img:
                local_w, local_h = img.size
        with suppress(Exception):
            local_bytes = int(scan_path.stat().st_size)
    return local_w, local_h, local_bytes


def _resolve_remote_dims(
    *,
    page_num: int,
    manifest_json: dict,
    remote_cache: dict[str, dict],
    remote_probe_enabled: bool,
    force_refresh: bool = False,
) -> tuple[int | None, int | None, str | None]:
    page_key = str(page_num)
    remote_entry = remote_cache.get(page_key) or {}
    remote_w = remote_entry.get("width")
    remote_h = remote_entry.get("height")
    remote_service = remote_entry.get("service_url")
    if remote_probe_enabled and (force_refresh or not remote_w or not remote_h):
        pw, ph, service_url = probe_remote_max_dimensions(manifest_json, page_num)
        remote_w, remote_h = pw, ph
        remote_service = service_url or remote_service
        remote_cache[page_key] = {
            "width": remote_w,
            "height": remote_h,
            "service_url": remote_service,
            "updated_ts": int(time.time()),
            "last_access_ts": int(time.time()),
        }
    elif remote_entry:
        remote_entry["last_access_ts"] = int(time.time())
        remote_cache[page_key] = remote_entry
    return remote_w, remote_h, remote_service


def _normalize_download_method(raw_method: Any, original_url: Any = "") -> str:
    method = str(raw_method or "").strip().lower()
    if method in {"direct", "tile_stitch", "cached"}:
        return method
    original_text = str(original_url or "").strip().lower()
    if "tile-stitch" in original_text:
        return "tile_stitch"
    if "(cached)" in original_text:
        return "cached"
    if original_text:
        return "direct"
    return ""


def _stats_download_method_map(stats_payload: dict[str, Any]) -> dict[int, str]:
    methods: dict[int, str] = {}
    for entry in stats_payload.get("pages") or []:
        if not isinstance(entry, dict):
            continue
        try:
            page_num = int(entry.get("page_index", -1)) + 1
        except (TypeError, ValueError):
            continue
        if page_num <= 0:
            continue
        method = _normalize_download_method(entry.get("download_method"), entry.get("original_url"))
        if method:
            methods[page_num] = method
    return methods


def _stats_page_meta_map(stats_payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    items: dict[int, dict[str, Any]] = {}
    for entry in stats_payload.get("pages") or []:
        if not isinstance(entry, dict):
            continue
        try:
            page_num = int(entry.get("page_index", -1)) + 1
        except (TypeError, ValueError):
            continue
        if page_num > 0:
            items[page_num] = entry
    return items


def _verified_direct_dims(
    *,
    page_num: int,
    stats_by_num: dict[int, dict[str, Any]],
    remote_cache: dict[str, dict],
) -> tuple[int | None, int | None]:
    stats_entry = stats_by_num.get(page_num) or {}
    method = _normalize_download_method(stats_entry.get("download_method"), stats_entry.get("original_url"))
    if method in {"direct", "cached"}:
        try:
            width = int(stats_entry.get("width") or 0)
        except (TypeError, ValueError):
            width = 0
        try:
            height = int(stats_entry.get("height") or 0)
        except (TypeError, ValueError):
            height = 0
        if width > 0 and height > 0:
            remote_cache.setdefault(str(page_num), {}).update(
                {
                    "verified_direct_width": width,
                    "verified_direct_height": height,
                    "verified_direct_ts": int(time.time()),
                }
            )
            return width, height

    cache_entry = remote_cache.get(str(page_num)) or {}
    try:
        cached_width = int(cache_entry.get("verified_direct_width") or 0)
    except (TypeError, ValueError):
        cached_width = 0
    try:
        cached_height = int(cache_entry.get("verified_direct_height") or 0)
    except (TypeError, ValueError):
        cached_height = 0
    return (cached_width or None), (cached_height or None)


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


def build_studio_tab_content(
    doc_id: str,
    library: str,
    page_idx: int,
    *,
    active_tab: str = "transcription",
    is_ocr_loading: bool = False,
    ocr_error: str | None = None,
    history_message: str | None = None,
):
    """Build Studio Tab Content."""
    storage = OCRStorage()
    meta = storage.load_metadata(doc_id, library) or {}
    ms_row = VaultManager().get_manuscript(doc_id) or {}
    full_title, _truncated_title = _resolve_studio_title(doc_id, meta, ms_row)
    paths = storage.get_document_paths(doc_id, library)
    scans_dir = Path(paths["scans"])
    manifest_json = load_json(paths["manifest"]) or {}
    inventory = resolve_page_inventory(doc_id=doc_id, scans_dir=scans_dir)
    manifest_pages = _manifest_total_pages(manifest_json, ms_row)
    total_pages = int(inventory.local_pages_count)
    meta = {
        **meta,
        "full_display_title": full_title,
        "local_pages_count": int(inventory.local_pages_count),
        "temp_pages_count": int(inventory.temp_pages_count),
        "manifest_total_pages": manifest_pages,
    }
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    safe_tab = _normalize_studio_tab(active_tab)
    export_url = (
        f"/studio/partial/export?doc_id={encoded_doc}&library={encoded_lib}"
        f"&page={page_idx}&tab={quote(safe_tab, safe='')}"
    )
    return render_studio_tabs(
        doc_id,
        library,
        page_idx,
        meta,
        total_pages,
        manifest_json=manifest_json,
        active_tab=safe_tab,
        is_ocr_loading=is_ocr_loading,
        ocr_error=ocr_error,
        history_message=history_message,
        export_fragment=None,
        export_url=export_url,
    )


def _saved_source_policy() -> str:
    policy = str(get_config_manager().get_setting("viewer.source_policy.saved_mode", "remote_first") or "").strip()
    return policy if policy in {"remote_first", "local_first"} else "remote_first"


def _resolve_studio_read_source_mode(
    *,
    ms_row: dict,
    local_pages_count: int,
    manifest_pages: int,
    require_complete_local: bool,
    allow_remote_preview: bool,
) -> tuple[str, bool]:
    if allow_remote_preview:
        return "remote", False

    policy = _saved_source_policy()
    status = str(ms_row.get("asset_state") or ms_row.get("status") or "").strip().lower()
    is_saved_state = status in {"", "saved"}
    is_local_complete = manifest_pages > 0 and local_pages_count >= manifest_pages

    if is_saved_state and policy == "remote_first":
        return "remote", False
    if require_complete_local and manifest_pages > 0 and not is_local_complete:
        return "local", True
    if local_pages_count > 0 and (policy == "local_first" or is_local_complete):
        return "local", False
    return "remote", False


def _load_studio_manifest_context(
    *,
    manifest_path: Path,
    remote_manifest_url: str,
    page: int,
) -> tuple[dict, str | None, bool]:
    manifest_exists_local = manifest_path.exists()
    if manifest_exists_local:
        manifest_json, initial_canvas = _load_manifest_payload(manifest_path, page)
        return manifest_json, initial_canvas, True

    if remote_manifest_url:
        remote_manifest = get_http_client().get_json(remote_manifest_url, retries=2) or {}
        if isinstance(remote_manifest, dict) and remote_manifest:
            return remote_manifest, _resolve_initial_canvas(remote_manifest, page), False

    return {}, None, False


def _select_studio_manifest_url(
    *,
    read_source_mode: str,
    local_manifest_url: str,
    remote_manifest_url: str,
) -> str:
    if read_source_mode == "remote" and remote_manifest_url:
        return remote_manifest_url
    return local_manifest_url


def _resolve_manifest_for_selected_source(
    *,
    read_source_mode: str,
    page: int,
    manifest_path: Path,
    local_manifest_url: str,
    remote_manifest_url: str,
    fallback_manifest: dict,
    fallback_canvas: str | None,
) -> tuple[dict, str | None, bool, str, str]:
    manifest_exists_local = manifest_path.exists()
    if read_source_mode == "remote" and remote_manifest_url:
        remote_manifest = get_http_client().get_json(remote_manifest_url, retries=2) or {}
        if isinstance(remote_manifest, dict) and remote_manifest:
            return (
                remote_manifest,
                _resolve_initial_canvas(remote_manifest, page),
                manifest_exists_local,
                remote_manifest_url,
                "remote",
            )
        if manifest_exists_local:
            local_manifest, local_canvas = _load_manifest_payload(manifest_path, page)
            if local_manifest:
                return local_manifest, local_canvas, True, local_manifest_url, "local"

    if read_source_mode == "local" and manifest_exists_local:
        local_manifest, local_canvas = _load_manifest_payload(manifest_path, page)
        if local_manifest:
            return local_manifest, local_canvas, True, local_manifest_url, "local"

    fallback_source_mode = "local" if manifest_exists_local else "remote"
    fallback_manifest_url = (
        local_manifest_url if fallback_source_mode == "local" else (remote_manifest_url or local_manifest_url)
    )
    return fallback_manifest, fallback_canvas, manifest_exists_local, fallback_manifest_url, fallback_source_mode


def _persist_studio_source_state(
    *,
    doc_id: str,
    read_source_mode: str,
    local_pages_count: int,
    manifest_exists_local: bool,
) -> None:
    with suppress(Exception):
        VaultManager().upsert_manuscript(
            doc_id,
            read_source_mode=read_source_mode,
            local_scans_available=1 if local_pages_count > 0 else 0,
            manifest_local_available=1 if manifest_exists_local else 0,
        )


def _manifest_missing_response(is_hx: bool):
    message = "Manifesto non trovato."
    panel = Div(message, cls="p-10")
    if is_hx:
        return _with_toast(panel, message, tone="danger")
    return panel


def _build_source_notice(*, read_source_mode: str, degraded_remote_manifest: bool) -> tuple[str, str]:
    mode = str(read_source_mode or "").strip().lower()
    if mode != "remote":
        return "", "info"
    if degraded_remote_manifest:
        return (
            "Stai leggendo la versione online del documento. Il manifest remoto non è disponibile lato server in "
            "questo momento, quindi alcuni metadati e contatori potrebbero essere incompleti.",
            "warning",
        )
    return ("Stai leggendo la versione online/remota del documento.", "info")


def _build_workspace_base_context(
    request: Request,
    doc_id: str,
    library: str,
    vault: VaultManager,
) -> dict[str, Any] | None:
    storage = OCRStorage()
    paths = storage.get_document_paths(doc_id, library)
    meta = storage.load_metadata(doc_id, library) or {}
    ms_row = vault.get_manuscript(doc_id) or {}
    if ms_row and str(ms_row.get("library") or "").strip() not in {"", library}:
        return None
    full_title, title = _resolve_studio_title(doc_id, meta, ms_row)
    scans_dir = Path(paths["scans"])
    inventory = resolve_page_inventory(doc_id=doc_id, scans_dir=scans_dir)
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    lib_q = quote(library, safe="")
    doc_q = quote(doc_id, safe="")
    return {
        "doc_id": doc_id,
        "library": library,
        "paths": paths,
        "meta": meta,
        "ms_row": ms_row,
        "full_title": full_title,
        "title": title,
        "inventory": inventory,
        "total_pages": int(inventory.local_pages_count),
        "local_manifest_url": f"{base_url}/iiif/manifest/{lib_q}/{doc_q}",
        "remote_manifest_url": str(ms_row.get("manifest_url") or "").strip(),
        "lib_q": lib_q,
        "doc_q": doc_q,
    }


def _resolve_workspace_manifest_context(
    *,
    request: Request,
    workspace: dict[str, Any],
    requested_page: int,
    active_tab: str,
) -> dict[str, Any] | None:
    ms_row = workspace["ms_row"]
    inventory = workspace["inventory"]
    manifest_path = Path(workspace["paths"]["manifest"])
    remote_manifest_url = workspace["remote_manifest_url"]
    manifest_json, initial_canvas, manifest_exists_local = _load_studio_manifest_context(
        manifest_path=manifest_path,
        remote_manifest_url=remote_manifest_url,
        page=requested_page,
    )
    resolved_manifest_pages = _manifest_total_pages(manifest_json or {}, ms_row)
    require_complete_local = bool(
        get_config_manager().get_setting("viewer.mirador.require_complete_local_images", True)
    )
    allow_remote_preview = str(request.query_params.get("allow_remote_preview") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    read_source_mode, should_gate_mirador = _resolve_studio_read_source_mode(
        ms_row=ms_row,
        local_pages_count=int(inventory.local_pages_count),
        manifest_pages=int(resolved_manifest_pages),
        require_complete_local=require_complete_local,
        allow_remote_preview=allow_remote_preview,
    )
    if read_source_mode == "local" and not manifest_exists_local and remote_manifest_url:
        read_source_mode = "remote"
        should_gate_mirador = False
    manifest_json, initial_canvas, manifest_exists_local, manifest_url, resolved_read_source_mode = (
        _resolve_manifest_for_selected_source(
            read_source_mode=read_source_mode,
            page=requested_page,
            manifest_path=manifest_path,
            local_manifest_url=workspace["local_manifest_url"],
            remote_manifest_url=remote_manifest_url,
            fallback_manifest=manifest_json,
            fallback_canvas=initial_canvas,
        )
    )
    degraded_remote_manifest = False
    if not manifest_json:
        if resolved_read_source_mode != "remote" or not remote_manifest_url:
            return None
        degraded_remote_manifest = True
    manifest_pages = _manifest_total_pages(manifest_json, ms_row)
    safe_page = requested_page if manifest_pages <= 0 else max(1, min(requested_page, manifest_pages))
    if manifest_json:
        initial_canvas = _resolve_initial_canvas(manifest_json, safe_page)
    source_notice_text, source_notice_tone = _build_source_notice(
        read_source_mode=resolved_read_source_mode,
        degraded_remote_manifest=degraded_remote_manifest,
    )
    meta = {
        **workspace["meta"],
        "full_display_title": workspace["full_title"],
        "local_pages_count": int(inventory.local_pages_count),
        "temp_pages_count": int(inventory.temp_pages_count),
        "manifest_total_pages": manifest_pages,
    }
    mirador_override_url = (
        (
            f"/studio?doc_id={workspace['doc_q']}&library={workspace['lib_q']}&page={int(safe_page)}"
            f"&tab={quote(active_tab, safe='')}&allow_remote_preview=1"
        )
        if should_gate_mirador
        else ""
    )
    _persist_studio_source_state(
        doc_id=str(workspace["doc_id"]),
        read_source_mode=resolved_read_source_mode,
        local_pages_count=int(inventory.local_pages_count),
        manifest_exists_local=manifest_exists_local,
    )
    return {
        "manifest_url": manifest_url,
        "manifest_json": manifest_json,
        "initial_canvas": initial_canvas,
        "mirador_initial_page": int(safe_page) if not initial_canvas and safe_page > 1 else None,
        "manifest_pages": int(manifest_pages),
        "safe_page": int(safe_page),
        "read_source_mode": resolved_read_source_mode,
        "should_gate_mirador": should_gate_mirador,
        "mirador_override_url": mirador_override_url,
        "meta": meta,
        "source_notice_text": source_notice_text,
        "source_notice_tone": source_notice_tone,
    }


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


def _is_truthy_flag(raw: str | None) -> bool:
    value = str(raw or "").strip().lower()
    return value in {"1", "true", "on", "yes"}


def _as_int(raw: int | str | None, default: int = 0) -> int:
    try:
        return int(raw or default)
    except (TypeError, ValueError):
        return int(default)


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

    def _ocr_task(progress_callback=None):
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

    panel = Div(
        build_studio_tab_content(
            doc_id,
            library,
            page_idx,
            is_ocr_loading=is_loading,
            ocr_error=error_msg,
            history_message=error_msg,
        ),
        id="studio-right-panel",
        cls="flex-1 overflow-hidden h-full",
    )
    return [panel, toast] if toast else panel


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
