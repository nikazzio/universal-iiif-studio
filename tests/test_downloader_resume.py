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
