from __future__ import annotations

from pathlib import Path

import universal_iiif_core.logic.downloader as downloader_module
from universal_iiif_core.logic.downloader import IIIFDownloader


class _DummyLogger:
    def info(self, *args, **kwargs):  # noqa: D401
        pass

    def warning(self, *args, **kwargs):  # noqa: D401
        pass

    def debug(self, *args, **kwargs):  # noqa: D401
        pass

    def error(self, *args, **kwargs):  # noqa: D401
        pass


class _DummyVault:
    def upsert_manuscript(self, *args, **kwargs):  # noqa: D401
        pass

    def update_status(self, *args, **kwargs):  # noqa: D401
        pass

    def update_download_job(self, *args, **kwargs):  # noqa: D401
        pass


def _build_downloader(
    monkeypatch,
    tmp_path: Path,
    manifest: dict,
    *,
    prefer_native_pdf: bool,
    create_pdf_from_images: bool,
) -> IIIFDownloader:
    monkeypatch.setattr(downloader_module, "get_json", lambda _url: manifest)
    monkeypatch.setattr(downloader_module, "get_download_logger", lambda _ms: _DummyLogger())
    monkeypatch.setattr(downloader_module, "VaultManager", _DummyVault)

    downloader = IIIFDownloader(
        "https://example.org/manifest.json",
        output_dir=tmp_path,
        library="Library",
        output_folder_name="DocA",
    )
    monkeypatch.setattr(downloader, "_should_prefer_native_pdf", lambda: prefer_native_pdf)
    monkeypatch.setattr(downloader, "_should_create_pdf_from_images", lambda: create_pdf_from_images)
    return downloader


def _manifest_with_native_pdf() -> dict:
    return {
        "label": "Test manuscript",
        "rendering": [{"id": "https://example.org/native.pdf", "format": "application/pdf"}],
        "items": [{"id": "canvas-1"}],
    }


def _manifest_without_native_pdf() -> dict:
    return {
        "label": "Test manuscript",
        "items": [{"id": "canvas-1"}],
    }


def test_native_pdf_priority_skips_canvas_download(monkeypatch, tmp_path: Path):
    downloader = _build_downloader(
        monkeypatch,
        tmp_path,
        _manifest_with_native_pdf(),
        prefer_native_pdf=True,
        create_pdf_from_images=False,
    )
    monkeypatch.setattr(downloader, "download_native_pdf", lambda _url: True)

    def _fake_extract(_pdf_path: Path, progress_callback=None):
        scan = downloader.scans_dir / "pag_0000.jpg"
        scan.write_bytes(b"fake-image")
        return True

    monkeypatch.setattr(downloader, "_extract_pages_from_pdf", _fake_extract)
    monkeypatch.setattr(
        downloader,
        "_download_canvases",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Canvas fallback should not run")),
    )

    pdf_from_images_called: list[bool] = []
    monkeypatch.setattr(downloader, "create_pdf", lambda files=None: pdf_from_images_called.append(True))

    downloader.run()

    assert (downloader.scans_dir / "pag_0000.jpg").exists()
    assert not pdf_from_images_called


def test_native_pdf_download_failure_falls_back_to_canvas(monkeypatch, tmp_path: Path):
    downloader = _build_downloader(
        monkeypatch,
        tmp_path,
        _manifest_with_native_pdf(),
        prefer_native_pdf=True,
        create_pdf_from_images=False,
    )
    monkeypatch.setattr(downloader, "download_native_pdf", lambda _url: False)

    fallback_called: list[bool] = []

    def _fake_download_canvases(*args, **kwargs):
        fallback_called.append(True)
        return [], []

    monkeypatch.setattr(downloader, "_download_canvases", _fake_download_canvases)
    monkeypatch.setattr(downloader, "_finalize_downloads", lambda valid: [])

    downloader.run()

    assert fallback_called


