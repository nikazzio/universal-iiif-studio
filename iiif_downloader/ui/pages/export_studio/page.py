from __future__ import annotations

from pathlib import Path
from typing import List

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


def _toggle_from_query_params(*, doc_key: str) -> None:
    toggle = st.query_params.get("export_toggle")
    if (
        toggle
        and isinstance(toggle, str)
        and not st.session_state.get(f"_export_toggle_done_{doc_key}", False)
    ):
        try:
            target_doc, target_p_s = toggle.split(":", 1)
            if target_doc == doc_key:
                target_p = int(target_p_s)
                k = f"export_page_{doc_key}_{target_p}"
                st.session_state[k] = not bool(st.session_state.get(k, False))
        except (ValueError, TypeError):
            pass

        try:
            del st.query_params["export_toggle"]
        except (KeyError, TypeError, AttributeError):
            pass

        st.session_state[f"_export_toggle_done_{doc_key}"] = True
        st.rerun()
    else:
        st.session_state[f"_export_toggle_done_{doc_key}"] = False


def _paginate(*, items: List[int], enabled: bool, page_size: int) -> List[int]:
    if not enabled:
        return items

    total = len(items)
    if total == 0:
        return items

    page_count = max(1, (total + page_size - 1) // page_size)
    page_index = st.number_input(
        "Pagina", min_value=1, max_value=page_count, value=1, step=1
    )
    start = (int(page_index) - 1) * page_size
    end = min(total, start + page_size)
    return items[start:end]


def render_export_studio_page() -> None:
    st.title("Export Studio")
    st.caption(
        "Crea un PDF professionale (frontespizio + pagine selezionate + colophon)."
    )

    thumb_max_edge = _get_int_setting(
        "thumbnails.max_long_edge_px", 320, min_v=120, max_v=900
    )
    thumb_jpeg_quality = _get_int_setting(
        "thumbnails.jpeg_quality", 70, min_v=30, max_v=95
    )
    thumb_columns = _get_int_setting("thumbnails.columns", 6, min_v=3, max_v=10)

    paginate_enabled = _get_bool_setting("thumbnails.paginate_enabled", True)
    page_size = _get_int_setting("thumbnails.page_size", 48, min_v=12, max_v=500)

    default_select_all = _get_bool_setting("thumbnails.default_select_all", True)

    hover_preview_enabled = _get_bool_setting("thumbnails.hover_preview_enabled", True)
    hover_preview_max_edge = _get_int_setting(
        "thumbnails.hover_preview_max_long_edge_px", 900, min_v=300, max_v=2000
    )
    hover_preview_jpeg_quality = _get_int_setting(
        "thumbnails.hover_preview_jpeg_quality", 82, min_v=30, max_v=95
    )
    hover_preview_delay_ms = _get_int_setting(
        "thumbnails.hover_preview_delay_ms", 550, min_v=0, max_v=3000
    )

    inline_base64_max_tiles = _get_int_setting(
        "thumbnails.inline_base64_max_tiles", 120, min_v=24, max_v=500
    )
    hover_preview_max_tiles = _get_int_setting(
        "thumbnails.hover_preview_max_tiles", 72, min_v=12, max_v=200
    )

    storage = OCRStorage()
    documents = storage.list_documents()
    if not documents:
        st.info("Nessun documento trovato. Scarica o importa un documento prima.")
        return

    options = []
    for d in documents:
        opt = load_document_option(storage, d)
        if opt:
            options.append(opt)

    if not options:
        st.info("Nessun documento valido trovato.")
        return

    selected_label = st.selectbox("Documento", [o.label for o in options])
    doc_opt = next(o for o in options if o.label == selected_label)

    paths = storage.get_document_paths(doc_opt.doc_id, doc_opt.library)
    scans_dir: Path = paths["scans"]

    if not scans_dir.exists():
        st.error(f"Scans non trovati: {scans_dir}")
        return

    available_pages = guess_available_pages(scans_dir)
    if not available_pages:
        st.warning("Nessuna immagine trovata in scans/.")
        return

    st.subheader("Frontespizio")
    col1, col2 = st.columns(2)
    with col1:
        cover_title = st.text_input(
            "Titolo", value=str(doc_opt.meta.get("label") or doc_opt.label)
        )
        cover_curator = st.text_input("Curatore / Note", value="")
    with col2:
        cover_description = st.text_area("Descrizione", value="", height=110)

    cover_logo = st.file_uploader(
        "Logo (opzionale)",
        type=["png", "jpg", "jpeg"],
        help="Carica un logo da mostrare sul frontespizio.",
    )
    cover_logo_bytes = cover_logo.read() if cover_logo is not None else None

    st.subheader("Opzioni PDF")
    compression = st.selectbox(
        "Compressione", list(COMPRESSION_PROFILES.keys()), index=1
    )
    mode = st.selectbox(
        "Trascrizione", ["Solo immagini", "Testo a fronte", "PDF Ricercabile"], index=0
    )

    st.subheader("Pagine")
    doc_key = f"{doc_opt.library}_{doc_opt.doc_id}".replace(" ", "_")
    thumbnails_dir = paths.get("thumbnails") or (paths["data"] / "thumbnails")

    _toggle_from_query_params(doc_key=doc_key)

    export_all_key = f"export_all_{doc_key}"
    export_all = st.checkbox(
        "📄 Esporta tutto il PDF",
        value=bool(st.session_state.get(export_all_key, False)),
        help="Se attivo, esporta tutte le pagine disponibili.",
    )
    st.session_state[export_all_key] = export_all

    action_pages = list(available_pages)
    total_tiles = len(action_pages)

    inline_enabled = total_tiles <= inline_base64_max_tiles
    if not inline_enabled:
        st.info(
            "Documento molto lungo: per performance si attiva la paginazione (limitando base64 inline). "
            f"Totale pagine: {total_tiles}"
        )

    effective_paginate = paginate_enabled or (not inline_enabled)
    visible_pages = _paginate(
        items=action_pages, enabled=effective_paginate, page_size=page_size
    )

    init_key = f"_export_init_{doc_key}"
    if default_select_all and not st.session_state.get(init_key, False):
        for p in action_pages:
            st.session_state[f"export_page_{doc_key}_{p}"] = True
        st.session_state[init_key] = True

    effective_hover = hover_preview_enabled and (total_tiles <= hover_preview_max_tiles)

    if export_all:
        selected_pages = action_pages
    else:
        selected_pages = render_thumbnail_grid(
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

    st.divider()

    out_dir = get_config_manager().get_downloads_dir() / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    default_name = clean_filename(
        f"{doc_opt.library}_{doc_opt.doc_id}_{compression}_{mode}.pdf"
    )
    out_name = st.text_input("Nome file PDF", value=default_name)

    if st.button(
        "📦 Genera PDF",
        type="primary",
        use_container_width=True,
        disabled=not bool(selected_pages),
    ):
        with st.spinner("Generazione PDF in corso..."):
            out_path = out_dir / out_name
            manifest_json = safe_read_json(paths["manifest"]) or {}
            transcription_json = safe_read_json(paths["transcription"])

            source_url = str(
                manifest_json.get("source_url")
                or manifest_json.get("manifest_url")
                or manifest_json.get("id")
                or manifest_json.get("@id")
                or doc_opt.meta.get("manifest")
                or doc_opt.meta.get("source_url")
                or ""
            )

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
        try:
            st.download_button(
                "⬇️ Scarica PDF", data=out_path.read_bytes(), file_name=out_path.name
            )
        except OSError:
            pass
