"""Tests for universal_iiif_core.logic.downloader_pdf — PDF download methods."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from universal_iiif_core.logic.downloader_pdf import (
    _determine_pdf_output_path,
    _load_logo_bytes,
    _should_create_pdf_from_images,
    _should_prefer_native_pdf,
    _clear_existing_scans,
    _collect_scan_stats,
)


def _make_downloader_stub(tmp_path: Path, **overrides):
    """Create a minimal object that looks like IIIFDownloader for method testing."""
    scans_dir = tmp_path / "scans"
    scans_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir = tmp_path / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    output_path = tmp_path / "output.pdf"

    cm = SimpleNamespace(
        get_setting=lambda key, default=None: overrides.get(f"setting.{key}", default)
    )

    stub = SimpleNamespace(
        scans_dir=scans_dir,
        pdf_dir=pdf_dir,
        output_path=output_path,
        ms_id="test_ms",
        cm=cm,
        prefer_images=overrides.get("prefer_images", False),
        logger=MagicMock(),
        get_pdf_url=lambda: overrides.get("pdf_url", None),
    )
    return stub


def test_determine_pdf_output_path_default(tmp_path: Path):
    """Default output path when no existing PDF."""
    stub = _make_downloader_stub(tmp_path)
    result = _determine_pdf_output_path(stub)
    assert result == stub.output_path


def test_determine_pdf_output_path_compiled_suffix(tmp_path: Path):
    """When PDF already exists and has a URL, use _compiled suffix."""
    stub = _make_downloader_stub(tmp_path, pdf_url="https://example.com/doc.pdf")
    stub.output_path.write_bytes(b"%PDF-fake")
    result = _determine_pdf_output_path(stub)
    assert "_compiled.pdf" in result.name


def test_load_logo_bytes_returns_none_for_empty_path(tmp_path: Path):
    """Empty logo path should return None."""
    stub = _make_downloader_stub(tmp_path)
    assert _load_logo_bytes(stub, "") is None


def test_load_logo_bytes_returns_none_for_missing_file(tmp_path: Path):
    """Missing logo file should return None."""
    stub = _make_downloader_stub(tmp_path)
    assert _load_logo_bytes(stub, "/nonexistent/logo.png") is None


def test_load_logo_bytes_reads_existing_file(tmp_path: Path):
    """Existing logo file should return its bytes."""
    stub = _make_downloader_stub(tmp_path)
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"PNG-DATA")
    result = _load_logo_bytes(stub, str(logo))
    assert result == b"PNG-DATA"


def test_should_prefer_native_pdf_default(tmp_path: Path):
    """Default config should prefer native PDF."""
    stub = _make_downloader_stub(tmp_path, **{"setting.pdf.prefer_native_pdf": True})
    assert _should_prefer_native_pdf(stub) is True


def test_should_prefer_native_pdf_disabled_by_prefer_images(tmp_path: Path):
    """prefer_images flag should override native PDF preference."""
    stub = _make_downloader_stub(tmp_path, prefer_images=True)
    stub.prefer_images = True
    assert _should_prefer_native_pdf(stub) is False


def test_should_create_pdf_from_images_default(tmp_path: Path):
    """Default config should not auto-create PDF from images."""
    stub = _make_downloader_stub(tmp_path, **{"setting.pdf.create_pdf_from_images": False})
    assert _should_create_pdf_from_images(stub) is False


def test_should_create_pdf_from_images_enabled(tmp_path: Path):
    """Enabled config should return True."""
    stub = _make_downloader_stub(tmp_path, **{"setting.pdf.create_pdf_from_images": True})
    assert _should_create_pdf_from_images(stub) is True


def test_clear_existing_scans(tmp_path: Path):
    """Should remove all pag_*.jpg files from scans_dir."""
    stub = _make_downloader_stub(tmp_path)
    from PIL import Image

    for i in range(3):
        img = Image.new("RGB", (10, 10))
        img.save(stub.scans_dir / f"pag_{i:04d}.jpg")
    # Also add a non-scan file that should NOT be removed
    (stub.scans_dir / "manifest.json").write_text("{}")

    _clear_existing_scans(stub)

    remaining = list(stub.scans_dir.glob("pag_*.jpg"))
    assert len(remaining) == 0
    assert (stub.scans_dir / "manifest.json").exists()


def test_collect_scan_stats(tmp_path: Path):
    """Should gather size/dimension stats for each scan file."""
    stub = _make_downloader_stub(tmp_path)
    from PIL import Image

    for i in range(2):
        img = Image.new("RGB", (3000, 2000))
        img.save(stub.scans_dir / f"pag_{i:04d}.jpg")

    stats = _collect_scan_stats(stub, "https://example.com/scan")
    assert len(stats) == 2
    assert stats[0]["page_index"] == 0
    assert stats[0]["width"] == 3000
    assert stats[0]["height"] == 2000
    assert stats[0]["resolution_category"] == "High"
    assert stats[0]["original_url"] == "https://example.com/scan"
