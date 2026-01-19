from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PIL import Image as PILImage


def _cached_image_matches_target(*, img_path: Path, target_long_edge: int) -> bool:
    """Return True if cached image is plausibly produced with target settings.

    We don't encode settings in filenames; instead we validate dimensions.
    Regenerate if the cached image is clearly too small or too large.
    """

    if target_long_edge <= 0:
        return True
    try:
        with PILImage.open(str(img_path)) as img:
            w, h = img.size
        long_edge = max(int(w), int(h))
    except (OSError, ValueError):
        return False

    # Accept small rounding differences and small originals.
    if long_edge <= target_long_edge and long_edge >= int(target_long_edge * 0.85):
        return True
    if abs(long_edge - target_long_edge) <= 2:
        return True
    return False


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
        if out_path.exists() and _cached_image_matches_target(
            img_path=out_path, target_long_edge=int(max_long_edge_px)
        ):
            return out_path
        if out_path.exists():
            try:
                out_path.unlink()
            except OSError:
                pass

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
        if out_path.exists() and _cached_image_matches_target(
            img_path=out_path, target_long_edge=int(max_long_edge_px)
        ):
            return out_path
        if out_path.exists():
            try:
                out_path.unlink()
            except OSError:
                pass

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
