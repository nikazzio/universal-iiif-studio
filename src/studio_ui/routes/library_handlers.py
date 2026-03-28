"""Route handlers for Local Library page."""

from __future__ import annotations

import json
from pathlib import Path

from fasthtml.common import Request

from studio_ui.common.toasts import build_toast
from studio_ui.components.layout import base_layout
from studio_ui.components.library import render_library_card, render_library_page
from studio_ui.routes.discovery_helpers import start_downloader_thread
from studio_ui.routes.library_query import (
    _collect_docs_and_filters,
    _decode,
    _default_library_mode,
    _effective_state,
    _parse_missing_pages,
    _resolve_library_mode,
    _row_to_view_model,
    _safe_catalog_title,
)
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.http_client import get_http_client
from universal_iiif_core.library_catalog import infer_item_type, normalize_item_type, parse_manifest_catalog
from universal_iiif_core.logger import get_logger
from universal_iiif_core.services.ocr.storage import OCRStorage
from universal_iiif_core.services.storage.vault_manager import VaultManager

logger = get_logger(__name__)


def _refresh_card_response(
    *,
    doc_id: str,
    library: str,
    view: str = "grid",
    message: str,
    tone: str = "info",
):
    rows = VaultManager().get_all_manuscripts()
    target_row = next(
        (row for row in rows if str(row.get("id") or "") == doc_id and str(row.get("library") or "Unknown") == library),
        None,
    )
    if target_row is None:
        target_row = VaultManager().get_manuscript(doc_id)
    if not target_row:
        return _with_toast(
            _render_page_fragment(view=view),
            message,
            tone=tone,
        )
    doc = _row_to_view_model(target_row)
    fragment = render_library_card(doc, compact=view == "list")
    return _with_toast(fragment, message, tone=tone)


def _with_toast(fragment, message: str, tone: str = "info"):
    return [fragment, build_toast(message, tone=tone)]


def _render_page_fragment(
    *,
    view: str = "grid",
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "",
    action_required: str = "0",
    sort_by: str = "",
):
    effective_mode = _resolve_library_mode(mode)
    default_mode = _default_library_mode()
    docs, libraries, categories = _collect_docs_and_filters(
        q=q,
        state=state,
        library_filter=library_filter,
        category=category,
        mode=effective_mode,
        action_required=action_required,
        sort_by=sort_by,
    )
    return render_library_page(
        docs,
        view=view,
        q=q,
        state=state,
        library_filter=library_filter,
        category=category,
        mode=effective_mode,
        default_mode=default_mode,
        action_required=action_required,
        sort_by=sort_by,
        libraries=libraries,
        categories=categories,
    )


def _refresh_response(*, message: str, tone: str = "info", **filters):
    fragment = _render_page_fragment(**filters)
    return _with_toast(fragment, message, tone=tone)


def _update_catalog_metadata(doc_id: str, manifest_url: str) -> dict:
    manifest = get_http_client().get_json(manifest_url)
    if not manifest:
        raise ValueError("Manifest non accessibile")
    catalog = parse_manifest_catalog(
        manifest,
        manifest_url=manifest_url,
        doc_id=doc_id,
        enrich_external_reference=True,
    )
    display_title = str(catalog.get("catalog_title") or catalog.get("label") or doc_id)
    updates = {
        "display_title": display_title,
        "catalog_title": display_title,
        "title": str(catalog.get("label") or display_title),
        "shelfmark": str(catalog.get("shelfmark") or doc_id),
        "date_label": str(catalog.get("date_label") or ""),
        "language_label": str(catalog.get("language_label") or ""),
        "source_detail_url": str(catalog.get("source_detail_url") or ""),
        "reference_text": str(catalog.get("reference_text") or ""),
        "metadata_json": str(catalog.get("metadata_json") or "{}"),
        "item_type": str(catalog.get("item_type") or "non classificato"),
        "item_type_source": "auto",
        "item_type_confidence": float(catalog.get("item_type_confidence") or 0.0),
        "item_type_reason": str(catalog.get("item_type_reason") or ""),
    }
    VaultManager().upsert_manuscript(doc_id, **updates)
    return updates