def test_native_pdf_extraction_failure_falls_back_to_canvas(monkeypatch, tmp_path: Path):
    downloader = _build_downloader(
        monkeypatch,
        tmp_path,
        _manifest_with_native_pdf(),
        prefer_native_pdf=True,
        create_pdf_from_images=False,
    )
    monkeypatch.setattr(downloader, "download_native_pdf", lambda _url: True)
    monkeypatch.setattr(downloader, "_extract_pages_from_pdf", lambda _path, progress_callback=None: False)

    fallback_called: list[bool] = []

    def _fake_download_canvases(*args, **kwargs):
        fallback_called.append(True)
        return [], []

    monkeypatch.setattr(downloader, "_download_canvases", _fake_download_canvases)
    monkeypatch.setattr(downloader, "_finalize_downloads", lambda valid: [])

    downloader.run()

    assert fallback_called


def test_native_pdf_ignored_when_preference_disabled(monkeypatch, tmp_path: Path):
    downloader = _build_downloader(
        monkeypatch,
        tmp_path,
        _manifest_with_native_pdf(),
        prefer_native_pdf=False,
        create_pdf_from_images=False,
    )
    monkeypatch.setattr(
        downloader,
        "download_native_pdf",
        lambda _url: (_ for _ in ()).throw(AssertionError("Native PDF should not be downloaded")),
    )

    fallback_called: list[bool] = []

    def _fake_download_canvases(*args, **kwargs):
        fallback_called.append(True)
        return [], []

    monkeypatch.setattr(downloader, "_download_canvases", _fake_download_canvases)
    monkeypatch.setattr(downloader, "_finalize_downloads", lambda valid: [])

    downloader.run()

    assert fallback_called


def test_no_native_pdf_does_not_create_pdf_when_disabled(monkeypatch, tmp_path: Path):
    downloader = _build_downloader(
        monkeypatch,
        tmp_path,
        _manifest_without_native_pdf(),
        prefer_native_pdf=True,
        create_pdf_from_images=False,
    )
    monkeypatch.setattr(downloader, "_download_canvases", lambda *args, **kwargs: ([], []))
    monkeypatch.setattr(downloader, "_finalize_downloads", lambda valid: ["pag_0000.jpg"])

    pdf_from_images_called: list[bool] = []
    monkeypatch.setattr(downloader, "create_pdf", lambda files=None: pdf_from_images_called.append(True))

    downloader.run()

    assert not pdf_from_images_called


def test_no_native_pdf_creates_pdf_when_enabled(monkeypatch, tmp_path: Path):
    downloader = _build_downloader(
        monkeypatch,
        tmp_path,
        _manifest_without_native_pdf(),
        prefer_native_pdf=True,
        create_pdf_from_images=True,
    )
    monkeypatch.setattr(downloader, "_download_canvases", lambda *args, **kwargs: ([], []))
    monkeypatch.setattr(downloader, "_finalize_downloads", lambda valid: ["pag_0000.jpg"])

    pdf_from_images_called: list[bool] = []
    monkeypatch.setattr(downloader, "create_pdf", lambda files=None: pdf_from_images_called.append(True))

    downloader.run()

    assert pdf_from_images_called


def test_extract_pages_from_pdf_uses_viewer_dpi(monkeypatch, tmp_path: Path):
    downloader = _build_downloader(
        monkeypatch,
        tmp_path,
        _manifest_with_native_pdf(),
        prefer_native_pdf=True,
        create_pdf_from_images=False,
    )

    def _fake_get_setting(key, default=None):
        if key == "pdf.viewer_dpi":
            return 222
        if key == "images.viewer_quality":
            return 88
        return default

    monkeypatch.setattr(downloader.cm, "get_setting", _fake_get_setting)

    captured: dict[str, object] = {}

    def _fake_convert_pdf_to_images(*, pdf_path, output_dir, progress_callback, dpi, jpeg_quality):
        captured["pdf_path"] = pdf_path
        captured["output_dir"] = output_dir
        captured["dpi"] = dpi
        captured["jpeg_quality"] = jpeg_quality
        return True, "ok"

    monkeypatch.setattr(downloader_module, "convert_pdf_to_images", _fake_convert_pdf_to_images)

    ok = downloader._extract_pages_from_pdf(downloader.output_path)

    assert ok is True
    assert captured["pdf_path"] == downloader.output_path
    assert captured["output_dir"] == downloader.scans_dir
    assert captured["dpi"] == 222
    assert captured["jpeg_quality"] == 88
