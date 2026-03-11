from pathlib import Path

from PIL import Image

from universal_iiif_core.logic.downloader import PageDownloader


def test_resume_existing_scan_detects_valid_image(tmp_path, monkeypatch):
    """Test that _resume_existing_scan correctly identifies a valid existing image file."""
    # Create a small valid JPEG
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    img_path = temp_dir / "pag_0000.jpg"
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    img.save(img_path, format="JPEG")

    # Create a minimal mock downloader with required attributes
    class MockDownloader:
        def __init__(self, temp_dir):
            self.temp_dir = temp_dir
            self.logger = type("Logger", (), {"info": lambda self, m: None, "warning": lambda *a, **k: None})()
            self.cm = type("CM", (), {"get_setting": lambda self, k, d=None: d})()

        def _get_thumbnail_url(self, canvas):
            return None

    mock_downloader = MockDownloader(temp_dir)

    # Minimal canvas placeholder
    canvas = {"thumbnail": None}

    # Instantiate PageDownloader
    pd = PageDownloader(mock_downloader, canvas, index=0, folder=temp_dir)
    pd.filename = img_path  # Override to point at our test file

    res = pd._resume_existing_scan("http://example.invalid/image")
    assert res is not None
    fname, stats = res
    assert Path(fname).name == "pag_0000.jpg"
    assert stats.get("size_bytes", 0) > 0


def test_fetch_direct_only_skips_stitch_when_direct_download_fails(tmp_path):
    """Direct-only mode must not fall back to stitching."""

    class MockDownloader:
        def __init__(self, temp_dir):
            self.temp_dir = temp_dir
            self.logger = type("Logger", (), {"info": lambda self, m: None, "warning": lambda *a, **k: None})()
            self.cm = type(
                "CM",
                (),
                {
                    "get_setting": lambda self, key, default=None: {
                        "images.iiif_quality": "default",
                        "images.stitch_mode_default": "auto_fallback",
                    }.get(key, default)
                },
            )()
            self.force_redownload = True
            self.force_max_resolution = True
            self.stitch_mode = "direct_only"
            self.direct_calls = 0
            self.stitch_calls = 0

        def _get_thumbnail_url(self, _canvas):
            return None

        def _download_with_retries(self, *_args, **_kwargs):
            self.direct_calls += 1
            return None

        def _stitch_tiles_from_service(self, *_args, **_kwargs):
            self.stitch_calls += 1
            return ("unexpected", {})

    mock_downloader = MockDownloader(tmp_path)
    canvas = {"items": [{"items": [{"body": {"service": [{"id": "https://example.org/iiif/image"}]}}]}]}
    pd = PageDownloader(mock_downloader, canvas, index=0, folder=tmp_path)

    res = pd.fetch()

    assert res is None
    assert mock_downloader.direct_calls == 1
    assert mock_downloader.stitch_calls == 0


def test_fetch_stitch_only_skips_direct_attempts(tmp_path):
    """Stitch-only mode must bypass direct image URL attempts."""

    class MockDownloader:
        def __init__(self, temp_dir):
            self.temp_dir = temp_dir
            self.logger = type("Logger", (), {"info": lambda self, m: None, "warning": lambda *a, **k: None})()
            self.cm = type(
                "CM",
                (),
                {
                    "get_setting": lambda self, key, default=None: {
                        "images.iiif_quality": "default",
                        "images.stitch_mode_default": "auto_fallback",
                    }.get(key, default)
                },
            )()
            self.force_redownload = True
            self.force_max_resolution = False
            self.stitch_mode = "stitch_only"
            self.direct_calls = 0
            self.stitch_calls = 0

        def _get_thumbnail_url(self, _canvas):
            return None

        def _download_with_retries(self, *_args, **_kwargs):
            self.direct_calls += 1
            return ("unexpected", {})

        def _stitch_tiles_from_service(self, *_args, **_kwargs):
            self.stitch_calls += 1
            return ("stitched", {"download_method": "tile_stitch"})

    mock_downloader = MockDownloader(tmp_path)
    canvas = {"items": [{"items": [{"body": {"service": [{"id": "https://example.org/iiif/image"}]}}]}]}
    pd = PageDownloader(mock_downloader, canvas, index=0, folder=tmp_path)

    res = pd.fetch()

    assert res == ("stitched", {"download_method": "tile_stitch"})
    assert mock_downloader.direct_calls == 0
    assert mock_downloader.stitch_calls == 1