def library_page(
    request: Request,
    view: str = "grid",
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "",
    action_required: str = "0",
    sort_by: str = "",
):
    """Render the Local Library page (full page or HTMX fragment)."""
    VaultManager().normalize_asset_states(limit=500)
    content = _render_page_fragment(
        view=view or "grid",
        q=q or "",
        state=state or "",
        library_filter=library_filter or "",
        category=category or "",
        mode=_resolve_library_mode(mode),
        action_required=action_required or "0",
        sort_by=sort_by or "",
    )
    if request.headers.get("HX-Request") == "true":
        return content
    return base_layout("Libreria", content, active_page="library")


def library_delete(
    doc_id: str,
    library: str,
    view: str = "grid",
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "operativa",
    action_required: str = "0",
    sort_by: str = "",
):
    """Delete one local manuscript and refresh library list."""
    doc_id = _decode(doc_id)
    _ = _decode(library)
    if OCRStorage().delete_document(doc_id, _):
        return _refresh_response(
            message=f"Documento '{doc_id}' eliminato.",
            tone="success",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )
    return _refresh_response(
        message=f"Errore eliminando '{doc_id}'.",
        tone="danger",
        view=view,
        q=q,
        state=state,
        library_filter=library_filter,
        category=category,
        mode=mode,
        action_required=action_required,
        sort_by=sort_by,
    )


def library_cleanup_partial(
    doc_id: str,
    library: str,
    view: str = "grid",
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "operativa",
    action_required: str = "0",
    sort_by: str = "",
):
    """Remove partial scans/temp data while keeping manuscript metadata."""
    doc_id = _decode(doc_id)
    library = _decode(library)
    try:
        storage = OCRStorage()
        paths = storage.get_document_paths(doc_id, library)
        scans_dir = Path(paths["scans"])
        removed = 0
        if scans_dir.exists():
            for img in scans_dir.glob("pag_*.jpg"):
                img.unlink(missing_ok=True)
                removed += 1
        temp_dir = get_config_manager().get_temp_dir() / doc_id
        if temp_dir.exists() and temp_dir.is_dir():
            import shutil

            shutil.rmtree(temp_dir)
        VaultManager().upsert_manuscript(
            doc_id,
            status="saved",
            asset_state="saved",
            downloaded_canvases=0,
            missing_pages_json="[]",
            error_log=None,
            local_scans_available=0,
            read_source_mode="remote",
            local_optimized=0,
            local_optimization_meta_json=None,
        )
        return _refresh_response(
            message=f"Pulizia parziale completata ({removed} pagine rimosse).",
            tone="success",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )
    except Exception:
        logger.exception("Partial cleanup failed for %s/%s", library, doc_id)
        return _refresh_response(
            message="Errore durante cleanup parziale.",
            tone="danger",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )


def library_start_download(
    doc_id: str,
    library: str,
    view: str = "grid",
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "operativa",
    action_required: str = "0",
    sort_by: str = "",
):
    """Queue a full download for an existing library entry."""
    doc_id = _decode(doc_id)
    library = _decode(library)
    ms = VaultManager().get_manuscript(doc_id) or {}
    manifest_url = str(ms.get("manifest_url") or "")
    if not manifest_url:
        return _refresh_response(
            message="Manifest URL non disponibile per questo documento.",
            tone="danger",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )
    if _effective_state(ms) == "complete":
        return _refresh_response(
            message="Documento già completo: usa 'Aggiorna metadati' o apri Studio.",
            tone="info",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )
    if _effective_state(ms) != "saved":
        return _refresh_response(
            message="Download completo disponibile solo per documenti in stato Remoto.",
            tone="info",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )
    try:
        start_downloader_thread(manifest_url, doc_id, library)
        return _refresh_response(
            message=f"Download accodato per {doc_id}.",
            tone="info",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )
    except Exception:
        logger.exception("Start download failed for %s/%s", library, doc_id)
        return _refresh_response(
            message="Impossibile accodare il download.",
            tone="danger",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )


def library_retry_missing(
    doc_id: str,
    library: str,
    view: str = "grid",
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "operativa",
    action_required: str = "0",
    sort_by: str = "",
):
    """Retry only missing pages when missing_pages_json is populated."""
    doc_id = _decode(doc_id)
    library = _decode(library)
    ms = VaultManager().get_manuscript(doc_id) or {}
    missing_pages = _parse_missing_pages(ms.get("missing_pages_json"))
    manifest_url = str(ms.get("manifest_url") or "")
    if not manifest_url:
        return _refresh_response(
            message="Manifest URL non disponibile per retry missing.",
            tone="danger",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )
    if not missing_pages:
        return _refresh_response(
            message="Nessuna pagina mancante rilevata.",
            tone="info",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )

    try:
        start_downloader_thread(manifest_url, doc_id, library, target_pages=set(missing_pages))
        return _refresh_response(
            message=f"Retry missing accodato per {doc_id} ({len(missing_pages)} pagine).",
            tone="info",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )
    except Exception:
        logger.exception("Retry missing failed for %s/%s", library, doc_id)
        return _refresh_response(
            message="Errore durante retry missing.",
            tone="danger",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )


