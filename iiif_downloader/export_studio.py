from __future__ import annotations

import contextlib
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import pymupdf as fitz
from PIL import Image as PILImage


@dataclass(frozen=True)
class CompressionProfile:
    """Compression configuration including quality and resizing limits."""

    name: str
    max_long_edge_px: int | None
    jpeg_quality: int


COMPRESSION_PROFILES: dict[str, CompressionProfile] = {
    "High-Res": CompressionProfile("High-Res", None, 95),
    "Standard": CompressionProfile("Standard", 2600, 82),
    "Light": CompressionProfile("Light", 1500, 60),
}


_A4_W = 595
_A4_H = 842


def _truncate(s: str, max_len: int) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max(0, max_len - 1)].rstrip() + "…"


def _safe_meta_get(meta: dict[str, Any], *keys: str) -> str:
    for k in keys:
        v = meta.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""


def clean_filename(name: str) -> str:
    """Sanitize a string to be safe for use as a filename."""
    s = re.sub(r"\s+", "_", (name or "export").strip())
    s = re.sub(r"[^A-Za-z0-9._-]", "", s)
    return s or "export"


def _load_transcription_map(transcription_json: dict[str, Any] | None) -> dict[int, str]:
    if not transcription_json:
        return {}
    pages = transcription_json.get("pages") or []
    out: dict[int, str] = {}
    for p in pages:
        try:
            idx = int(p.get("page_index"))
        except (TypeError, ValueError):
            continue
        txt = p.get("full_text") or ""
        out[idx] = str(txt)
    return out


def _encode_jpeg_bytes(img: PILImage.Image, quality: int) -> bytes:
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=int(quality), optimize=True, progressive=True)
    return buf.getvalue()


def _prepare_image_bytes(image_path: Path, profile: CompressionProfile) -> tuple[bytes, tuple[int, int]]:
    img = PILImage.open(str(image_path))
    if img.mode != "RGB":
        img = img.convert("RGB")

    if profile.max_long_edge_px:
        w, h = img.size
        long_edge = max(w, h)
        if long_edge > profile.max_long_edge_px:
            scale = profile.max_long_edge_px / float(long_edge)
            new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            img = img.resize(new_size, PILImage.Resampling.LANCZOS)

    raw = _encode_jpeg_bytes(img, profile.jpeg_quality)
    return raw, img.size


