"""Tests for discovery and library pure handler helpers."""

from __future__ import annotations

from types import SimpleNamespace

from studio_ui.routes.discovery_handlers import (
    _build_item_preview_data,
    _build_manifest_preview_data,
    _has_native_pdf_rendering,
    _page_count_from_result,
    _pause_guard_response,
    _provider_supports_pagination,
    _toast_text,
)
from studio_ui.routes.library_handlers import _parse_ranges

# --- _toast_text ---

def test_toast_text_with_detail():
    assert _toast_text("Title", "some detail") == "Title: some detail"


def test_toast_text_without_detail():
    assert _toast_text("Title") == "Title"
    assert _toast_text("Title", "") == "Title"
    assert _toast_text("Title", "   ") == "Title"


# --- _build_item_preview_data ---

def test_build_item_preview_data_all_fields():
    item = {
        "id": "abc",
        "title": "Test MS",
        "manifest": "https://example.com/manifest",
        "description": "A test",
        "thumbnail": "https://example.com/thumb.jpg",
        "has_native_pdf": True,
    }
    result = _build_item_preview_data(item, "Vatican", pages=42)
    assert result["id"] == "abc"
    assert result["library"] == "Vatican"
    assert result["url"] == "https://example.com/manifest"
    assert result["label"] == "Test MS"
    assert result["pages"] == 42
    assert result["thumbnail"] == "https://example.com/thumb.jpg"
    assert result["has_native_pdf"] is True


def test_build_item_preview_data_defaults():
    result = _build_item_preview_data({}, "Oxford")
    assert result["label"] == "Senza Titolo"
    assert result["description"] == ""
    assert result["pages"] == 0


# --- _build_manifest_preview_data ---

def test_build_manifest_preview_data():
    info = {
        "catalog_title": "Catalog Title",
        "label": "Label Fallback",
        "description": "Desc",
        "pages": 100,
        "thumbnail": "thumb.jpg",
        "has_native_pdf": False,
    }
    result = _build_manifest_preview_data(info, "https://m.com/manifest", "doc123", "Gallica")
    assert result["label"] == "Catalog Title"
    assert result["id"] == "doc123"
    assert result["url"] == "https://m.com/manifest"
    assert result["library"] == "Gallica"
    assert result["pages"] == 100


def test_build_manifest_preview_data_fallback_label():
    info = {"label": "Fallback Label"}
    result = _build_manifest_preview_data(info, "https://m.com", None, "Oxford")
    assert result["label"] == "Fallback Label"
    assert result["id"] == "Fallback Label"


def test_build_manifest_preview_data_no_label():
    result = _build_manifest_preview_data({}, "https://m.com", None, "Oxford")
    assert result["label"] == "Senza Titolo"
    assert result["description"] == "Nessuna descrizione."


# --- _page_count_from_result ---

def test_page_count_explicit():
    assert _page_count_from_result({"raw": {"page_count": 42}}) == 42


def test_page_count_string_value():
    assert _page_count_from_result({"raw": {"page_count": "10"}}) == 10


def test_page_count_no_raw():
    assert _page_count_from_result({}) == 0


def test_page_count_non_dict_raw():
    assert _page_count_from_result({"raw": "not a dict"}) == 0


def test_page_count_invalid_page_count_falls_through():
    """Invalid page_count falls through to total_canvases."""
    assert _page_count_from_result({"raw": {"page_count": "invalid"}}) == 0


# --- _has_native_pdf_rendering ---

def test_has_pdf_by_format():
    manifest = {"rendering": [{"format": "application/pdf", "@id": "https://x.com/doc"}]}
    assert _has_native_pdf_rendering(manifest) is True


def test_has_pdf_by_url():
    manifest = {"rendering": [{"id": "https://x.com/doc.pdf"}]}
    assert _has_native_pdf_rendering(manifest) is True


def test_no_pdf_rendering():
    manifest = {"rendering": [{"format": "text/plain", "id": "https://x.com/doc.txt"}]}
    assert _has_native_pdf_rendering(manifest) is False


def test_no_rendering_key():
    assert _has_native_pdf_rendering({}) is False


def test_rendering_as_single_dict():
    manifest = {"rendering": {"format": "application/pdf", "@id": "https://x.com/d"}}
    assert _has_native_pdf_rendering(manifest) is True


def test_rendering_with_non_dict_entries():
    manifest = {"rendering": ["not-a-dict", {"format": "application/pdf", "id": "x"}]}
    assert _has_native_pdf_rendering(manifest) is True


# --- _pause_guard_response ---

def test_pause_guard_already_paused():
    assert _pause_guard_response("paused") is not None


def test_pause_guard_already_pausing():
    assert _pause_guard_response("pausing") is not None


def test_pause_guard_invalid_status():
    assert _pause_guard_response("completed") is not None


def test_pause_guard_running_returns_none():
    assert _pause_guard_response("running") is None


def test_pause_guard_queued_returns_none():
    assert _pause_guard_response("queued") is None


# --- _provider_supports_pagination ---

def test_provider_supports_pagination_true():
    provider = SimpleNamespace(search_strategy="archive_org")
    assert _provider_supports_pagination(provider) is True
    provider = SimpleNamespace(search_strategy="gallica")
    assert _provider_supports_pagination(provider) is True


def test_provider_supports_pagination_false():
    provider = SimpleNamespace(search_strategy="vatican")
    assert _provider_supports_pagination(provider) is False
    provider = SimpleNamespace(search_strategy="")
    assert _provider_supports_pagination(provider) is False


def test_provider_supports_pagination_none():
    provider = SimpleNamespace(search_strategy=None)
    assert _provider_supports_pagination(provider) is False


# --- _parse_ranges ---

def test_parse_ranges_simple():
    assert _parse_ranges("1,2,3") == {1, 2, 3}


def test_parse_ranges_range():
    assert _parse_ranges("1-5") == {1, 2, 3, 4, 5}


def test_parse_ranges_mixed():
    assert _parse_ranges("1-3,8,10-12") == {1, 2, 3, 8, 10, 11, 12}


def test_parse_ranges_reversed():
    assert _parse_ranges("5-1") == {1, 2, 3, 4, 5}


def test_parse_ranges_empty():
    assert _parse_ranges("") == set()
    assert _parse_ranges("   ") == set()


def test_parse_ranges_filters_zero():
    assert _parse_ranges("0,1,2") == {1, 2}


def test_parse_ranges_single():
    assert _parse_ranges("42") == {42}