def _parse_ranges(raw: str) -> set[int]:
    values: set[int] = set()
    text = (raw or "").strip()
    if not text:
        return values
    chunks = [c.strip() for c in text.split(",") if c.strip()]
    for chunk in chunks:
        if "-" in chunk:
            a, b = chunk.split("-", 1)
            start = int(a.strip())
            end = int(b.strip())
            if start > end:
                start, end = end, start
            for p in range(start, end + 1):
                values.add(p)
        else:
            values.add(int(chunk))
    return {v for v in values if v > 0}


def library_retry_range(
    doc_id: str,
    library: str,
    ranges: str = "",
    view: str = "grid",
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "operativa",
    action_required: str = "0",
    sort_by: str = "",
):
    """Retry a specific set/range of pages."""
    doc_id = _decode(doc_id)
    library = _decode(library)
    pages = _parse_ranges(ranges)
    if not pages:
        return _refresh_response(
            message="Range non valido. Usa formato: 1-10,15,18-20",
            tone="danger",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )

    ms = VaultManager().get_manuscript(doc_id) or {}
    manifest_url = str(ms.get("manifest_url") or "")
    if not manifest_url:
        return _refresh_response(
            message="Manifest URL non disponibile per retry range.",
            tone="danger",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )

    try:
        start_downloader_thread(manifest_url, doc_id, library, target_pages=pages)
        return _refresh_response(
            message=f"Retry range accodato per {doc_id} ({len(pages)} pagine).",
            tone="info",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )
    except Exception:
        logger.exception("Retry range failed for %s/%s", library, doc_id)
        return _refresh_response(
            message="Errore durante retry range.",
            tone="danger",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )


def library_download_full(*args, **kwargs):
    """Alias endpoint for full local download action."""
    return library_start_download(*args, **kwargs)


def library_download_range(*args, **kwargs):
    """Alias endpoint for page-range local download action."""
    return library_retry_range(*args, **kwargs)


def library_set_type(
    doc_id: str,
    library: str,
    item_type: str,
    view: str = "grid",
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "operativa",
    action_required: str = "0",
    sort_by: str = "",
):
    """Override automatic type classification for a manuscript."""
    doc_id = _decode(doc_id)
    _decode(library)
    normalized = normalize_item_type(item_type)
    VaultManager().upsert_manuscript(
        doc_id,
        item_type=normalized,
        item_type_source="manual",
        item_type_confidence=1.0,
        item_type_reason="manual_override",
    )
    return _refresh_response(
        message=f"Tipologia aggiornata: {normalized}",
        tone="success",
        view=view,
        q=q,
        state=state,
        library_filter=library_filter,
        category=category,
        mode=mode,
        action_required=action_required,
        sort_by=sort_by,
    )


def library_update_notes(
    doc_id: str,
    library: str,
    user_notes: str = "",
    view: str = "grid",
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "operativa",
    action_required: str = "0",
    sort_by: str = "",
):
    """Persist inline note edits for a manuscript card."""
    doc_id = _decode(doc_id)
    _decode(library)
    VaultManager().upsert_manuscript(doc_id, user_notes=(user_notes or "").strip())
    return _refresh_response(
        message="Note aggiornate.",
        tone="success",
        view=view,
        q=q,
        state=state,
        library_filter=library_filter,
        category=category,
        mode=mode,
        action_required=action_required,
        sort_by=sort_by,
    )


