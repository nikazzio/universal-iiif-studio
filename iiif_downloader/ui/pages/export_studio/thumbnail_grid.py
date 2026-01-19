from __future__ import annotations

import base64
import html
import textwrap
from pathlib import Path
from typing import List, Optional

import streamlit as st

from iiif_downloader.thumbnail_utils import ensure_hover_preview, ensure_thumbnail


def _build_css(*, columns: int, hover_preview_delay_ms: int) -> str:
    tile_w_pct = max(10, min(100, int(100 / max(1, columns))))
    delay_ms = max(0, int(hover_preview_delay_ms or 0))

    css = textwrap.dedent(
        f"""
<style>
  .uidl-grid {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: flex-start;
  }}
  .uidl-tile {{
    width: calc({tile_w_pct}% - 10px);
    min-width: 120px;
    max-width: 240px;
  }}
  .uidl-a {{
    display: block;
    text-decoration: none;
    color: inherit;
    border: 1px solid rgba(0,0,0,0.10);
    border-radius: 8px;
    overflow: visible;
    position: relative;
    background: rgba(255,255,255,0.78);
  }}
  .uidl-a.selected {{
    border-color: rgba(255, 75, 75, 0.92);
    box-shadow: 0 0 0 1px rgba(255, 75, 75, 0.22) inset;
  }}
  .uidl-img {{
    width: 100%;
    height: auto;
    display: block;
    border-radius: 8px 8px 0 0;
  }}
  .uidl-label {{
    padding: 5px 8px;
    font-size: 0.9rem;
    color: rgba(0,0,0,0.75);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(255,255,255,0.85);
    border-top: 1px solid rgba(0,0,0,0.06);
    border-radius: 0 0 8px 8px;
  }}
  .uidl-badge {{
    font-size: 0.8rem;
    padding: 1px 8px;
    border-radius: 999px;
    border: 1px solid rgba(0,0,0,0.10);
    background: rgba(0,0,0,0.03);
    white-space: nowrap;
  }}

  /* Hover preview: anchored to each tile (no fullscreen), sized proportionally */
  .uidl-preview {{
    position: absolute;
    left: 50%;
    top: calc(100% + 8px);
    transform: translateX(-50%);
    z-index: 50;
    width: min(42vw, 420px);
    max-width: 420px;
    background: rgba(255,255,255,0.98);
    border: 1px solid rgba(0,0,0,0.18);
    border-radius: 10px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.22);
    padding: 6px;
    opacity: 0;
    visibility: hidden;
    transition: opacity 140ms ease;
    transition-delay: {delay_ms}ms;
    pointer-events: none;
  }}
  .uidl-preview img {{
    width: 100%;
    height: auto;
    max-height: 60vh;
    object-fit: contain;
    display: block;
    border-radius: 8px;
  }}
  .uidl-a:hover .uidl-preview {{
    opacity: 1;
    visibility: visible;
  }}
  @media (prefers-reduced-motion: reduce) {{
    .uidl-preview {{ transition: none; }}
  }}
</style>
"""
    ).strip()

    # IMPORTANT: css must not start with indentation/newlines.
    return css


def _build_tile_html(
    *,
    href: str,
    thumb_url: str,
    preview_url: Optional[str],
    page_num: int,
    is_selected: bool,
) -> str:
    selected_cls = " selected" if is_selected else ""
    badge = "Selez." if is_selected else ""
    check = "✅" if is_selected else "⬜"

    safe_href = html.escape(href, quote=True)

    preview_html = ""
    if preview_url:
        # Keep HTML flat: leading indentation/newlines can make Streamlit render
        # HTML as Markdown code blocks.
        preview_html = (
            f'<div class="uidl-preview"><img src="{preview_url}" alt="preview"/></div>'
        )

    tile_html = (
        '<div class="uidl-tile">'
        f'<a class="uidl-a{selected_cls}" href="{safe_href}">'
        f'<img class="uidl-img" src="{thumb_url}" alt="thumb"/>'
        f"{preview_html}"
        '<div class="uidl-label">'
        f"<div>Pag. {page_num}</div>"
        f'<div class="uidl-badge">{check} {badge}</div>'
        "</div>"
        "</a>"
        "</div>"
    )

    return tile_html


def render_thumbnail_grid(
    *,
    doc_key: str,
    pages: List[int],
    action_pages: List[int],
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
) -> List[int]:
    st.caption("Seleziona le pagine (griglia thumbnails).")

    c1, c2, c3 = st.columns([1, 1, 1])
    if c1.button("✅ Tutte", disabled=disabled, use_container_width=True):
        for p in action_pages:
            st.session_state[f"export_page_{doc_key}_{p}"] = True
        st.rerun()
    if c2.button("⬜ Nessuna", disabled=disabled, use_container_width=True):
        for p in action_pages:
            st.session_state[f"export_page_{doc_key}_{p}"] = False
        st.rerun()
    if c3.button("🔄 Inverti", disabled=disabled, use_container_width=True):
        for p in action_pages:
            k = f"export_page_{doc_key}_{p}"
            st.session_state[k] = not bool(st.session_state.get(k, False))
        st.rerun()

    def _b64_data_url(img_path: Path) -> Optional[str]:
        try:
            b = img_path.read_bytes()
            return "data:image/jpeg;base64," + base64.b64encode(b).decode("ascii")
        except OSError:
            return None

    css = _build_css(columns=columns, hover_preview_delay_ms=hover_preview_delay_ms)

    tiles_html: List[str] = []
    for p in pages:
        thumb = ensure_thumbnail(
            scans_dir=scans_dir,
            thumbnails_dir=thumbnails_dir,
            page_num_1_based=p,
            max_long_edge_px=max_long_edge_px,
            jpeg_quality=jpeg_quality,
        )
        if thumb is None:
            continue

        preview_path = None
        if hover_preview_enabled:
            preview_path = ensure_hover_preview(
                scans_dir=scans_dir,
                thumbnails_dir=thumbnails_dir,
                page_num_1_based=p,
                max_long_edge_px=hover_preview_max_long_edge_px,
                jpeg_quality=hover_preview_jpeg_quality,
            )
        if preview_path is None:
            preview_path = thumb

        thumb_url = _b64_data_url(thumb)
        preview_url = _b64_data_url(preview_path)
        if not thumb_url:
            continue

        href = f"?export_toggle={doc_key}:{p}"
        k = f"export_page_{doc_key}_{p}"
        is_selected = bool(st.session_state.get(k, False))

        tile_html = _build_tile_html(
            href=href,
            thumb_url=thumb_url,
            preview_url=preview_url,
            page_num=p,
            is_selected=is_selected,
        )
        tiles_html.append(tile_html)

    if tiles_html:
        st.markdown(
            css + '<div class="uidl-grid">' + "\n".join(tiles_html) + "</div>",
            unsafe_allow_html=True,
        )

    return [
        p
        for p in action_pages
        if bool(st.session_state.get(f"export_page_{doc_key}_{p}", False))
    ]
