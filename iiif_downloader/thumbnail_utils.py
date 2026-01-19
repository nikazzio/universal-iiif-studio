from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PIL import Image as PILImage


def guess_available_pages(scans_dir: Path) -> List[int]:
    """Return available 1-based page numbers from pag_XXXX.jpg files."""

    pages: List[int] = []
    for p in sorted(scans_dir.glob("pag_*.jpg")):
        stem = p.stem
        try:
            idx0 = int(stem.split("_")[-1])
        except (ValueError, IndexError):
            continue
        pages.append(idx0 + 1)
    return pages


def thumbnail_path(thumbnails_dir: Path, page_num_1_based: int) -> Path:
    return thumbnails_dir / f"thumb_{page_num_1_based - 1:04d}.jpg"


def hover_preview_path(thumbnails_dir: Path, page_num_1_based: int) -> Path:
    return thumbnails_dir / f"hover_{page_num_1_based - 1:04d}.jpg"


def ensure_thumbnail(
    *,
    scans_dir: Path,
    thumbnails_dir: Path,
    page_num_1_based: int,
    max_long_edge_px: int = 320,
    jpeg_quality: int = 70,
) -> Optional[Path]:
    """Create (if missing) and return cached thumbnail path for a page.

    - Reads: scans_dir/pag_XXXX.jpg (0-based file index)
    - Writes: thumbnails_dir/thumb_XXXX.jpg (0-based file index)
    """

    try:
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        out_path = thumbnail_path(thumbnails_dir, page_num_1_based)
        if out_path.exists():
            return out_path

        scan_path = scans_dir / f"pag_{page_num_1_based - 1:04d}.jpg"
        if not scan_path.exists():
            return None

        img = PILImage.open(str(scan_path))
        if img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        long_edge = max(w, h)
        if long_edge > max_long_edge_px:
            scale = max_long_edge_px / float(long_edge)
            new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            img = img.resize(new_size, PILImage.Resampling.LANCZOS)

        img.save(str(out_path), format="JPEG", quality=int(jpeg_quality), optimize=True, progressive=True)
        return out_path
    except (OSError, ValueError):
        return None


def ensure_hover_preview(
    *,
    scans_dir: Path,
    thumbnails_dir: Path,
    page_num_1_based: int,
    max_long_edge_px: int = 900,
    jpeg_quality: int = 82,
) -> Optional[Path]:
    """Create (if missing) and return a cached hover preview for a page.

    This is intentionally larger than thumbnails, but smaller than the original scans,
    so it can be embedded in the UI for hover previews.
    """

    try:
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        out_path = hover_preview_path(thumbnails_dir, page_num_1_based)
        if out_path.exists():
            return out_path

        scan_path = scans_dir / f"pag_{page_num_1_based - 1:04d}.jpg"
        if not scan_path.exists():
            return None

        img = PILImage.open(str(scan_path))
        if img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        long_edge = max(w, h)
        if long_edge > max_long_edge_px:
            scale = max_long_edge_px / float(long_edge)
            new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            img = img.resize(new_size, PILImage.Resampling.LANCZOS)

        img.save(str(out_path), format="JPEG", quality=int(jpeg_quality), optimize=True, progressive=True)
        return out_path
    except (OSError, ValueError):
        return None