def library_refresh_metadata(
    doc_id: str,
    library: str,
    card_only: str = "0",
    view: str = "grid",
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "operativa",
    action_required: str = "0",
    sort_by: str = "",
):
    """Refresh stored catalog metadata from manifest + external detail page."""
    doc_id = _decode(doc_id)
    library = _decode(library)
    manuscript = VaultManager().get_manuscript(doc_id) or {}
    manifest_url = str(manuscript.get("manifest_url") or "")
    if not manifest_url:
        return _refresh_response(
            message="Manifest URL non disponibile per aggiornare i metadati.",
            tone="danger",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )
    try:
        _update_catalog_metadata(doc_id, manifest_url)
        if (card_only or "0").strip() == "1":
            return _refresh_card_response(
                doc_id=doc_id,
                library=library,
                view=view,
                message=f"Metadati aggiornati per {doc_id}.",
                tone="success",
            )
        return _refresh_response(
            message=f"Metadati aggiornati per {doc_id}.",
            tone="success",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )
    except ValueError as exc:
        return _refresh_response(
            message=str(exc),
            tone="danger",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )
    except Exception:
        logger.exception("Metadata refresh failed for %s/%s", library, doc_id)
        return _refresh_response(
            message="Errore aggiornando i metadati.",
            tone="danger",
            view=view,
            q=q,
            state=state,
            library_filter=library_filter,
            category=category,
            mode=mode,
            action_required=action_required,
            sort_by=sort_by,
        )


def library_reclassify(
    doc_id: str,
    library: str,
    view: str = "grid",
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "operativa",
    action_required: str = "0",
    sort_by: str = "",
):
    """Recalculate item category automatically from available metadata."""
    doc_id = _decode(doc_id)
    library = _decode(library)
    manuscript = VaultManager().get_manuscript(doc_id) or {}
    metadata_map: dict[str, str] = {}
    raw_metadata = str(manuscript.get("metadata_json") or "").strip()
    if raw_metadata:
        try:
            parsed = json.loads(raw_metadata)
            if isinstance(parsed, dict):
                metadata_map = {str(k): str(v) for k, v in parsed.items()}
        except Exception:
            metadata_map = {}

    label = _safe_catalog_title(manuscript)
    description = str(manuscript.get("reference_text") or manuscript.get("title") or "")
    item_type, confidence, reason = infer_item_type(label, description, metadata_map)

    VaultManager().upsert_manuscript(
        doc_id,
        item_type=item_type,
        item_type_source="auto",
        item_type_confidence=confidence,
        item_type_reason=reason,
    )
    return _refresh_response(
        message=f"Classificazione aggiornata: {item_type}",
        tone="success",
        view=view,
        q=q,
        state=state,
        library_filter=library_filter,
        category=category,
        mode=mode,
        action_required=action_required,
        sort_by=sort_by,
    )


def library_reclassify_all(
    view: str = "grid",
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "operativa",
    action_required: str = "0",
    sort_by: str = "",
):
    """Recalculate automatic category for all manuscripts not manually overridden."""
    vm = VaultManager()
    docs = vm.get_all_manuscripts()
    updated = 0
    for doc in docs:
        if str(doc.get("item_type_source") or "auto") == "manual":
            continue
        label = _safe_catalog_title(doc)
        description = str(doc.get("reference_text") or doc.get("title") or "")
        metadata_map: dict[str, str] = {}
        try:
            parsed = json.loads(str(doc.get("metadata_json") or "{}"))
            if isinstance(parsed, dict):
                metadata_map = {str(k): str(v) for k, v in parsed.items()}
        except Exception:
            metadata_map = {}
        item_type, confidence, reason = infer_item_type(label, description, metadata_map)
        vm.upsert_manuscript(
            str(doc.get("id") or ""),
            item_type=item_type,
            item_type_source="auto",
            item_type_confidence=confidence,
            item_type_reason=reason,
        )
        updated += 1

    return _refresh_response(
        message=f"Riclassificazione completata ({updated} elementi).",
        tone="success",
        view=view,
        q=q,
        state=state,
        library_filter=library_filter,
        category=category,
        mode=mode,
        action_required=action_required,
        sort_by=sort_by,
    )


def library_normalize_states(
    view: str = "grid",
    q: str = "",
    state: str = "",
    library_filter: str = "",
    category: str = "",
    mode: str = "operativa",
    action_required: str = "0",
    sort_by: str = "",
):
    """Run a normalization pass for legacy/inconsistent state records."""
    updated = VaultManager().normalize_asset_states(limit=1000)
    return _refresh_response(
        message=f"Normalizzazione stati completata ({updated} record aggiornati).",
        tone="success",
        view=view,
        q=q,
        state=state,
        library_filter=library_filter,
        category=category,
        mode=mode,
        action_required=action_required,
        sort_by=sort_by,
    )
