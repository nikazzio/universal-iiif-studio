"""Tests for universal_iiif_core.utils — pure utility functions."""

from __future__ import annotations

import time
from pathlib import Path

from universal_iiif_core.utils import (
    cleanup_old_files,
    compute_text_diff_stats,
    ensure_dir,
    generate_folder_name,
    generate_job_id,
    load_json,
    sanitize_filename,
    save_json,
)


def test_save_and_load_json_roundtrip(tmp_path: Path):
    """save_json + load_json should roundtrip cleanly."""
    data = {"key": "value", "nested": [1, 2, 3]}
    path = tmp_path / "test.json"
    save_json(str(path), data)
    assert path.exists()
    loaded = load_json(str(path))
    assert loaded == data


def test_load_json_returns_none_for_missing_file(tmp_path: Path):
    """load_json on missing path returns None."""
    assert load_json(str(tmp_path / "nope.json")) is None


def test_load_json_returns_none_for_corrupt_file(tmp_path: Path):
    """load_json on invalid JSON returns None."""
    bad = tmp_path / "bad.json"
    bad.write_text("{broken", encoding="utf-8")
    assert load_json(str(bad)) is None


def test_save_json_overwrites_existing(tmp_path: Path):
    """save_json should atomically overwrite an existing file."""
    path = tmp_path / "data.json"
    save_json(str(path), {"v": 1})
    save_json(str(path), {"v": 2})
    assert load_json(str(path)) == {"v": 2}


def test_ensure_dir_creates_nested(tmp_path: Path):
    """ensure_dir should create nested directories."""
    target = tmp_path / "a" / "b" / "c"
    ensure_dir(target)
    assert target.is_dir()


def test_ensure_dir_noop_on_none():
    """ensure_dir should not crash on None."""
    ensure_dir(None)


def test_cleanup_old_files_removes_stale(tmp_path: Path):
    """cleanup_old_files should delete entries older than threshold."""
    old_file = tmp_path / "old.txt"
    old_file.write_text("old")
    # Set mtime to 30 days ago
    old_time = time.time() - (30 * 24 * 60 * 60)
    import os

    os.utime(old_file, (old_time, old_time))

    new_file = tmp_path / "new.txt"
    new_file.write_text("new")

    stats = cleanup_old_files(tmp_path, older_than_days=7)
    assert stats["deleted"] >= 1
    assert not old_file.exists()
    assert new_file.exists()


def test_cleanup_old_files_handles_nonexistent_dir(tmp_path: Path):
    """cleanup_old_files on nonexistent dir returns zeroed stats."""
    stats = cleanup_old_files(tmp_path / "nope", older_than_days=1)
    assert stats == {"deleted": 0, "errors": 0, "skipped": 0}


def test_cleanup_old_files_removes_stale_directories(tmp_path: Path):
    """cleanup_old_files should also remove stale directories."""
    old_dir = tmp_path / "old_subdir"
    old_dir.mkdir()
    (old_dir / "file.txt").write_text("x")
    old_time = time.time() - (30 * 24 * 60 * 60)
    import os

    os.utime(old_dir, (old_time, old_time))

    stats = cleanup_old_files(tmp_path, older_than_days=7)
    assert stats["deleted"] == 1
    assert not old_dir.exists()


def test_compute_text_diff_stats_additions():
    """Diff stats should count character-level additions and deletions."""
    result = compute_text_diff_stats("hello", "hello world")
    assert result["added"] == 6
    assert result["deleted"] == 0


def test_compute_text_diff_stats_deletions():
    """Diff stats should detect pure deletions."""
    result = compute_text_diff_stats("hello world", "hello")
    assert result["added"] == 0
    assert result["deleted"] == 6


def test_compute_text_diff_stats_replacement():
    """Diff stats should handle mixed replacements."""
    result = compute_text_diff_stats("abc", "xyz")
    assert result["added"] > 0
    assert result["deleted"] > 0


def test_compute_text_diff_stats_none_inputs():
    """Diff stats should handle None inputs gracefully."""
    result = compute_text_diff_stats(None, "new text")
    assert result["added"] == 8
    assert result["deleted"] == 0

    result2 = compute_text_diff_stats("old", None)
    assert result2["deleted"] == 3


def test_generate_job_id_deterministic():
    """Job ID should be deterministic for same inputs."""
    id1 = generate_job_id("Gallica", "https://example.com/manifest.json")
    id2 = generate_job_id("Gallica", "https://example.com/manifest.json")
    assert id1 == id2
    assert id1.startswith("Gallica_")
    assert len(id1) > 20


def test_generate_job_id_different_for_different_urls():
    """Different URLs should produce different job IDs."""
    id1 = generate_job_id("Gallica", "https://example.com/m1.json")
    id2 = generate_job_id("Gallica", "https://example.com/m2.json")
    assert id1 != id2


def test_generate_folder_name_basic():
    """Folder name should include library, doc_id, and title."""
    name = generate_folder_name("Gallica", "bpt6k123", "Les Misérables")
    assert "GALLICA" in name
    assert "bpt6k123" in name
    assert "Les Mis" in name


def test_generate_folder_name_no_title():
    """Folder name without title should still be valid."""
    name = generate_folder_name("Vatican", "MSS_Vat.lat.123")
    assert "VATICAN" in name
    assert "MSS_Vat.lat.123" in name


def test_generate_folder_name_truncates_long_title():
    """Title should be truncated to prevent excessively long paths."""
    long_title = "A" * 100
    name = generate_folder_name("Lib", "id1", long_title)
    assert len(name) < 80


def test_sanitize_filename_removes_dangerous_chars():
    """Sanitize should strip filesystem-unsafe characters."""
    assert "/" not in sanitize_filename("path/to/file")
    assert ":" not in sanitize_filename("file:name")
    assert '"' not in sanitize_filename('file"name')
    assert "<" not in sanitize_filename("file<name>")


def test_sanitize_filename_collapses_whitespace():
    """Sanitize should collapse multiple spaces."""
    result = sanitize_filename("hello   world   test")
    assert result == "hello world test"


def test_sanitize_filename_strips_control_chars():
    """Sanitize should remove control characters."""
    result = sanitize_filename("hello\x00\x01world")
    assert "\x00" not in result
    assert "helloworld" in result
