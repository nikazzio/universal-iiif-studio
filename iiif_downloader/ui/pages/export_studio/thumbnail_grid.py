from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from iiif_downloader.thumbnail_utils import ensure_hover_preview, ensure_thumbnail


def _selection_key(doc_key: str, page_num_1_based: int) -> str:
    return f"export_page_{doc_key}_{page_num_1_based}"


def _thumb_path(thumbnails_dir: Path, page_num_1_based: int) -> Path:
    return thumbnails_dir / f"thumb_{page_num_1_based - 1:04d}.jpg"


def _hover_path(thumbnails_dir: Path, page_num_1_based: int) -> Path:
    return thumbnails_dir / f"hover_{page_num_1_based - 1:04d}.jpg"


def _b64_data_url(img_path: Path) -> str | None:
    try:
        b = img_path.read_bytes()
        return "data:image/jpeg;base64," + base64.b64encode(b).decode("ascii")
    except OSError:
        return None


def _render_bulk_controls(*, doc_key: str, action_pages: list[int], disabled: bool) -> None:
    c1, c2, c3 = st.columns([1, 1, 1])
    if c1.button("✅ Tutte", disabled=disabled, width="stretch"):
        for p in action_pages:
            st.session_state[_selection_key(doc_key, p)] = True
        st.rerun()
    if c2.button("⬜ Nessuna", disabled=disabled, width="stretch"):
        for p in action_pages:
            st.session_state[_selection_key(doc_key, p)] = False
        st.rerun()
    if c3.button("🔄 Inverti", disabled=disabled, width="stretch"):
        for p in action_pages:
            k = _selection_key(doc_key, p)
            st.session_state[k] = not bool(st.session_state.get(k, False))
        st.rerun()


