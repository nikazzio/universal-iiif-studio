from pathlib import Path

from PIL import Image as PILImage

from iiif_downloader.thumbnail_utils import ensure_thumbnail, guess_available_pages


def test_guess_available_pages(tmp_path: Path) -> None:
    scans = tmp_path / "scans"
    scans.mkdir(parents=True)

    PILImage.new("RGB", (10, 10), color=(255, 0, 0)).save(scans / "pag_0000.jpg")
    PILImage.new("RGB", (10, 10), color=(255, 0, 0)).save(scans / "pag_0002.jpg")

    assert guess_available_pages(scans) == [1, 3]


def test_ensure_thumbnail_resizes_and_caches(tmp_path: Path) -> None:
    scans = tmp_path / "scans"
    thumbs = tmp_path / "data" / "thumbnails"
    scans.mkdir(parents=True)

    # Create a large scan
    PILImage.new("RGB", (2000, 1000), color=(0, 255, 0)).save(scans / "pag_0000.jpg")

    thumb1 = ensure_thumbnail(
        scans_dir=scans,
        thumbnails_dir=thumbs,
        page_num_1_based=1,
        max_long_edge_px=320,
        jpeg_quality=70,
    )
    assert thumb1 is not None
    assert thumb1.exists()

    img = PILImage.open(str(thumb1))
    w, h = img.size
    assert max(w, h) <= 320

    # Second call should use cache (file still exists)
    thumb2 = ensure_thumbnail(
        scans_dir=scans,
        thumbnails_dir=thumbs,
        page_num_1_based=1,
        max_long_edge_px=320,
        jpeg_quality=70,
    )
    assert thumb2 == thumb1


def test_ensure_thumbnail_regenerates_when_size_changes(tmp_path: Path) -> None:
    scans = tmp_path / "scans"
    thumbs = tmp_path / "data" / "thumbnails"
    scans.mkdir(parents=True)

    # Create a large scan so different target sizes are meaningful.
    PILImage.new("RGB", (2000, 1000), color=(0, 255, 0)).save(scans / "pag_0000.jpg")

    thumb_small = ensure_thumbnail(
        scans_dir=scans,
        thumbnails_dir=thumbs,
        page_num_1_based=1,
        max_long_edge_px=320,
        jpeg_quality=70,
    )
    assert thumb_small is not None

    with PILImage.open(str(thumb_small)) as img:
        assert max(img.size) <= 320

    # Ask for a bigger thumbnail: should regenerate from scan, not keep the old cached one.
    thumb_big = ensure_thumbnail(
        scans_dir=scans,
        thumbnails_dir=thumbs,
        page_num_1_based=1,
        max_long_edge_px=640,
        jpeg_quality=70,
    )
    assert thumb_big == thumb_small
    with PILImage.open(str(thumb_big)) as img:
        assert max(img.size) <= 640
        assert max(img.size) > 320
