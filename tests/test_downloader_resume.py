from pathlib import Path

from PIL import Image

from universal_iiif_core.logic.downloader import IIIFDownloader


def test_resume_existing_scan_detects_valid_image(tmp_path, monkeypatch):
    """Test that _resume_existing_scan correctly identifies a valid existing image file."""
    # Create a small valid JPEG
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    img_path = temp_dir / "pag_0000.jpg"
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    img.save(img_path, format="JPEG")

    # Instantiate downloader with harmless manifest_url and output_dir
    # Prevent network call to fetch manifest by patching the symbol imported into downloader
    import universal_iiif_core.logic.downloader as dl_mod

    monkeypatch.setattr(dl_mod, "get_json", lambda url: {})

    d = IIIFDownloader(
        manifest_url="http://example.invalid/manifest.json", output_dir=str(tmp_path), output_name="testdoc"
    )
    # Force temp_dir to our test folder
    d.temp_dir = temp_dir

    # Minimal canvas placeholder
    canvas = {"thumbnail": None}

    res = d._resume_existing_scan(img_path, base_url="", canvas=canvas, index=0)
    assert res is not None
    fname, stats = res
    assert Path(fname).name == "pag_0000.jpg"
    assert stats.get("size_bytes", 0) > 0