def _add_cover_page(  # noqa: C901
    doc: fitz.Document,
    title: str,
    curator: str,
    description: str,
    meta: dict[str, Any],
    logo_bytes: bytes | None = None,
) -> None:
    page = doc.new_page(width=_A4_W, height=_A4_H)  # A4 points
    rect = page.rect

    # Visual style
    margin_x = 54
    top_band_h = 150
    accent = (0.18, 0.25, 0.35)  # muted blue/gray
    light_bg = (0.97, 0.98, 0.99)

    page.draw_rect(rect, color=None, fill=light_bg)
    page.draw_rect(fitz.Rect(0, 0, rect.width, top_band_h), color=None, fill=accent)
    page.draw_line(
        fitz.Point(margin_x, top_band_h + 18),
        fitz.Point(rect.width - margin_x, top_band_h + 18),
        color=(0.85, 0.85, 0.85),
        width=1,
    )

    institution = _safe_meta_get(meta, "attribution", "institution", "provider", "repository")
    shelfmark = _safe_meta_get(meta, "shelfmark", "id", "identifier")
    license_s = _safe_meta_get(meta, "license")
    source_url = _safe_meta_get(meta, "manifest", "source_url", "manifest_url")

    # Logo (optional)
    if logo_bytes:
        try:
            logo_rect = fitz.Rect(rect.width - margin_x - 120, 28, rect.width - margin_x, 28 + 80)
            page.insert_image(logo_rect, stream=logo_bytes, keep_proportion=True)
        except (OSError, ValueError, RuntimeError):
            # Non fatal: continue without logo
            pass

    # Title block
    title_text = title or _safe_meta_get(meta, "label", "title") or "Export Studio"
    page.insert_text(
        fitz.Point(margin_x, 58),
        _truncate(title_text, 90),
        fontsize=28,
        fontname="helv",
        color=(1, 1, 1),
    )

    subtitle = "Universal IIIF Downloader · PDF Export"
    page.insert_text(
        fitz.Point(margin_x, 92),
        subtitle,
        fontsize=11.5,
        fontname="helv",
        color=(0.92, 0.94, 0.97),
    )

    # Metadata summary (right under band)
    meta_y = top_band_h + 42
    left_col_w = 140
    rows: list[tuple[str, str]] = []
    if institution:
        rows.append(("Istituzione", institution))
    if shelfmark:
        rows.append(("Segnatura/ID", shelfmark))
    if license_s:
        rows.append(("Licenza", license_s))
    if source_url:
        rows.append(("Sorgente", source_url))

    if rows:
        page.insert_text(
            fitz.Point(margin_x, meta_y - 16), "Metadati", fontsize=13, fontname="helv", color=(0.2, 0.2, 0.2)
        )
        yy = meta_y
        for k, v in rows[:6]:
            page.insert_text(
                fitz.Point(margin_x, yy), f"{k}:", fontsize=10.5, fontname="helv", color=(0.25, 0.25, 0.25)
            )
            page.insert_textbox(
                fitz.Rect(margin_x + left_col_w, yy - 2, rect.width - margin_x, yy + 16),
                _truncate(v, 180),
                fontsize=10.5,
                fontname="helv",
                color=(0.12, 0.12, 0.12),
                align=0,
            )
            yy += 18

    # Curator / description
    body_top = meta_y + (len(rows[:6]) * 18) + 30
    if curator:
        page.insert_text(
            fitz.Point(margin_x, body_top), "Curatore / Note", fontsize=12.5, fontname="helv", color=(0.2, 0.2, 0.2)
        )
        page.insert_textbox(
            fitz.Rect(margin_x, body_top + 14, rect.width - margin_x, body_top + 70),
            curator,
            fontsize=11,
            fontname="helv",
            color=(0.12, 0.12, 0.12),
            align=0,
        )
        body_top += 78

    if description:
        page.insert_text(
            fitz.Point(margin_x, body_top), "Descrizione", fontsize=12.5, fontname="helv", color=(0.2, 0.2, 0.2)
        )
        page.insert_textbox(
            fitz.Rect(margin_x, body_top + 14, rect.width - margin_x, rect.height - 90),
            description,
            fontsize=11,
            fontname="helv",
            color=(0.12, 0.12, 0.12),
            align=0,
        )

    # Footer
    page.insert_text(
        fitz.Point(margin_x, rect.height - 50),
        f"Generato il {time.strftime('%Y-%m-%d')} · Universal IIIF Downloader",
        fontsize=9.5,
        fontname="helv",
        color=(0.45, 0.45, 0.45),
    )


def _add_colophon_page(
    doc: fitz.Document,
    source_url: str,
    profile: CompressionProfile,
    mode: str,
    selected_pages_count: int,
    images_added: int,
    original_bytes_total: int,
    encoded_bytes_total: int,
) -> None:
    page = doc.new_page(width=_A4_W, height=_A4_H)
    rect = page.rect

    def _mb(n: int) -> str:
        if n <= 0:
            return "0.00"
        return f"{n / (1024 * 1024):.2f}"

    ratio = None
    if original_bytes_total > 0:
        ratio = encoded_bytes_total / float(original_bytes_total)

    lines = [
        "Colophon",
        "",
        f"Generato il: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Profilo compressione: {profile.name}",
        f"JPEG quality: {profile.jpeg_quality}",
        f"Max long edge: {profile.max_long_edge_px or 'originale'} px",
        f"Modalità trascrizione: {mode}",
        f"Pagine richieste: {selected_pages_count}",
        f"Immagini inserite: {images_added}",
        f"Dimensione scans (totale): {_mb(original_bytes_total)} MB",
        f"Dimensione immagini (post): {_mb(encoded_bytes_total)} MB",
    ]
    if ratio is not None:
        lines.append(f"Rapporto (post/pre): {ratio:.2f}×")
    if source_url:
        lines.append(f"Sorgente IIIF: {source_url}")

    page.insert_textbox(
        fitz.Rect(72, 90, rect.width - 72, rect.height - 90),
        "\n".join(lines),
        fontsize=11,
        fontname="helv",
    )


