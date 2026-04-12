"""Thumbnail pagination, export-tab defaults, remote-resolution cache."""

from __future__ import annotations

import json
import time
from contextlib import suppress
from pathlib import Path
from typing import Any
from urllib.parse import quote

from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.logger import get_logger
from universal_iiif_core.pdf_profiles import list_profiles, resolve_effective_profile
from universal_iiif_core.services.storage.vault_manager import VaultManager

logger = get_logger(__name__)


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
