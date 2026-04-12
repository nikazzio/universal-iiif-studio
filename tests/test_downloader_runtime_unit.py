"""Tests for downloader_runtime pure helpers — _build_canvas_plan, _page_number_from_filename, _emit_canvas_progress."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from universal_iiif_core.logic.downloader_runtime import (
    _build_canvas_plan,
    _page_number_from_filename,
)


# --- _build_canvas_plan ---

class TestBuildCanvasPlan:
    def test_no_target_pages_returns_all(self):
        canvases = [{"id": "c0"}, {"id": "c1"}, {"id": "c2"}]
        selected, plan = _build_canvas_plan(canvases, None)
        assert selected == set()
        assert len(plan) == 3
        assert plan[0] == (0, {"id": "c0"})
        assert plan[2] == (2, {"id": "c2"})

    def test_empty_target_pages_returns_all(self):
        canvases = [{"id": "c0"}, {"id": "c1"}]
        selected, plan = _build_canvas_plan(canvases, set())
        assert len(plan) == 2

    def test_target_pages_filters_1_indexed(self):
        canvases = [{"id": "c0"}, {"id": "c1"}, {"id": "c2"}, {"id": "c3"}]
        selected, plan = _build_canvas_plan(canvases, {2, 4})
        assert selected == {2, 4}
        assert len(plan) == 2
        assert plan[0] == (1, {"id": "c1"})  # page 2 = index 1
        assert plan[1] == (3, {"id": "c3"})  # page 4 = index 3

    def test_target_page_out_of_range_skipped(self):
        canvases = [{"id": "c0"}]
        selected, plan = _build_canvas_plan(canvases, {1, 99})
        assert len(plan) == 1
        assert plan[0] == (0, {"id": "c0"})

    def test_empty_canvases(self):
        selected, plan = _build_canvas_plan([], {1, 2})
        assert plan == []


# --- _page_number_from_filename ---

class TestPageNumberFromFilename:
    def test_standard_filename(self):
        assert _page_number_from_filename("pag_0000.jpg") == 1

    def test_higher_index(self):
        assert _page_number_from_filename("pag_0042.jpg") == 43

    def test_no_underscore(self):
        assert _page_number_from_filename("invalid.jpg") is None

    def test_non_numeric_suffix(self):
        assert _page_number_from_filename("pag_abc.jpg") is None

    def test_path_with_directory(self):
        assert _page_number_from_filename("/tmp/scans/pag_0003.jpg") == 4

    def test_extension_agnostic(self):
        # stem is "pag_0005" regardless of extension
        assert _page_number_from_filename("pag_0005.png") == 6


# --- _emit_canvas_progress (needs self stub) ---

def test_emit_canvas_progress_no_callback():
    """No callback should not crash."""
    from universal_iiif_core.logic.downloader_runtime import _emit_canvas_progress

    stub = MagicMock()
    _emit_canvas_progress(stub, [None, "file.jpg", None], total_canvases=10, progress_callback=None)
    # Should not raise


def test_emit_canvas_progress_counts_completed():
    from universal_iiif_core.logic.downloader_runtime import _emit_canvas_progress

    stub = MagicMock()
    callback = MagicMock()
    downloaded = ["f1.jpg", "f2.jpg", None, "f3.jpg"]
    _emit_canvas_progress(stub, downloaded, total_canvases=10, progress_callback=callback, pages_outside_plan=3)
    callback.assert_called_once_with(6, 10)  # 3 outside + 3 completed in plan


def test_emit_canvas_progress_swallows_callback_error():
    from universal_iiif_core.logic.downloader_runtime import _emit_canvas_progress

    stub = MagicMock()
    callback = MagicMock(side_effect=RuntimeError("boom"))
    _emit_canvas_progress(stub, ["f.jpg"], total_canvases=5, progress_callback=callback)
    callback.assert_called_once()  # Called but didn't crash


# --- _store_page_stats ---

def test_store_page_stats_merges_with_existing(tmp_path: Path):
    """New stats should merge with existing page stats by page_index."""
    from types import SimpleNamespace

    from universal_iiif_core.logic.downloader_runtime import _store_page_stats
    from universal_iiif_core.utils import load_json, save_json

    stats_path = tmp_path / "stats.json"
    save_json(stats_path, {"pages": [{"page_index": 0, "width": 1000}]})

    stub = SimpleNamespace(stats_path=stats_path, ms_id="test_doc", logger=MagicMock())

    new_stats = [{"page_index": 1, "width": 2000}, {"page_index": 0, "width": 3000}]
    _store_page_stats(stub, new_stats)

    result = load_json(stats_path)
    pages = result["pages"]
    by_index = {p["page_index"]: p for p in pages}
    assert by_index[0]["width"] == 3000
    assert by_index[1]["width"] == 2000


def test_store_page_stats_empty_is_noop(tmp_path: Path):
    """Empty stats list should not create file."""
    from universal_iiif_core.logic.downloader_runtime import _store_page_stats

    stub = MagicMock()
    stub.stats_path = tmp_path / "stats.json"
    _store_page_stats(stub, [])
    assert not stub.stats_path.exists()


# --- _collect_finalized_scan_files ---

def test_collect_finalized_scan_files(tmp_path: Path):
    """Should return sorted scan paths for expected pages."""
    from universal_iiif_core.logic.downloader_runtime import _collect_finalized_scan_files
    from PIL import Image

    scans_dir = tmp_path / "scans"
    scans_dir.mkdir()

    for i in [0, 2, 4]:
        img = Image.new("RGB", (10, 10))
        img.save(scans_dir / f"pag_{i:04d}.jpg")

    stub = MagicMock()
    stub.scans_dir = scans_dir

    result = _collect_finalized_scan_files(stub, expected_pages={1, 3, 5}, validated_pages=set())
    assert len(result) == 3
    assert "pag_0000.jpg" in result[0]
    assert "pag_0002.jpg" in result[1]
    assert "pag_0004.jpg" in result[2]


def test_collect_finalized_scan_files_missing_pages(tmp_path: Path):
    """Missing scan files should be skipped."""
    from universal_iiif_core.logic.downloader_runtime import _collect_finalized_scan_files

    scans_dir = tmp_path / "scans"
    scans_dir.mkdir()

    stub = MagicMock()
    stub.scans_dir = scans_dir

    result = _collect_finalized_scan_files(stub, expected_pages={1, 2}, validated_pages=set())
    assert result == []


# --- _page_numbers_in_dir ---

def test_page_numbers_in_dir(tmp_path: Path):
    """Should find 1-indexed page numbers from pag_XXXX.jpg files."""
    from universal_iiif_core.logic.downloader_runtime import _page_numbers_in_dir
    from PIL import Image

    for i in [0, 3, 7]:
        img = Image.new("RGB", (10, 10))
        img.save(tmp_path / f"pag_{i:04d}.jpg")

    result = _page_numbers_in_dir(tmp_path)
    assert result == {1, 4, 8}  # 0-indexed + 1


def test_page_numbers_in_dir_empty(tmp_path: Path):
    from universal_iiif_core.logic.downloader_runtime import _page_numbers_in_dir

    assert _page_numbers_in_dir(tmp_path) == set()


def test_page_numbers_in_dir_nonexistent():
    from universal_iiif_core.logic.downloader_runtime import _page_numbers_in_dir

    assert _page_numbers_in_dir(Path("/nonexistent/dir")) == set()
