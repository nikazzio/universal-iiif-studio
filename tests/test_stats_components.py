"""Tests for library stats components and route handlers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from studio_ui.components.library_stats import (
    _dir_size,
    _fmt_count,
    _format_bytes,
    _pct_str,
    _scan_disk_usage,
    _scan_transcriptions,
    _time_ago,
    render_library_stats,
    render_sidebar_stats_widget,
    render_stats_page_content,
)

# ── helpers ───────────────────────────────────────────────────────────────────


def _ms(**overrides) -> dict:
    doc = {
        "id": "DOC1",
        "library": "Gallica",
        "display_title": "Test ms",
        "asset_state": "complete",
        "total_canvases": 10,
        "downloaded_canvases": 10,
        "local_path": None,
        "updated_at": None,
    }
    doc.update(overrides)
    return doc


# ── _format_bytes ─────────────────────────────────────────────────────────────


def test_format_bytes_bytes():
    assert _format_bytes(512) == "512.0 B"


def test_format_bytes_kilobytes():
    assert _format_bytes(1536) == "1.5 KB"


def test_format_bytes_megabytes():
    assert _format_bytes(1_572_864) == "1.5 MB"


def test_format_bytes_gigabytes():
    assert _format_bytes(1_610_612_736) == "1.5 GB"


# ── _pct_str ──────────────────────────────────────────────────────────────────


def test_pct_str_zero_total():
    assert _pct_str(0, 0) == "—"


def test_pct_str_half():
    assert _pct_str(50, 100) == "50%"


# ── _fmt_count ────────────────────────────────────────────────────────────────


def test_fmt_count_small():
    assert _fmt_count(42) == "42"


def test_fmt_count_thousands():
    assert _fmt_count(8400) == "8.4k"


def test_fmt_count_millions():
    assert _fmt_count(2_500_000) == "2.5M"


# ── _time_ago ─────────────────────────────────────────────────────────────────


def test_time_ago_none():
    assert _time_ago(None) == "—"


def test_time_ago_naive_sqlite_timestamp():
    """Naive SQLite timestamps (no tz) must be treated as UTC, not local time."""
    result = _time_ago("2000-01-01 00:00:00")
    assert result != "—"
    assert "a fa" in result


def test_time_ago_iso_with_z():
    result = _time_ago("2000-06-15T12:00:00Z")
    assert "a fa" in result


def test_time_ago_invalid():
    assert _time_ago("not-a-date") == "—"


# ── _dir_size ─────────────────────────────────────────────────────────────────


def test_dir_size_counts_files(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"hello")
    (tmp_path / "b.txt").write_bytes(b"world!")
    assert _dir_size(tmp_path) == 11


def test_dir_size_skips_unreadable_file(tmp_path):
    """A single unreadable file must not zero out the whole directory size."""
    good = tmp_path / "good.txt"
    good.write_bytes(b"abc")

    bad = tmp_path / "bad.txt"
    bad.write_bytes(b"xyz")

    original_stat = Path.stat

    def patched_stat(self, *args, **kwargs):
        result = original_stat(self, *args, **kwargs)
        if self.name == "bad.txt":
            raise OSError("permission denied")
        return result

    with patch.object(Path, "stat", patched_stat):
        size = _dir_size(tmp_path)

    assert size == 3  # only 'good.txt' counted


# ── _scan_disk_usage ──────────────────────────────────────────────────────────


def test_scan_disk_usage_skips_path_outside_downloads(tmp_path):
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "file.bin").write_bytes(b"secret")

    manuscripts = [_ms(local_path=str(outside))]

    with patch("studio_ui.components.library_stats.get_config_manager") as mock_cm:
        mock_cm.return_value.get_downloads_dir.return_value = downloads
        total = _scan_disk_usage(manuscripts)

    assert total == 0


def test_scan_disk_usage_counts_valid_path(tmp_path):
    downloads = tmp_path / "downloads"
    ms_dir = downloads / "Gallica" / "DOC1"
    ms_dir.mkdir(parents=True)
    (ms_dir / "page.jpg").write_bytes(b"x" * 100)

    manuscripts = [_ms(local_path=str(ms_dir))]

    with patch("studio_ui.components.library_stats.get_config_manager") as mock_cm:
        mock_cm.return_value.get_downloads_dir.return_value = downloads
        total = _scan_disk_usage(manuscripts)

    assert total == 100


def test_scan_disk_usage_deduplicates_local_path(tmp_path):
    downloads = tmp_path / "downloads"
    ms_dir = downloads / "lib" / "doc"
    ms_dir.mkdir(parents=True)
    (ms_dir / "f.jpg").write_bytes(b"x" * 50)

    manuscripts = [_ms(local_path=str(ms_dir)), _ms(local_path=str(ms_dir))]

    with patch("studio_ui.components.library_stats.get_config_manager") as mock_cm:
        mock_cm.return_value.get_downloads_dir.return_value = downloads
        total = _scan_disk_usage(manuscripts)

    assert total == 50


# ── _scan_transcriptions ──────────────────────────────────────────────────────


def test_scan_transcriptions_counts_pages(tmp_path):
    ms_dir = tmp_path / "ms1"
    data_dir = ms_dir / "data"
    data_dir.mkdir(parents=True)
    tx = {
        "pages": [
            {"full_text": "Hello", "is_manual": True},
            {"full_text": "World", "is_manual": False},
            {"full_text": ""},
        ]
    }
    (data_dir / "transcription.json").write_text(json.dumps(tx), encoding="utf-8")

    manuscripts = [_ms(local_path=str(ms_dir))]
    transcribed, ocr = _scan_transcriptions(manuscripts)

    assert transcribed == 2
    assert ocr == 1


def test_scan_transcriptions_missing_file(tmp_path):
    manuscripts = [_ms(local_path=str(tmp_path))]
    transcribed, ocr = _scan_transcriptions(manuscripts)
    assert transcribed == 0
    assert ocr == 0


# ── render_sidebar_stats_widget ───────────────────────────────────────────────


def test_sidebar_widget_renders_counts():
    manuscripts = [_ms(total_canvases=100, downloaded_canvases=50)] * 3
    rendered = repr(render_sidebar_stats_widget(manuscripts))
    assert "3 mss" in rendered
    assert "50%" in rendered


def test_sidebar_widget_links_to_stats():
    rendered = repr(render_sidebar_stats_widget([_ms()]))
    assert '"/stats"' in rendered or "href='/stats'" in rendered or "/stats" in rendered


def test_sidebar_widget_empty_library():
    rendered = repr(render_sidebar_stats_widget([]))
    assert "0 mss" in rendered
    assert "0% locale" in rendered


# ── render_stats_page_content ─────────────────────────────────────────────────


def test_stats_page_content_shows_manuscript_count():
    manuscripts = [_ms(library="BnF")] * 5
    rendered = repr(render_stats_page_content(manuscripts))
    assert "5" in rendered
    assert "Manoscritti" in rendered


def test_stats_page_content_has_provider_panel():
    manuscripts = [_ms(library="Gallica")] * 3 + [_ms(library="BnF")] * 2
    rendered = repr(render_stats_page_content(manuscripts))
    assert "Gallica" in rendered
    assert "BnF" in rendered
    assert "Distribuzione per biblioteca" in rendered


def test_stats_page_content_has_lazy_detail_placeholder():
    rendered = repr(render_stats_page_content([_ms()]))
    assert "/api/stats/detail" in rendered
    assert "stats-detail-panel" in rendered


def test_stats_page_content_shows_recent_activity():
    manuscripts = [_ms(display_title="Codex A", asset_state="complete", updated_at="2024-01-01T00:00:00Z")]
    rendered = repr(render_stats_page_content(manuscripts))
    assert "Ultimi aggiornati" in rendered
    assert "Codex A" in rendered


# ── render_library_stats (detail panel) ──────────────────────────────────────


def test_render_library_stats_returns_detail_panel(tmp_path):
    downloads = tmp_path / "downloads"
    downloads.mkdir()

    manuscripts = [_ms(total_canvases=20)]

    with patch("studio_ui.components.library_stats.get_config_manager") as mock_cm:
        mock_cm.return_value.get_downloads_dir.return_value = downloads
        rendered = repr(render_library_stats(manuscripts))

    assert "stats-detail-panel" in rendered
    assert "Spazio disco" in rendered
    assert "Pagine trascritte" in rendered
    assert "Pagine OCR" in rendered


# ── route handlers ────────────────────────────────────────────────────────────


def test_stats_page_handler_returns_full_layout_for_normal_request(monkeypatch):
    from studio_ui.routes import stats_handlers

    monkeypatch.setattr(
        stats_handlers.VaultManager,
        "get_all_manuscripts",
        lambda self: [_ms()],
    )

    mock_request = MagicMock()
    mock_request.headers.get.return_value = None

    result = repr(stats_handlers.stats_page(mock_request))
    assert "Statistiche" in result


def test_stats_page_handler_returns_fragment_for_htmx(monkeypatch):
    from studio_ui.routes import stats_handlers

    monkeypatch.setattr(
        stats_handlers.VaultManager,
        "get_all_manuscripts",
        lambda self: [_ms()],
    )

    mock_request = MagicMock()
    mock_request.headers.get.return_value = "true"

    result = repr(stats_handlers.stats_page(mock_request))
    assert "stats-page" in result


def test_stats_sidebar_widget_handler(monkeypatch):
    from studio_ui.routes import stats_handlers

    monkeypatch.setattr(
        stats_handlers.VaultManager,
        "get_all_manuscripts",
        lambda self: [_ms(total_canvases=50, downloaded_canvases=25)],
    )

    result = repr(stats_handlers.stats_sidebar_widget())
    assert "sidebar-stats-widget" in result
    assert "1 mss" in result


def test_stats_detail_handler_uses_cache(monkeypatch, tmp_path):
    from studio_ui.routes import stats_handlers

    downloads = tmp_path / "downloads"
    downloads.mkdir()

    call_count = {"n": 0}

    def _fake_get_all(self):
        call_count["n"] += 1
        return [_ms()]

    monkeypatch.setattr(stats_handlers.VaultManager, "get_all_manuscripts", _fake_get_all)
    monkeypatch.setattr(
        "studio_ui.components.library_stats.get_config_manager",
        lambda: MagicMock(get_downloads_dir=lambda: downloads),
    )

    # Reset cache
    stats_handlers._detail_cache = None

    stats_handlers.stats_detail_content()
    stats_handlers.stats_detail_content()

    assert call_count["n"] == 1, "Second call should use cache, not re-query VaultManager"


def test_stats_detail_handler_refreshes_after_ttl(monkeypatch, tmp_path):
    from studio_ui.routes import stats_handlers

    downloads = tmp_path / "downloads"
    downloads.mkdir()

    call_count = {"n": 0}

    def _fake_get_all(self):
        call_count["n"] += 1
        return [_ms()]

    monkeypatch.setattr(stats_handlers.VaultManager, "get_all_manuscripts", _fake_get_all)
    monkeypatch.setattr(
        "studio_ui.components.library_stats.get_config_manager",
        lambda: MagicMock(get_downloads_dir=lambda: downloads),
    )

    import time as _t

    # Seed cache with a timestamp guaranteed to be past the TTL
    stats_handlers._detail_cache = (_t.monotonic() - stats_handlers._DETAIL_TTL - 1, None)

    stats_handlers.stats_detail_content()
    assert call_count["n"] == 1, "Expired cache must trigger a fresh scan"
