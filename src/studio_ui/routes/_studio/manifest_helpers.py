"""Manifest loading, canvas resolution, source-mode helpers."""

from __future__ import annotations

import json
from contextlib import suppress
from pathlib import Path

from fasthtml.common import Div

from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.iiif_logic import total_canvases as manifest_total_canvases
from universal_iiif_core.logger import get_logger
from universal_iiif_core.resolvers.manifest_fetch import fetch_manifest_dict
from universal_iiif_core.services.storage.vault_manager import VaultManager

from .ui_utils import _with_toast

logger = get_logger(__name__)


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
    try:
        with manifest_path.open(encoding="utf-8") as f:
            manifest_json = json.load(f)
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("Failed to load local manifest from %s: %s", manifest_path, exc)
        return {}, None
    return manifest_json, _resolve_initial_canvas(manifest_json, page)


def _manifest_total_pages(manifest_json: dict, ms_row: dict | None = None) -> int:
    """Resolve expected page count from manifest with DB fallback."""
    with suppress(Exception):
        total = int(manifest_total_canvases(manifest_json or {}))
        if total > 0:
            return total
    fallback = int((ms_row or {}).get("total_canvases") or 0)
    return max(fallback, 0)


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
        remote_manifest = fetch_manifest_dict(remote_manifest_url, retries=2) or {}
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
        remote_manifest = fetch_manifest_dict(remote_manifest_url, retries=2) or {}
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
