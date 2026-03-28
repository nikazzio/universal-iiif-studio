"""Persistence and prefetch helpers for Discovery handlers."""

from __future__ import annotations

import time
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import Any

from studio_ui.common.title_utils import resolve_preferred_title
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.logger import get_logger
from universal_iiif_core.resolvers.parsers import IIIFManifestParser
from universal_iiif_core.services.storage.vault_manager import VaultManager
from universal_iiif_core.utils import get_json, save_json

logger = get_logger(__name__)


def downloads_doc_path(library: str, doc_id: str) -> Path:
    """Resolve a document path under configured downloads root with traversal guard."""
    root = get_config_manager().get_downloads_dir().resolve()
    target = (root / str(library or "").strip() / str(doc_id or "").strip()).resolve()
    try:
        target.relative_to(root)
    except Exception as exc:
        raise ValueError("Identificatore documento non valido.") from exc
    return target


def find_manuscript_by_id_and_library(doc_id: str, library: str) -> dict | None:
    """Find a manuscript row matching both id and library, with fallback lookup."""
    target_id = str(doc_id or "").strip()
    target_library = str(library or "").strip()
    if not target_id or not target_library:
        return None

    vm = VaultManager()
    for row in vm.get_all_manuscripts():
        if str(row.get("id") or "").strip() == target_id and str(row.get("library") or "").strip() == target_library:
            return row

    fallback = vm.get_manuscript(target_id) or {}
    if str(fallback.get("library") or "").strip() == target_library:
        return fallback
    return None


def is_manuscript_complete(row: dict | None) -> bool:
    """Return True when a manuscript row is considered complete for download gating."""
    if not row:
        return False
    status = str(row.get("status") or "").strip().lower()
    asset_state = str(row.get("asset_state") or "").strip().lower()
    downloaded = int(row.get("downloaded_canvases") or 0)
    total = int(row.get("total_canvases") or 0)
    if status in {"complete", "completed"}:
        return True
    if asset_state == "complete":
        return True
    return total > 0 and downloaded >= total


def resolve_saved_entry_title(info: dict, doc_id: str, *, result_title: str = "") -> str:
    """Choose the strongest human title available for a saved discovery entry."""
    clean_doc_id = str(doc_id or "").strip()
    clean_result_title = str(result_title or "").strip()
    clean_shelfmark = str(info.get("shelfmark") or "").strip()
    preferred = str(
        resolve_preferred_title(
            {
                "id": clean_doc_id,
                "catalog_title": str(info.get("catalog_title") or "").strip(),
                "display_title": str(info.get("label") or "").strip(),
                "title": str(info.get("label") or "").strip(),
                "reference_text": clean_result_title or str(info.get("reference_text") or "").strip(),
                "shelfmark": clean_shelfmark,
            },
            fallback_doc_id=clean_doc_id,
        )
        or ""
    ).strip()
    if clean_result_title and preferred in {"", clean_doc_id, clean_shelfmark}:
        return clean_result_title
    return preferred or clean_result_title or clean_doc_id or "Senza Titolo"


def upsert_saved_entry(
    manifest_url: str,
    doc_id: str,
    library: str,
    *,
    label: str = "",
    description: str = "",
    pages: int = 0,
    has_native_pdf: bool | None = None,
    catalog_title: str = "",
    author: str = "",
    publisher: str = "",
    attribution: str = "",
    shelfmark: str = "",
    date_label: str = "",
    language_label: str = "",
    source_detail_url: str = "",
    reference_text: str = "",
    item_type: str = "non classificato",
    item_type_confidence: float = 0.0,
    item_type_reason: str = "",
    metadata_json: str = "{}",
    manifest_local_available: bool = False,
    thumbnail_url: str = "",
    preferred_title: str = "",
) -> None:
    """Create or update a saved discovery entry preserving existing runtime state flags."""
    entry_label = (
        str(preferred_title or "").strip()
        or str(label or "").strip()
        or str(catalog_title or "").strip()
        or str(doc_id or "").strip()
        or "Senza Titolo"
    )
    total = int(pages or 0)
    v = VaultManager()
    existing = find_manuscript_by_id_and_library(doc_id, library) or {}
    existing_status = str(existing.get("status") or "").strip().lower()
    existing_asset_state = str(existing.get("asset_state") or "").strip().lower()
    known_states = {"saved", "partial", "complete", "downloading", "running", "queued", "error"}
    status_to_store = existing_status if existing_status in known_states else "saved"
    asset_state_to_store = existing_asset_state if existing_asset_state in known_states else "saved"
    existing_total = int(existing.get("total_canvases") or 0)
    existing_downloaded = int(existing.get("downloaded_canvases") or 0)
    manifest_flag = 1 if manifest_local_available else int(existing.get("manifest_local_available") or 0)
    local_scans_flag = int(existing.get("local_scans_available") or 0)
    pdf_local_flag = int(existing.get("pdf_local_available") or 0)
    existing_thumbnail = str(existing.get("thumbnail_url") or "").strip()
    source_mode = str(existing.get("read_source_mode") or "remote").strip().lower() or "remote"
    thumbnail_to_store = str(thumbnail_url or existing_thumbnail or "").strip()
    catalog_title_to_store = str(catalog_title or "").strip() or entry_label
    if str(preferred_title or "").strip():
        catalog_title_to_store = str(preferred_title).strip()
    v.upsert_manuscript(
        doc_id,
        display_title=entry_label,
        title=entry_label,
        catalog_title=catalog_title_to_store,
        library=library,
        manifest_url=manifest_url,
        local_path=str(downloads_doc_path(library, doc_id)),
        status=status_to_store,
        asset_state=asset_state_to_store,
        total_canvases=max(total, existing_total),
        downloaded_canvases=max(existing_downloaded, 0),
        has_native_pdf=1 if has_native_pdf else 0 if has_native_pdf is False else None,
        pdf_local_available=pdf_local_flag,
        manifest_local_available=manifest_flag,
        local_scans_available=local_scans_flag,
        read_source_mode=source_mode if source_mode in {"local", "remote"} else "remote",
        item_type=item_type or "non classificato",
        item_type_source="auto",
        item_type_confidence=float(item_type_confidence or 0.0),
        item_type_reason=item_type_reason or "",
        missing_pages_json="[]",
        author=author or "",
        publisher=publisher or "",
        attribution=attribution or "",
        description=description or "",
        shelfmark=shelfmark or "",
        date_label=date_label or "",
        language_label=language_label or "",
        source_detail_url=source_detail_url or "",
        reference_text=reference_text or "",
        thumbnail_url=thumbnail_to_store,
        metadata_json=metadata_json or "{}",
    )


