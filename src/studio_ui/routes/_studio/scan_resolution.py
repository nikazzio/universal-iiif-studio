"""Local scan info, remote dimension probing, download-method helpers."""

from __future__ import annotations

import time
from contextlib import suppress
from pathlib import Path
from typing import Any

from universal_iiif_core.iiif_resolution import probe_remote_max_dimensions
from universal_iiif_core.logger import get_logger

logger = get_logger(__name__)


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
