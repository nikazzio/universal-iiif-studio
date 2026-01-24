from __future__ import annotations

from contextlib import suppress
from pathlib import Path

import streamlit as st

from iiif_downloader.config_manager import get_config_manager
from iiif_downloader.export_studio import (
    COMPRESSION_PROFILES,
    build_professional_pdf,
    clean_filename,
)
from iiif_downloader.ocr.storage import OCRStorage
from iiif_downloader.thumbnail_utils import guess_available_pages

from .documents import load_document_option, safe_read_json
from .thumbnail_grid import render_thumbnail_grid


def _get_int_setting(key: str, default: int, *, min_v: int, max_v: int) -> int:
    cm = get_config_manager()
    try:
        value = int(cm.get_setting(key, default) or default)
    except (TypeError, ValueError):
        value = default
    return max(min_v, min(max_v, value))


def _get_bool_setting(key: str, default: bool) -> bool:
    cm = get_config_manager()
    return bool(cm.get_setting(key, default))


def _paginate(*, items: list[int], enabled: bool, page_size: int) -> list[int]:
    if not enabled:
        return items

    total = len(items)
    if total == 0:
        return items

    page_count = max(1, (total + page_size - 1) // page_size)
    page_index = st.number_input("Pagina", min_value=1, max_value=page_count, value=1, step=1)
    start = (int(page_index) - 1) * page_size
    end = min(total, start + page_size)
    return items[start:end]


def _load_document_options(storage: OCRStorage):
    documents = storage.list_documents()
    if not documents:
        st.info("Nessun documento trovato. Scarica o importa un documento prima.")
        return None

    options = []
    for d in documents:
        opt = load_document_option(storage, d)
        if opt:
            options.append(opt)

    if not options:
        st.info("Nessun documento valido trovato.")
        return None
    return options


def _select_document(options):
    selected_label = st.selectbox("Documento", [o.label for o in options])
    return next(o for o in options if o.label == selected_label)


def _get_scan_paths(storage: OCRStorage, doc_opt):
    paths = storage.get_document_paths(doc_opt.doc_id, doc_opt.library)
    scans_dir: Path = paths["scans"]
    if not scans_dir.exists():
        st.error(f"Scans non trovati: {scans_dir}")
        return None, None
    return paths, scans_dir


def _get_available_pages(scans_dir: Path) -> list[int] | None:
    available_pages = guess_available_pages(scans_dir)
    if not available_pages:
        st.warning("Nessuna immagine trovata in scans/.")
        return None
    return available_pages


def _render_cover_section(doc_opt):
    st.subheader("Frontespizio")
    col1, col2 = st.columns(2)
    with col1:
        cover_title = st.text_input("Titolo", value=str(doc_opt.meta.get("label") or doc_opt.label))
        cover_curator = st.text_input("Curatore / Note", value="")
    with col2:
        cover_description = st.text_area("Descrizione", value="", height=110)

    cover_logo = st.file_uploader(
        "Logo (opzionale)",
        type=["png", "jpg", "jpeg"],
        help="Carica un logo da mostrare sul frontespizio.",
    )
    cover_logo_bytes = cover_logo.read() if cover_logo is not None else None
    return cover_title, cover_curator, cover_description, cover_logo_bytes


def _render_options_section():
    st.subheader("Opzioni PDF")
    compression = st.selectbox("Compressione", list(COMPRESSION_PROFILES.keys()), index=1)
    mode = st.selectbox("Trascrizione", ["Solo immagini", "Testo a fronte", "PDF Ricercabile"], index=0)
    return compression, mode


def _init_export_selection(doc_key: str, action_pages: list[int], default_select_all: bool) -> None:
    init_key = f"_export_init_{doc_key}"
    if default_select_all and not st.session_state.get(init_key, False):
        for p in action_pages:
            st.session_state[f"export_page_{doc_key}_{p}"] = True
        st.session_state[init_key] = True


def _render_pages_section(
    *,
    doc_key: str,
    action_pages: list[int],
    visible_pages: list[int],
    scans_dir: Path,
    thumbnails_dir: Path,
    thumb_columns: int,
    thumb_max_edge: int,
    thumb_jpeg_quality: int,
    hover_preview_enabled: bool,
    hover_preview_max_edge: int,
    hover_preview_jpeg_quality: int,
    hover_preview_delay_ms: int,
    hover_preview_max_tiles: int,
) -> list[int]:
    st.subheader("Pagine")

    export_all_key = f"export_all_{doc_key}"
    export_all = st.checkbox(
        "📄 Esporta tutto il PDF",
        value=bool(st.session_state.get(export_all_key, False)),
        help="Se attivo, esporta tutte le pagine disponibili.",
    )
    st.session_state[export_all_key] = export_all

    effective_hover = hover_preview_enabled and (len(visible_pages) <= hover_preview_max_tiles)
    return render_thumbnail_grid(
        doc_key=doc_key,
        pages=visible_pages,
        action_pages=action_pages,
        scans_dir=scans_dir,
        thumbnails_dir=thumbnails_dir,
        columns=thumb_columns,
        max_long_edge_px=thumb_max_edge,
        jpeg_quality=thumb_jpeg_quality,
        hover_preview_enabled=effective_hover,
        hover_preview_max_long_edge_px=hover_preview_max_edge,
        hover_preview_jpeg_quality=hover_preview_jpeg_quality,
        hover_preview_delay_ms=hover_preview_delay_ms,
    )


def _resolve_output_dir(paths: dict, out_name: str) -> tuple[Path, Path]:
    out_dir = paths.get("exports")
    if not out_dir:
        out_dir = (paths.get("data") or paths["root"] / "data") / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir, out_dir / out_name


def _collect_source_url(doc_opt, manifest_json: dict) -> str:
    return str(
        manifest_json.get("source_url")
        or manifest_json.get("manifest_url")
        or manifest_json.get("id")
        or manifest_json.get("@id")
        or doc_opt.meta.get("manifest")
        or doc_opt.meta.get("source_url")
        or ""
    )


def render_export_studio_page() -> None:
    """Render the Export Studio interface for professional PDFs."""
    st.title("Export Studio")
    st.caption("Crea un PDF professionale (frontespizio + pagine selezionate + colophon).")

    thumb_max_edge = _get_int_setting("thumbnails.max_long_edge_px", 320, min_v=64, max_v=900)
    thumb_jpeg_quality = _get_int_setting("thumbnails.jpeg_quality", 70, min_v=30, max_v=95)
    thumb_columns = _get_int_setting("thumbnails.columns", 6, min_v=3, max_v=10)

    paginate_enabled = _get_bool_setting("thumbnails.paginate_enabled", True)
    page_size = _get_int_setting("thumbnails.page_size", 48, min_v=12, max_v=500)

    default_select_all = _get_bool_setting("thumbnails.default_select_all", True)

    hover_preview_enabled = _get_bool_setting("thumbnails.hover_preview_enabled", True)
    hover_preview_max_edge = _get_int_setting("thumbnails.hover_preview_max_long_edge_px", 900, min_v=300, max_v=2000)
    hover_preview_jpeg_quality = _get_int_setting("thumbnails.hover_preview_jpeg_quality", 82, min_v=30, max_v=95)
    hover_preview_delay_ms = _get_int_setting("thumbnails.hover_preview_delay_ms", 550, min_v=0, max_v=3000)

    hover_preview_max_tiles = _get_int_setting("thumbnails.hover_preview_max_tiles", 72, min_v=12, max_v=200)

    storage = OCRStorage()
    options = _load_document_options(storage)
    if not options:
        return

    doc_opt = _select_document(options)
    paths, scans_dir = _get_scan_paths(storage, doc_opt)
    if not paths or not scans_dir:
        return

    available_pages = _get_available_pages(scans_dir)
    if not available_pages:
        return

    cover_title, cover_curator, cover_description, cover_logo_bytes = _render_cover_section(doc_opt)
    compression, mode = _render_options_section()

    doc_key = f"{doc_opt.library}_{doc_opt.doc_id}".replace(" ", "_")
    thumbnails_dir = paths.get("thumbnails") or (paths["data"] / "thumbnails")

    action_pages = list(available_pages)
    total_tiles = len(action_pages)

    # Rendering many images/widgets is expensive: force pagination for long documents.
    effective_paginate = paginate_enabled or (total_tiles > page_size)
    visible_pages = _paginate(items=action_pages, enabled=effective_paginate, page_size=page_size)

    init_key = f"_export_init_{doc_key}"
    if default_select_all and not st.session_state.get(init_key, False):
        for p in action_pages:
            st.session_state[f"export_page_{doc_key}_{p}"] = True
        st.session_state[init_key] = True

    # Enable hover previews when the rendered grid is reasonably small.
    # For long documents we paginate; in that case we should base the decision on
    # visible tiles, otherwise hover previews would be disabled forever.
    _init_export_selection(doc_key, action_pages, default_select_all)
    selected_pages = _render_pages_section(
        doc_key=doc_key,
        action_pages=action_pages,
        visible_pages=visible_pages,
        scans_dir=scans_dir,
        thumbnails_dir=thumbnails_dir,
        thumb_columns=thumb_columns,
        thumb_max_edge=thumb_max_edge,
        thumb_jpeg_quality=thumb_jpeg_quality,
        hover_preview_enabled=hover_preview_enabled,
        hover_preview_max_edge=hover_preview_max_edge,
        hover_preview_jpeg_quality=hover_preview_jpeg_quality,
        hover_preview_delay_ms=hover_preview_delay_ms,
        hover_preview_max_tiles=hover_preview_max_tiles,
    )

    st.divider()
    default_name = clean_filename(f"{doc_opt.library}_{doc_opt.doc_id}_{compression}_{mode}.pdf")
    out_name = st.text_input("Nome file PDF", value=default_name)
    out_dir, out_path = _resolve_output_dir(paths, out_name)

    if st.button(
        "📦 Genera PDF",
        type="primary",
        width="stretch",
        disabled=not bool(selected_pages),
    ):
        with st.spinner("Generazione PDF in corso..."):
            manifest_json = safe_read_json(paths["manifest"]) or {}
            transcription_json = safe_read_json(paths["transcription"])

            source_url = _collect_source_url(doc_opt, manifest_json)

            meta_for_cover = dict(doc_opt.meta or {})
            if source_url:
                meta_for_cover.setdefault("source_url", source_url)
                meta_for_cover.setdefault("manifest", source_url)

            build_professional_pdf(
                doc_dir=paths["root"],
                output_path=out_path,
                selected_pages=selected_pages,
                cover_title=cover_title,
                cover_curator=cover_curator,
                cover_description=cover_description,
                manifest_meta=meta_for_cover,
                transcription_json=transcription_json,
                mode=mode,
                compression=compression,
                source_url=source_url,
                cover_logo_bytes=cover_logo_bytes,
            )
        st.success(f"PDF generato: {out_path}")
        with suppress(OSError):
            st.download_button("⬇️ Scarica PDF", data=out_path.read_bytes(), file_name=out_path.name)