def _thumbnail_url_from_manifest(manifest_payload: dict, *, manifest_url: str = "", doc_id: str = "") -> str:
    if not isinstance(manifest_payload, dict):
        return ""
    return IIIFManifestParser.extract_thumbnail(manifest_payload, manifest_url=manifest_url, doc_id=doc_id or None)


def _stream_thumbnail_bytes(url: str, *, max_bytes: int) -> BytesIO | None:
    from universal_iiif_core.http_client import get_http_client

    client = get_http_client()
    response = client.get(url, timeout=(10, 15), stream=True)
    try:
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                if int(content_length) > max_bytes:
                    return None
            except ValueError:
                pass

        buffer = BytesIO()
        downloaded = 0
        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue
            downloaded += len(chunk)
            if downloaded > max_bytes:
                return None
            buffer.write(chunk)
    finally:
        response.close()
    if buffer.tell() <= 0:
        return None
    buffer.seek(0)
    return buffer


def _save_preview_jpeg(buffer: BytesIO, preview_path: Path) -> bool:
    from PIL import DecompressionBombError, Image, UnidentifiedImageError

    try:
        with Image.open(buffer) as img:
            rgb = img.convert("RGB")
            width, height = rgb.size
            long_edge = max(width, height)
            if long_edge > 640:
                scale = 640 / float(long_edge)
                target_size = (max(1, int(width * scale)), max(1, int(height * scale)))
                rgb = rgb.resize(target_size, Image.Resampling.LANCZOS)
            rgb.save(preview_path, format="JPEG", quality=82, optimize=True, progressive=True)
        return True
    except (DecompressionBombError, OSError, UnidentifiedImageError):
        return False


def _download_prefetch_preview(data_dir: Path, thumbnail_url: str) -> str:
    clean_url = str(thumbnail_url or "").strip()
    if not clean_url:
        return ""
    if not clean_url.lower().startswith(("http://", "https://")):
        return ""
    preview_path = data_dir / "preview.jpg"
    max_bytes = 5 * 1024 * 1024
    try:
        buffer = _stream_thumbnail_bytes(clean_url, max_bytes=max_bytes)
        if buffer is None:
            return ""
        if not _save_preview_jpeg(buffer, preview_path):
            return ""
        return str(preview_path)
    except Exception:
        logger.debug("Unable to persist prefetch preview from %s", clean_url, exc_info=True)
        return ""


def persist_prefetch_light(
    manifest_url: str,
    doc_id: str,
    library: str,
    *,
    title: str,
    description: str,
    pages: int,
    thumbnail_url: str = "",
    get_json_fn: Callable[..., Any] | None = None,
) -> tuple[bool, str]:
    """Save lightweight local files for `saved` entries (manifest + metadata)."""
    doc_root = downloads_doc_path(library, doc_id)
    data_dir = doc_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    metadata_payload = {
        "id": doc_id,
        "title": title or doc_id,
        "label": title or doc_id,
        "description": description or "",
        "manifest_url": manifest_url,
        "manifest": manifest_url,
        "pages": int(pages or 0),
        "download_date": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_json(data_dir / "metadata.json", metadata_payload)

    fetch_json = get_json_fn or get_json
    manifest_payload = fetch_json(str(manifest_url or "").strip(), retries=2)
    derived_thumb = str(thumbnail_url or "").strip()
    manifest_cached = False
    if isinstance(manifest_payload, dict) and manifest_payload:
        save_json(data_dir / "manifest.json", manifest_payload)
        manifest_cached = True
        if not derived_thumb:
            derived_thumb = _thumbnail_url_from_manifest(
                manifest_payload,
                manifest_url=manifest_url,
                doc_id=doc_id,
            )

    local_preview_path = _download_prefetch_preview(data_dir, derived_thumb)
    return manifest_cached, local_preview_path or derived_thumb
