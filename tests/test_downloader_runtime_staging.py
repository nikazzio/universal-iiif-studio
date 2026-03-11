from pathlib import Path

import pytest
from PIL import Image

from universal_iiif_core.logic import downloader_runtime

# Mark as slow (creates images, tests file promotion/staging)
pytestmark = pytest.mark.slow


class _Logger:
    def debug(self, *_args, **_kwargs):
        return None


class _Vault:
    def __init__(self):
        self.calls: list[dict] = []

    def upsert_manuscript(self, _ms_id, **kwargs):
        self.calls.append(kwargs)


class _DummyDownloader:
    def __init__(self, root: Path, *, expected_total: int):
        self.scans_dir = root / "scans"
        self.temp_dir = root / "temp"
        self.pdf_dir = root / "pdf"
        self.data_dir = root / "data"
        self.scans_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.overwrite_existing_scans = False
        self.expected_total_canvases = expected_total
        self.total_canvases = expected_total
        self.ms_id = "DOC_STAGE"
        self.logger = _Logger()
        self.vault = _Vault()
        self.stats_path = self.data_dir / "image_stats.json"


def _write_valid_jpg(path: Path, color: str = "white") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), color=color).save(path, format="JPEG")


def test_finalize_downloads_keeps_temp_files_when_incomplete(tmp_path):
    """Incomplete downloads must keep staged images in temp dir."""
    dummy = _DummyDownloader(tmp_path, expected_total=3)
    staged = dummy.temp_dir / "pag_0000.jpg"
    _write_valid_jpg(staged)

    out = downloader_runtime._finalize_downloads(dummy, [str(staged)])
    assert out == []
    assert staged.exists()
    assert not (dummy.scans_dir / "pag_0000.jpg").exists()


def test_finalize_downloads_promotes_temp_files_when_complete(tmp_path):
    """Once all pages are present, staged files should move to scans and temp cleaned."""
    dummy = _DummyDownloader(tmp_path, expected_total=2)
    p0 = dummy.temp_dir / "pag_0000.jpg"
    p1 = dummy.temp_dir / "pag_0001.jpg"
    _write_valid_jpg(p0)
    _write_valid_jpg(p1)

    out = downloader_runtime._finalize_downloads(dummy, [str(p0), str(p1)])
    assert len(out) == 2
    assert (dummy.scans_dir / "pag_0000.jpg").exists()
    assert (dummy.scans_dir / "pag_0001.jpg").exists()
    assert not dummy.temp_dir.exists()


def test_sync_asset_state_counts_known_pages_from_scans_and_temp(tmp_path):
    """Asset sync should consider both scans and staged pages."""
    dummy = _DummyDownloader(tmp_path, expected_total=5)
    _write_valid_jpg(dummy.scans_dir / "pag_0000.jpg")
    _write_valid_jpg(dummy.temp_dir / "pag_0001.jpg")
    _write_valid_jpg(dummy.temp_dir / "pag_0002.jpg")

    downloader_runtime._sync_asset_state(dummy, total_expected=5)

    payload = dummy.vault.calls[-1]
    assert payload["asset_state"] == "partial"
    assert int(payload["downloaded_canvases"]) == 3
    assert payload["missing_pages_json"] == "[4, 5]"


def test_finalize_downloads_does_not_promote_unvalidated_temp_files(tmp_path):
    """Only files present in the validated list may be promoted into scans."""
    dummy = _DummyDownloader(tmp_path, expected_total=1)
    validated = dummy.temp_dir / "pag_0000.jpg"
    stale = dummy.temp_dir / "pag_0001.jpg"
    _write_valid_jpg(validated)
    stale.write_bytes(b"stale")

    out = downloader_runtime._finalize_downloads(dummy, [str(validated)])
    assert len(out) == 1
    assert (dummy.scans_dir / "pag_0000.jpg").exists()
    assert not (dummy.scans_dir / "pag_0001.jpg").exists()


def test_finalize_downloads_promotes_previous_valid_temp_pages_when_now_complete(tmp_path):
    """Segmented runs should promote all validated staged pages once complete."""
    dummy = _DummyDownloader(tmp_path, expected_total=5)
    staged = []
    for idx in range(5):
        image_path = dummy.temp_dir / f"pag_{idx:04d}.jpg"
        _write_valid_jpg(image_path)
        staged.append(image_path)

    # Simulate current run validating only the last segment (pages 3-5).
    out = downloader_runtime._finalize_downloads(dummy, [str(staged[2]), str(staged[3]), str(staged[4])])
    assert len(out) == 5
    for idx in range(5):
        assert (dummy.scans_dir / f"pag_{idx:04d}.jpg").exists()
    assert not dummy.temp_dir.exists()