def _global_hover_css() -> None:
    st.markdown(
        """
        <style>
        /* CRITICAL: Ensure the column containing the hovered button
           is raised above subsequent columns (z-index trap) */
        div[data-testid="column"]:has(button:hover) {
            z-index: 10000 !important;
        }
        div.element-container:has(button:hover) {
            z-index: 10001 !important;
        }
        /* Ensure the button itself is high */
        div.stButton button:hover {
            z-index: 10002 !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )


def _render_tile(
    *,
    doc_key: str,
    page_num_1_based: int,
    scans_dir: Path,
    thumbnails_dir: Path,
    max_long_edge_px: int,
    jpeg_quality: int,
    hover_preview_enabled: bool,
    hover_preview_max_long_edge_px: int,
    hover_preview_jpeg_quality: int,
) -> bool:
    thumb = ensure_thumbnail(
        scans_dir=scans_dir,
        thumbnails_dir=thumbnails_dir,
        page_num_1_based=page_num_1_based,
        max_long_edge_px=max_long_edge_px,
        jpeg_quality=jpeg_quality,
    )
    if thumb is None:
        return False

    preview_path: Path | None = None
    if hover_preview_enabled:
        preview_path = ensure_hover_preview(
            scans_dir=scans_dir,
            thumbnails_dir=thumbnails_dir,
            page_num_1_based=page_num_1_based,
            max_long_edge_px=hover_preview_max_long_edge_px,
            jpeg_quality=hover_preview_jpeg_quality,
        )

    sel_key = _selection_key(doc_key, page_num_1_based)
    is_selected = bool(st.session_state.get(sel_key, False))

    thumb_url = _b64_data_url(thumb)
    if not thumb_url:
        return False

    preview_url = _b64_data_url(preview_path) if preview_path is not None else None
    if not preview_url:
        preview_url = thumb_url

    def _on_toggle(doc_key: str = doc_key, p: int = page_num_1_based) -> None:
        k = _selection_key(doc_key, p)
        st.session_state[k] = not bool(st.session_state.get(k, False))

    safe_key = doc_key.replace(".", "_").replace(" ", "_").replace("/", "_")
    tile_id = f"tile-{safe_key}-{page_num_1_based}"

    selected_style = ""
    if is_selected:
        selected_style = """
            border-color: rgba(255, 75, 75, 0.95) !important;
            box-shadow: 0 0 0 2px rgba(255, 75, 75, 0.18) inset, 0 10px 28px rgba(0,0,0,0.14);
        """

    tile_css = f"""
    <style>
    div:has(span.{tile_id}) + div button {{
        background-image: url("{thumb_url}");
        background-repeat: no-repeat;
        background-position: center;
        background-size: cover;
        color: transparent !important;
        height: 240px; /* fallback height */
        aspect-ratio: 3/4 !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
        border-radius: 8px;
        transition: transform 0.1s, box-shadow 0.1s;
        {selected_style}
    }}
    div:has(span.{tile_id}) + div button:hover {{
        transform: scale(1.02);
        border-color: rgba(0,0,0,0.3) !important;
        z-index: 10;
    }}
    div:has(span.{tile_id}) + div button:active {{
        transform: scale(0.98);
    }}
    /* Hover Preview */
    div:has(span.{tile_id}) + div button:hover::after {{
        content: "";
        position: absolute;
        left: 50%;
        bottom: 100%;
        transform: translate(-50%, -10px);
        width: 400px;
        height: 560px;
        background-image: url("{preview_url}");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        background-color: white;
        border: 1px solid #ddd;
        border-radius: 8px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.35);
        z-index: 99999;
        pointer-events: none;
    }}
    </style>
    <span class="{tile_id}" style="display:none"></span>
    """

    st.markdown(tile_css, unsafe_allow_html=True)
    st.button(
        "Select",
        key=f"btn_{doc_key}_{page_num_1_based}",
        on_click=_on_toggle,
        width="stretch",
    )
    badge_icon = "✅" if is_selected else "⬜"
    st.caption(f"{badge_icon} Pag. {page_num_1_based}")
    return True


def render_thumbnail_grid(
    *,
    doc_key: str,
    pages: list[int],
    action_pages: list[int],
    scans_dir: Path,
    thumbnails_dir: Path,
    columns: int = 6,
    max_long_edge_px: int = 320,
    jpeg_quality: int = 70,
    hover_preview_enabled: bool = True,
    hover_preview_max_long_edge_px: int = 900,
    hover_preview_jpeg_quality: int = 82,
    hover_preview_delay_ms: int = 550,
    disabled: bool = False,
) -> list[int]:
    """Render a reliable Streamlit-native thumbnail grid.

    This intentionally avoids injected HTML/JS and URL query-params toggling.
    Click behavior stays stable across Streamlit versions.
    """
    st.caption("Seleziona le pagine (click sull'immagine).")

    _render_bulk_controls(doc_key=doc_key, action_pages=action_pages, disabled=disabled)

    missing_thumbs = sum(1 for p in pages if not _thumb_path(thumbnails_dir, p).exists())
    missing_hovers = 0
    if hover_preview_enabled:
        missing_hovers = sum(1 for p in pages if not _hover_path(thumbnails_dir, p).exists())

    show_progress = (missing_thumbs + missing_hovers) > 0
    status_ph = st.empty() if show_progress else None
    progress_ph = st.empty() if show_progress else None

    cols_n = max(1, int(columns or 1))

    grid_cols = st.columns(cols_n)
    _global_hover_css()

    # We collect all per-tile styles to inject them in a batch if possible,
    # but Streamlit columns are rendered imperatively. We will inject one style block per tile.
    # It's not the most efficient but it's reliable for correct targeting.

    total = max(1, len(pages))
    for i, p in enumerate(pages, start=1):
        if show_progress and status_ph is not None and progress_ph is not None:
            status_ph.info(
                f"Generazione thumbnails… {i}/{total} (mancanti: thumb={missing_thumbs}, preview={missing_hovers})"
            )
            progress_ph.progress(min(1.0, i / float(total)))

        with grid_cols[(i - 1) % cols_n]:
            _render_tile(
                doc_key=doc_key,
                page_num_1_based=p,
                scans_dir=scans_dir,
                thumbnails_dir=thumbnails_dir,
                max_long_edge_px=max_long_edge_px,
                jpeg_quality=jpeg_quality,
                hover_preview_enabled=hover_preview_enabled,
                hover_preview_max_long_edge_px=hover_preview_max_long_edge_px,
                hover_preview_jpeg_quality=hover_preview_jpeg_quality,
            )

    if show_progress and status_ph is not None and progress_ph is not None:
        status_ph.empty()
        progress_ph.empty()

    return [p for p in action_pages if bool(st.session_state.get(_selection_key(doc_key, p), False))]