def _add_image_page(
    doc: fitz.Document,
    img_bytes: bytes,
    visible_text: str,
    searchable_text: str,
    mode: str,
    page_label: str,
) -> None:
    page = doc.new_page(width=_A4_W, height=_A4_H)
    page_rect = page.rect

    # Reserve space for text if needed
    has_text = bool(visible_text) and mode in ("Testo a fronte",)
    text_height = 260 if has_text else 0

    img_rect = fitz.Rect(36, 44, page_rect.width - 36, page_rect.height - 36 - text_height)
    page.insert_image(img_rect, stream=img_bytes, keep_proportion=True)

    if page_label:
        page.insert_text(
            fitz.Point(36, 26),
            page_label,
            fontsize=9.5,
            fontname="helv",
            color=(0.45, 0.45, 0.45),
        )

    if mode == "Testo a fronte" and visible_text:
        text_rect = fitz.Rect(36, page_rect.height - 36 - text_height, page_rect.width - 36, page_rect.height - 36)
        tw = fitz.TextWriter(page_rect)
        tw.fill_textbox(
            text_rect,
            visible_text,
            font=fitz.Font("helv"),
            fontsize=9.5,
            align=0,
            warn=False,
        )
        tw.write_text(page, color=(0, 0, 0), render_mode=0)

    if mode == "PDF Ricercabile" and searchable_text:
        # Invisible-but-searchable text layer (render_mode=3).
        # Use TextWriter so we still write what fits instead of an all-or-nothing failure.
        tw = fitz.TextWriter(page_rect)
        tw.fill_textbox(
            fitz.Rect(36, 36, page_rect.width - 36, page_rect.height - 36),
            searchable_text,
            font=fitz.Font("helv"),
            fontsize=6.5,
            align=0,
            warn=False,
        )
        tw.write_text(page, color=(0, 0, 0), render_mode=3)


def _fits_text_in_box(
    box_rect: fitz.Rect, text: str, font: fitz.Font, fontsize: float
) -> bool:
    """Return True if the supplied text fits inside the provided rectangle."""
    rect = fitz.Rect(box_rect)
    tw = fitz.TextWriter(rect)
    try:
        tw.fill_textbox(
            rect,
            text,
            font=font,
            fontsize=fontsize,
            align=0,
            warn=False,
        )
        return True
    except ValueError:
        return False


def _split_chunk_at_boundary(text: str, length: int) -> tuple[str, str]:
    if length >= len(text):
        return text, ""
    cutoff = text.rfind("\n", 0, length)
    if cutoff >= 0:
        return text[: cutoff + 1], text[cutoff + 1 :]
    cutoff = text.rfind(" ", 0, length)
    if cutoff >= 0:
        return text[: cutoff + 1], text[cutoff + 1 :]
    return text[:length], text[length:]


def _slice_transcription_text(
    text: str, box_rect: fitz.Rect, font: fitz.Font, fontsize: float
) -> tuple[str, str]:
    if not text:
        return "", ""
    low, high, best = 1, len(text), 0
    while low <= high:
        mid = (low + high) // 2
        candidate = text[:mid]
        if _fits_text_in_box(box_rect, candidate, font, fontsize):
            best = mid
            low = mid + 1
        else:
            high = mid - 1

    if best == 0:
        best = min(1, len(text))

    chunk, remainder = _split_chunk_at_boundary(text, best)
    if not chunk:
        chunk, remainder = text[0], text[1:]
    return chunk, remainder


