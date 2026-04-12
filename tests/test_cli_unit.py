"""Tests for CLI pure helpers — _build_parser, _status_icon, _resolve_manifest, _handle_db_commands."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock

from universal_iiif_cli import cli
from universal_iiif_cli.cli import _build_parser, _handle_db_commands, _status_icon

# --- _status_icon ---

def test_status_icon_complete():
    assert _status_icon("complete") == "✅"


def test_status_icon_downloading():
    assert _status_icon("downloading") == "⏳"


def test_status_icon_error():
    assert _status_icon("error") == "❌"


def test_status_icon_unknown_returns_circle():
    assert _status_icon("pending") == "⚪"
    assert _status_icon("") == "⚪"


# --- _build_parser ---

def test_build_parser_returns_parser():
    parser = _build_parser()
    assert isinstance(parser, argparse.ArgumentParser)


def test_build_parser_url_optional():
    parser = _build_parser()
    args = parser.parse_args([])
    assert args.url is None


def test_build_parser_url_positional():
    parser = _build_parser()
    args = parser.parse_args(["https://example.com/manifest.json"])
    assert args.url == "https://example.com/manifest.json"


def test_build_parser_workers_default():
    parser = _build_parser()
    args = parser.parse_args([])
    assert args.workers == 4


def test_build_parser_workers_custom():
    parser = _build_parser()
    args = parser.parse_args(["-w", "8", "http://x.com"])
    assert args.workers == 8


def test_build_parser_prefer_images_flag():
    parser = _build_parser()
    args = parser.parse_args(["--prefer-images", "http://x.com"])
    assert args.prefer_images is True


def test_build_parser_list_flag():
    parser = _build_parser()
    args = parser.parse_args(["--list"])
    assert args.list is True


def test_build_parser_info_arg():
    parser = _build_parser()
    args = parser.parse_args(["--info", "Vat.lat.3225"])
    assert args.info == "Vat.lat.3225"


def test_build_parser_delete_arg():
    parser = _build_parser()
    args = parser.parse_args(["--delete", "ms123"])
    assert args.delete == "ms123"


def test_build_parser_set_status():
    parser = _build_parser()
    args = parser.parse_args(["--set-status", "ms123", "complete"])
    assert args.set_status == ["ms123", "complete"]


def test_build_parser_clean_cache():
    parser = _build_parser()
    args = parser.parse_args(["--clean-cache", "http://x.com"])
    assert args.clean_cache is True


def test_build_parser_ocr_model():
    parser = _build_parser()
    args = parser.parse_args(["--ocr", "best.mlmodel", "http://x.com"])
    assert args.ocr == "best.mlmodel"


def test_build_parser_create_pdf():
    parser = _build_parser()
    args = parser.parse_args(["--create-pdf", "http://x.com"])
    assert args.create_pdf is True


def test_build_parser_output():
    parser = _build_parser()
    args = parser.parse_args(["-o", "out.pdf", "http://x.com"])
    assert args.output == "out.pdf"


def test_build_parser_delete_job():
    parser = _build_parser()
    args = parser.parse_args(["--delete-job", "job-abc123"])
    assert args.delete_job == "job-abc123"


# --- _resolve_manifest ---

def test_resolve_manifest_uses_library_aware_resolver(monkeypatch):
    """CLI manifest resolution should preserve the detected library name."""
    monkeypatch.setattr(
        cli,
        "resolve_url_with_library",
        lambda _value: ("https://example.org/manifest.json", "DOC123", "Generic"),
    )

    manifest_url, suggested_id, library = cli._resolve_manifest("https://example.org/input")

    assert manifest_url == "https://example.org/manifest.json"
    assert suggested_id == "DOC123"
    assert library == "Generic"


def test_resolve_manifest_keeps_direct_manifest_urls():
    """Direct manifest URLs should still bypass resolver-specific detection."""
    original = cli.resolve_url_with_library
    cli.resolve_url_with_library = lambda _value: (None, None, "Unknown")
    try:
        manifest_url, suggested_id, library = cli._resolve_manifest("https://example.org/direct-manifest.json")
    finally:
        cli.resolve_url_with_library = original

    assert manifest_url == "https://example.org/direct-manifest.json"
    assert suggested_id is None
    assert library == "Unknown"


# --- _handle_db_commands ---

def test_handle_db_commands_list(monkeypatch):
    mock_list = MagicMock()
    monkeypatch.setattr(cli, "_handle_list", mock_list)
    args = _build_parser().parse_args(["--list"])
    assert _handle_db_commands(args) is True
    mock_list.assert_called_once()


def test_handle_db_commands_info(monkeypatch):
    mock_info = MagicMock()
    monkeypatch.setattr(cli, "_handle_info", mock_info)
    args = _build_parser().parse_args(["--info", "ms123"])
    assert _handle_db_commands(args) is True
    mock_info.assert_called_once_with("ms123")


def test_handle_db_commands_delete(monkeypatch):
    mock_delete = MagicMock()
    monkeypatch.setattr(cli, "_handle_delete", mock_delete)
    args = _build_parser().parse_args(["--delete", "ms123"])
    assert _handle_db_commands(args) is True
    mock_delete.assert_called_once_with("ms123")


def test_handle_db_commands_delete_job(monkeypatch):
    mock_delete_job = MagicMock()
    monkeypatch.setattr(cli, "_handle_delete_job", mock_delete_job)
    args = _build_parser().parse_args(["--delete-job", "job-abc"])
    assert _handle_db_commands(args) is True
    mock_delete_job.assert_called_once_with("job-abc")


def test_handle_db_commands_set_status(monkeypatch):
    mock_set = MagicMock()
    monkeypatch.setattr(cli, "_handle_set_status", mock_set)
    args = _build_parser().parse_args(["--set-status", "ms1", "complete"])
    assert _handle_db_commands(args) is True
    mock_set.assert_called_once_with("ms1", "complete")


def test_handle_db_commands_no_command():
    args = _build_parser().parse_args([])
    assert _handle_db_commands(args) is False


# --- _resolve_download_args ---

def test_resolve_download_args_with_url():
    from universal_iiif_cli.cli import _resolve_download_args

    args = _build_parser().parse_args([
        "http://x.com/m.json", "-w", "8", "--prefer-images",
        "--ocr", "model.mlmodel", "--create-pdf",
    ])
    result = _resolve_download_args(args)
    assert result == ("http://x.com/m.json", None, 8, False, True, "model.mlmodel", True)


def test_resolve_download_args_wizard_mode(monkeypatch):
    from universal_iiif_cli.cli import _resolve_download_args

    monkeypatch.setattr(cli, "wizard_mode", lambda: ("https://wiz.com", "output.pdf", "model.ml"))
    args = _build_parser().parse_args([])
    result = _resolve_download_args(args)
    assert result == ("https://wiz.com", "output.pdf", 4, False, False, "model.ml", False)
