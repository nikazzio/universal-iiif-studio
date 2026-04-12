"""Extended tests for universal_iiif_core.thumbnail_utils — hover previews and edge cases."""

from __future__ import annotations

from pathlib import Path

from PIL import Image as PILImage

from universal_iiif_core.thumbnail_utils import (
    ensure_hover_preview,
    ensure_thumbnail,
    hover_preview_path,
    thumbnail_path,
)


def _create_scan(scans_dir: Path, page_0based: int, size: tuple[int, int] = (2000, 1500)) -> Path:
    """Helper to create a scan file."""
    scans_dir.mkdir(parents=True, exist_ok=True)
    path = scans_dir / f"pag_{page_0based:04d}.jpg"
    PILImage.new("RGB", size, color=(100, 150, 200)).save(path, format="JPEG")
    return path


def test_thumbnail_path_computation():
    """Thumbnail path should follow pag_XXXX.jpg naming (0-based)."""
    base = Path("/tmp/thumbs")
    assert thumbnail_path(base, 1) == base / "thumb_0000.jpg"
    assert thumbnail_path(base, 10) == base / "thumb_0009.jpg"


def test_hover_preview_path_computation():
    """Hover preview path should follow hover_XXXX.jpg naming."""
    base = Path("/tmp/thumbs")
    assert hover_preview_path(base, 1) == base / "hover_0000.jpg"
    assert hover_preview_path(base, 5) == base / "hover_0004.jpg"


def test_ensure_thumbnail_missing_scan_returns_none(tmp_path: Path):
    """Missing scan file should return None without crashing."""
    result = ensure_thumbnail(
        scans_dir=tmp_path / "scans",
        thumbnails_dir=tmp_path / "thumbs",
        page_num_1_based=1,
    )
    assert result is None


def test_ensure_hover_preview_creates_larger_image(tmp_path: Path):
    """Hover preview should be larger than thumbnail for same source."""
    scans = tmp_path / "scans"
    thumbs = tmp_path / "thumbs"
    _create_scan(scans, 0, size=(3000, 2000))

    thumb = ensure_thumbnail(
        scans_dir=scans, thumbnails_dir=thumbs, page_num_1_based=1, max_long_edge_px=320
    )
    hover = ensure_hover_preview(
        scans_dir=scans, thumbnails_dir=thumbs, page_num_1_based=1, max_long_edge_px=900
    )

    assert thumb is not None and hover is not None
    assert thumb.exists() and hover.exists()

    with PILImage.open(str(thumb)) as t, PILImage.open(str(hover)) as h:
        assert max(h.size) > max(t.size)
        assert max(h.size) <= 900


def test_ensure_hover_preview_missing_scan_returns_none(tmp_path: Path):
    """Missing scan should return None for hover preview."""
    result = ensure_hover_preview(
        scans_dir=tmp_path / "scans",
        thumbnails_dir=tmp_path / "thumbs",
        page_num_1_based=1,
    )
    assert result is None


def test_ensure_hover_preview_uses_cache(tmp_path: Path):
    """Second call should hit cache when source hasn't changed."""
    scans = tmp_path / "scans"
    thumbs = tmp_path / "thumbs"
    _create_scan(scans, 0)

    first = ensure_hover_preview(scans_dir=scans, thumbnails_dir=thumbs, page_num_1_based=1)
    assert first is not None
    first_mtime = first.stat().st_mtime_ns

    second = ensure_hover_preview(scans_dir=scans, thumbnails_dir=thumbs, page_num_1_based=1)
    assert second is not None
    assert second.stat().st_mtime_ns == first_mtime


def test_ensure_thumbnail_small_source_no_resize(tmp_path: Path):
    """Source smaller than target should not be upscaled."""
    scans = tmp_path / "scans"
    thumbs = tmp_path / "thumbs"
    _create_scan(scans, 0, size=(200, 150))

    result = ensure_thumbnail(
        scans_dir=scans, thumbnails_dir=thumbs, page_num_1_based=1, max_long_edge_px=320
    )
    assert result is not None
    with PILImage.open(str(result)) as img:
        assert max(img.size) == 200