def test_finalize_downloads_promotes_page_refresh_immediately_when_overwriting(tmp_path):
    """Page-only refreshes should overwrite scans immediately even if the full manuscript is incomplete."""
    dummy = _DummyDownloader(tmp_path, expected_total=5)
    dummy.overwrite_existing_scans = True

    existing = dummy.scans_dir / "pag_0000.jpg"
    staged = dummy.temp_dir / "pag_0000.jpg"
    _write_valid_jpg(existing, color="blue")
    _write_valid_jpg(staged, color="red")

    out = downloader_runtime._finalize_downloads(dummy, [str(staged)])

    assert str(existing) in out
    assert existing.exists()
    assert not staged.exists()
    assert not dummy.temp_dir.exists()


def test_finalize_downloads_excludes_stale_scans_outside_manifest_scope(tmp_path):
    """Finalized files should be restricted to current manifest page scope."""
    dummy = _DummyDownloader(tmp_path, expected_total=2)
    stale = dummy.scans_dir / "pag_9999.jpg"
    _write_valid_jpg(stale)

    p0 = dummy.temp_dir / "pag_0000.jpg"
    p1 = dummy.temp_dir / "pag_0001.jpg"
    _write_valid_jpg(p0)
    _write_valid_jpg(p1)

    out = downloader_runtime._finalize_downloads(dummy, [str(p0), str(p1)])
    assert len(out) == 2
    assert str(stale) not in out
    assert str(dummy.scans_dir / "pag_0000.jpg") in out
    assert str(dummy.scans_dir / "pag_0001.jpg") in out


class _RunDummy:
    def __init__(self):
        self.progress_callback = None
        self.ocr_model = None
        self.finalize_calls: list[list[str]] = []
        self.clean_cache = False

    def extract_metadata(self):
        return None

    def get_canvases(self):
        return [{"id": "c1"}, {"id": "c2"}]

    def _build_canvas_plan(self, canvases, _target_pages):
        return set(), [(idx, canvas) for idx, canvas in enumerate(canvases)]

    def _mark_downloading_state(self, _total_pages):
        return None

    def _maybe_run_native_pdf(self, _native_pdf_url, _selected_pages, _progress_callback):
        return False

    def get_pdf_url(self):
        return None

    def _download_canvases(self, _canvas_plan, progress_callback=None, should_cancel=None, total_for_progress=0):
        _ = progress_callback
        _ = should_cancel
        _ = total_for_progress
        return (["staged/pag_0000.jpg", "staged/pag_0001.jpg"], [])

    def _store_page_stats(self, _page_stats):
        return None

    def _finalize_downloads(self, valid):
        self.finalize_calls.append(list(valid))
        return []

    def _should_create_pdf_from_images(self):
        return False

    def _sync_asset_state(self, _total_pages):
        return None


def test_run_calls_finalize_even_when_stop_requested_late():
    """Late stop requests must not skip finalization decision."""
    dummy = _RunDummy()
    downloader_runtime.run(dummy, should_cancel=lambda: True)
    assert dummy.finalize_calls == [["staged/pag_0000.jpg", "staged/pag_0001.jpg"]]


def test_run_fails_selected_direct_refresh_when_no_page_was_replaced():
    """Page-only direct refreshes must error when no selected page download succeeds."""

    class _DirectRefreshDummy(_RunDummy):
        def __init__(self):
            super().__init__()
            self.force_redownload = True
            self.overwrite_existing_scans = True
            self.stitch_mode = "direct_only"

        def _build_canvas_plan(self, canvases, target_pages):
            selected = set(target_pages or set())
            return selected, [(idx, canvas) for idx, canvas in enumerate(canvases) if (idx + 1) in selected]

        def _download_canvases(self, _canvas_plan, progress_callback=None, should_cancel=None, total_for_progress=0):
            _ = progress_callback
            _ = should_cancel
            _ = total_for_progress
            return ([], [])

    dummy = _DirectRefreshDummy()

    with pytest.raises(RuntimeError, match="Refresh diretto high-res fallito"):
        downloader_runtime.run(dummy, target_pages={1})


def test_store_page_stats_merges_existing_pages(tmp_path):
    """Saving fresh stats should merge by page index instead of dropping prior entries."""
    dummy = _DummyDownloader(tmp_path, expected_total=2)
    downloader_runtime.save_json(
        dummy.data_dir / "image_stats.json",
        {
            "doc_id": dummy.ms_id,
            "pages": [
                {"page_index": 0, "download_method": "direct"},
                {"page_index": 1, "download_method": "tile_stitch"},
            ],
        },
    )
    dummy.stats_path = dummy.data_dir / "image_stats.json"

    downloader_runtime._store_page_stats(
        dummy,
        [
            {"page_index": 1, "download_method": "direct"},
        ],
    )

    payload = downloader_runtime.load_json(dummy.stats_path)
    assert payload["pages"] == [
        {"page_index": 0, "download_method": "direct"},
        {"page_index": 1, "download_method": "direct"},
    ]
