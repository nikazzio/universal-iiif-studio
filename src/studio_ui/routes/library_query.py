"""Shared query/filter helpers for library route handlers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote

from studio_ui.common.library_constants import to_optional_bool
from studio_ui.common.title_utils import resolve_preferred_title
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.library_catalog import ITEM_TYPES, normalize_item_type
from universal_iiif_core.logger import get_logger
from universal_iiif_core.services.storage.vault_manager import VaultManager

logger = get_logger(__name__)

STATE_PRIORITY = {
    "error": 0,
    "partial": 1,
    "downloading": 2,
    "running": 2,
    "queued": 3,
    "saved": 4,
    "complete": 5,
}
RUNNING_STATES = {"downloading", "running", "queued", "pending"}


def _decode(value: str) -> str:
    return unquote(value or "")


def _default_library_mode() -> str:
    raw = get_config_manager().get_setting("library.default_mode", "operativa")
    return "archivio" if str(raw or "").strip().lower() == "archivio" else "operativa"


def _resolve_library_mode(mode: str | None) -> str:
    value = str(mode or "").strip().lower()
    if value in {"operativa", "archivio"}:
        return value
    return _default_library_mode()


def _parse_missing_pages(raw: str | None) -> list[int]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        try:
            page = int(item)
        except (TypeError, ValueError):
            continue
        if page > 0:
            out.append(page)
    return sorted(set(out))


def _effective_state(row: dict) -> str:
    status = str(row.get("status") or "").lower()
    asset_state = str(row.get("asset_state") or "").lower()
    total = int(row.get("total_canvases") or 0)
    downloaded = int(row.get("downloaded_canvases") or 0)

    if status in RUNNING_STATES:
        return "downloading" if status == "pending" else status
    if status == "error":
        return "error"
    if asset_state in {"partial", "complete", "saved"}:
        return asset_state
    if downloaded <= 0:
        return "saved"
    if total <= 0 or downloaded >= total:
        return "complete"
    return "partial"


def _needs_action(state: str) -> bool:
    return state in {"saved", "partial", "error", "downloading", "running", "queued"}


def _matches_query(doc: dict, query: str) -> bool:
    q = (query or "").strip().lower()
    if not q:
        return True
    haystack = " ".join(
        [
            str(doc.get("display_title") or ""),
            str(doc.get("catalog_title") or ""),
            str(doc.get("reference_text") or ""),
            str(doc.get("shelfmark") or ""),
            str(doc.get("id") or ""),
            str(doc.get("library") or ""),
            str(doc.get("author") or ""),
            str(doc.get("description") or ""),
            str(doc.get("publisher") or ""),
        ]
    ).lower()
    return q in haystack


def _metadata_preview_items(raw_metadata_json: str, max_items: int = 8) -> list[tuple[str, str]]:
    text = (raw_metadata_json or "").strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []

    ignored = {
        "shelfmark",
        "date",
        "language",
        "description",
        "title",
        "author",
        "creator",
        "publisher",
        "source",
    }
    items: list[tuple[str, str]] = []
    for key, value in payload.items():
        if not key or key.lower().strip() in ignored:
            continue
        val = str(value or "").strip()
        if not val:
            continue
        items.append((key, val))
    return items[:max_items]


def _safe_catalog_title(row: dict) -> str:
    doc_id = str(row.get("id") or "").strip()
    return resolve_preferred_title(row, fallback_doc_id=doc_id)


def _to_downloads_url(path: Path) -> str:
    downloads_dir = get_config_manager().get_downloads_dir().resolve()
    try:
        rel = path.resolve().relative_to(downloads_dir)
    except Exception:
        return ""
    encoded = "/".join(quote(part, safe="") for part in rel.parts)
    return f"/downloads/{encoded}"


def _thumbnail_url(row: dict) -> str:
    candidates: list[Path] = []
    local_path_raw = str(row.get("local_path") or "").strip()
    if local_path_raw:
        candidates.append(Path(local_path_raw) / "scans" / "pag_0000.jpg")

    library = str(row.get("library") or "Unknown")
    doc_id = str(row.get("id") or "").strip()
    if doc_id:
        candidates.append(get_config_manager().get_downloads_dir() / library / doc_id / "scans" / "pag_0000.jpg")

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return _to_downloads_url(candidate)
    return ""


def _to_optional_bool(value) -> bool | None:
    return to_optional_bool(value)


def _pdf_dir_candidates(row: dict) -> list[Path]:
    candidates: list[Path] = []
    local_path_raw = str(row.get("local_path") or "").strip()
    if local_path_raw:
        candidates.append(Path(local_path_raw) / "pdf")

    lib = str(row.get("library") or "Unknown")
    doc_id = str(row.get("id") or "").strip()
    if doc_id:
        candidates.append(get_config_manager().get_downloads_dir() / lib / doc_id / "pdf")

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _pdf_local_stats(row: dict) -> tuple[bool, int]:
    count = 0
    for directory in _pdf_dir_candidates(row):
        if not directory.exists() or not directory.is_dir():
            continue
        count += sum(1 for pdf in directory.glob("*.pdf") if pdf.is_file())

    if count > 0:
        return True, count

    db_flag = bool(_to_optional_bool(row.get("pdf_local_available")))
    if db_flag:
        return True, 1
    return False, 0


def _pdf_source(row: dict) -> str:
    native = _to_optional_bool(row.get("has_native_pdf"))
    if native is True:
        return "native"
    if native is False:
        return "images"
    return "unknown"


def _operational_rank(doc: dict) -> int:
    state = str(doc.get("asset_state") or "saved").lower()
    has_missing = bool(doc.get("has_missing_pages"))
    if state == "error":
        return 0
    if state == "partial" and has_missing:
        return 1
    if state in {"downloading", "running", "queued"}:
        return 2
    if state in {"saved", "partial"}:
        return 3
    if state == "complete":
        return 4
    return 5


def _updated_at_sort_value(doc: dict) -> float:
    raw = str(doc.get("updated_at") or doc.get("created_at") or "").strip()
    if not raw:
        return 0.0
    normalized = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return 0.0


def _sort_docs(docs: list[dict], mode: str, sort_by: str) -> list[dict]:
    mode_value = _resolve_library_mode(mode)
    sort_value = (sort_by or "").strip().lower()

    if mode_value == "archivio" and not sort_value:
        sort_value = "title_az"
    if mode_value != "archivio" and not sort_value:
        sort_value = "priority"

    if sort_value == "recent":
        return sorted(
            docs,
            key=lambda d: (
                str(d.get("updated_at") or d.get("created_at") or ""),
                str(d.get("display_title") or "").lower(),
            ),
            reverse=True,
        )
    if sort_value == "title_az":
        return sorted(
            docs,
            key=lambda d: (
                str(d.get("library") or "").lower(),
                str(d.get("item_type") or "").lower(),
                str(d.get("display_title") or "").lower(),
            ),
        )
    if sort_value == "pages_desc":
        return sorted(
            docs,
            key=lambda d: (
                -(int(d.get("total_canvases") or 0)),
                str(d.get("display_title") or "").lower(),
            ),
        )
    return sorted(
        docs,
        key=lambda d: (
            _operational_rank(d),
            STATE_PRIORITY.get(str(d.get("asset_state") or "saved"), 99),
            -len(d.get("missing_pages") or []),
            -_updated_at_sort_value(d),
            str(d.get("library") or "").lower(),
            str(d.get("item_type") or "").lower(),
            -(int(d.get("total_canvases") or 0)),
            str(d.get("display_title") or "").lower(),
        ),
    )


def _collect_docs_and_filters(
    *,
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "",
    action_required: str = "0",
    sort_by: str = "",
) -> tuple[list[dict], list[str], list[str]]:
    rows = VaultManager().get_all_manuscripts()
    libraries: set[str] = set()
    categories: set[str] = set()
    docs: list[dict] = []

    state_filter = (state or "").strip().lower()
    lib_filter = (library_filter or "").strip()
    category_filter = normalize_item_type(category)
    action_filter = (action_required or "0").strip() == "1"

    for row in rows:
        doc = _row_to_view_model(row)
        lib = str(doc.get("library") or "Unknown")
        item_type = str(doc.get("item_type") or "non classificato")
        libraries.add(lib)
        categories.add(item_type)

        if state_filter and doc["asset_state"] != state_filter:
            continue
        if lib_filter and lib != lib_filter:
            continue
        if category and item_type != category_filter:
            continue
        if action_filter and not _needs_action(doc["asset_state"]):
            continue
        if not _matches_query(doc, q):
            continue
        docs.append(doc)

    ordered_categories = [cat for cat in ITEM_TYPES if cat in categories]
    return _sort_docs(docs, _resolve_library_mode(mode), sort_by), sorted(libraries), ordered_categories


def _row_to_view_model(row: dict) -> dict:
    lib = str(row.get("library") or "Unknown")
    item_type = normalize_item_type(str(row.get("item_type") or ""))
    missing_pages = _parse_missing_pages(row.get("missing_pages_json"))
    pdf_local_available, pdf_local_count = _pdf_local_stats(row)
    native_pdf = _to_optional_bool(row.get("has_native_pdf"))
    return {
        **row,
        "library": lib,
        "item_type": item_type,
        "display_title": _safe_catalog_title(row),
        "asset_state": _effective_state(row),
        "downloaded_canvases": int(row.get("downloaded_canvases") or 0),
        "total_canvases": int(row.get("total_canvases") or 0),
        "missing_pages": missing_pages,
        "has_missing_pages": bool(missing_pages),
        "item_type_source": row.get("item_type_source") or "auto",
        "item_type_confidence": float(row.get("item_type_confidence") or 0.0),
        "author": str(row.get("author") or ""),
        "description": str(row.get("description") or ""),
        "publisher": str(row.get("publisher") or ""),
        "attribution": str(row.get("attribution") or ""),
        "reference_text": str(row.get("reference_text") or ""),
        "shelfmark": str(row.get("shelfmark") or row.get("id") or ""),
        "source_detail_url": str(row.get("source_detail_url") or ""),
        "user_notes": str(row.get("user_notes") or ""),
        "metadata_preview": _metadata_preview_items(str(row.get("metadata_json") or "")),
        "thumbnail_url": _thumbnail_url(row),
        "has_native_pdf": native_pdf,
        "pdf_source": _pdf_source(row),
        "pdf_local_available": pdf_local_available,
        "pdf_local_count": int(pdf_local_count),
    }
