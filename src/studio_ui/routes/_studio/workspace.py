"""Workspace helpers — build base context and resolve manifest for Studio."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

from fasthtml.common import Request

from studio_ui.common.page_inventory import resolve_page_inventory
from studio_ui.components.studio.tabs import render_studio_tabs
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.logger import get_logger
from universal_iiif_core.resolvers.mag_parser import is_iccu_magparser_url
from universal_iiif_core.services.ocr.storage import OCRStorage
from universal_iiif_core.services.storage.vault_manager import VaultManager
from universal_iiif_core.utils import load_json

from .context import _normalize_studio_tab, _resolve_studio_title
from .manifest_helpers import (
    _build_source_notice,
    _load_studio_manifest_context,
    _manifest_total_pages,
    _persist_studio_source_state,
    _resolve_initial_canvas,
    _resolve_manifest_for_selected_source,
    _resolve_studio_read_source_mode,
)

logger = get_logger(__name__)


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
    if is_iccu_magparser_url(manifest_url):
        manifest_url = f"/api/iccu/manifest?url={quote(manifest_url, safe='')}"
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