def _add_transcription_page(
    doc: fitz.Document,
    text: str,
    page_label: str,
    include_header: bool = True,
) -> None:
    if not (text or "").strip():
        # Keep the page intentionally minimal to avoid confusion.
        return

    font = fitz.Font("helv")
    fontsize = 11
    margin = 54
    remaining = text
    page_index = 0

    while remaining:
        page = doc.new_page(width=_A4_W, height=_A4_H)
        rect = page.rect
        content_top = 92 if include_header and page_index == 0 else 60
        has_header = include_header and page_index == 0

        if page_label:
            label = page_label if page_index == 0 else f"{page_label} (continua)"
            page.insert_text(
                fitz.Point(margin, 28),
                label,
                fontsize=9.5,
                fontname="helv",
                color=(0.45, 0.45, 0.45),
            )

        if has_header:
            page.insert_text(
                fitz.Point(margin, 60),
                "Trascrizione",
                fontsize=18,
                fontname="helv",
                color=(0.18, 0.18, 0.18),
            )
            page.draw_line(
                fitz.Point(margin, 72),
                fitz.Point(rect.width - margin, 72),
                color=(0.85, 0.85, 0.85),
                width=1,
            )

        text_area = fitz.Rect(margin, content_top, rect.width - margin, rect.height - margin)
        chunk, remaining = _slice_transcription_text(remaining, fitz.Rect(text_area), font, fontsize)
        if not chunk:
            break

        tw = fitz.TextWriter(rect)
        tw.fill_textbox(
            text_area,
            chunk,
            font=font,
            fontsize=fontsize,
            align=0,
            warn=False,
        )
        tw.write_text(page, color=(0.12, 0.12, 0.12), render_mode=0)

        page_index += 1


def build_professional_pdf(
    *,
    doc_dir: Path,
    output_path: Path,
    selected_pages: list[int],
    cover_title: str,
    cover_curator: str,
    cover_description: str,
    manifest_meta: dict[str, Any],
    transcription_json: dict[str, Any] | None,
    mode: str,
    compression: str,
    source_url: str,
    cover_logo_bytes: bytes | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> Path:
    """Assemble [Cover] + [Selected Pages] + [Colophon] into a single PDF.

    Page indices are 1-based.
    """
    profile = COMPRESSION_PROFILES.get(compression) or COMPRESSION_PROFILES["Standard"]
    trans_map = _load_transcription_map(transcription_json)

    scans_dir = doc_dir / "scans"
    if not scans_dir.exists():
        raise FileNotFoundError(f"Directory scans non trovata: {scans_dir}")

    if not selected_pages:
        raise ValueError("Nessuna pagina selezionata")

    doc = fitz.open()
    try:
        _add_cover_page(
            doc,
            cover_title,
            cover_curator,
            cover_description,
            manifest_meta or {},
            logo_bytes=cover_logo_bytes,
        )

        original_bytes_total = 0
        encoded_bytes_total = 0
        images_added = 0
        total_pages_to_process = len(selected_pages)

        for idx, page_idx in enumerate(selected_pages):
            if progress_callback:
                progress_callback(idx, total_pages_to_process)

            img_path = scans_dir / f"pag_{page_idx - 1:04d}.jpg"
            if not img_path.exists():
                continue

            img_bytes, _ = _prepare_image_bytes(img_path, profile)
            with contextlib.suppress(OSError):
                original_bytes_total += int(img_path.stat().st_size)

            encoded_bytes_total += len(img_bytes)
            images_added += 1
            page_text = trans_map.get(page_idx, "")

            page_label = f"Pag. {page_idx}"

            if mode == "Testo a fronte":
                # Facing-pages style: left scan page, right transcription page.
                _add_image_page(
                    doc,
                    img_bytes=img_bytes,
                    visible_text="",
                    searchable_text="",
                    mode="Solo immagini",
                    page_label=page_label,
                )
                _add_transcription_page(
                    doc,
                    text=page_text,
                    page_label=f"Trascrizione · Pag. {page_idx}",
                    include_header=True,
                )
                continue

            visible_text = page_text if mode == "Testo a fronte" else ""
            searchable_text = page_text if mode == "PDF Ricercabile" else ""

            _add_image_page(
                doc,
                img_bytes=img_bytes,
                visible_text=visible_text,
                searchable_text=searchable_text,
                mode=mode,
                page_label=page_label,
            )

        _add_colophon_page(
            doc,
            source_url=source_url,
            profile=profile,
            mode=mode,
            selected_pages_count=len(selected_pages),
            images_added=images_added,
            original_bytes_total=original_bytes_total,
            encoded_bytes_total=encoded_bytes_total,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path), garbage=4, deflate=True)
        return output_path
    finally:
        doc.close()
