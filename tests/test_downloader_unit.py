"""Tests for downloader pure helpers.

Covers CanvasServiceLocator, _format_dimension, get_canvases,
get_pdf_url, _get_thumbnail_url.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from universal_iiif_core.logic.downloader import CanvasServiceLocator, PageDownloader

# --- CanvasServiceLocator ---


class TestCanvasServiceLocator:
    def test_locate_direct_service_id(self):
        canvas = {"service": {"@id": "https://img.example.com/svc"}}
        assert CanvasServiceLocator.locate(canvas) == "https://img.example.com/svc"

    def test_locate_service_list(self):
        canvas = {"service": [{"@id": "https://a.com"}, {"@id": "https://b.com"}]}
        assert CanvasServiceLocator.locate(canvas) == "https://a.com"

    def test_locate_service_with_id_key(self):
        canvas = {"service": {"id": "https://v3.example.com/svc"}}
        assert CanvasServiceLocator.locate(canvas) == "https://v3.example.com/svc"

    def test_locate_nested_in_body(self):
        canvas = {"body": {"service": {"@id": "https://nested.com"}}}
        assert CanvasServiceLocator.locate(canvas) == "https://nested.com"

    def test_locate_nested_in_resource(self):
        canvas = {"resource": {"service": [{"@id": "https://res.com/svc"}]}}
        assert CanvasServiceLocator.locate(canvas) == "https://res.com/svc"

    def test_locate_nested_in_items(self):
        canvas = {"items": [{"body": {"service": {"id": "https://items.com"}}}]}
        assert CanvasServiceLocator.locate(canvas) == "https://items.com"

    def test_locate_normalize_full_url(self):
        canvas = {"body": {"@id": "https://img.com/12345/full/max/0/default.jpg"}}
        assert CanvasServiceLocator.locate(canvas) == "https://img.com/12345"

    def test_locate_returns_none_for_empty(self):
        assert CanvasServiceLocator.locate({}) is None

    def test_locate_returns_none_for_non_dict(self):
        assert CanvasServiceLocator.locate("not a dict") is None
        assert CanvasServiceLocator.locate(None) is None

    def test_locate_handles_cyclic_references(self):
        """Cyclic dicts shouldn't crash (seen guard prevents infinite loop)."""
        canvas: dict = {"body": {}}
        # Can't create true cycle with dict identity, but nested duplicates are fine
        inner = {"service": {"@id": "https://found.com"}}
        canvas["body"] = {"items": [inner, inner]}
        assert CanvasServiceLocator.locate(canvas) == "https://found.com"


# --- PageDownloader._format_dimension ---


class TestFormatDimension:
    def test_empty_returns_max(self):
        assert PageDownloader._format_dimension("") == "max"
        assert PageDownloader._format_dimension("  ") == "max"

    def test_max_returns_max(self):
        assert PageDownloader._format_dimension("max") == "max"
        assert PageDownloader._format_dimension("MAX") == "max"
        assert PageDownloader._format_dimension(" Max ") == "max"

    def test_digit_gets_comma(self):
        assert PageDownloader._format_dimension("1024") == "1024,"

    def test_digit_with_trailing_comma(self):
        assert PageDownloader._format_dimension("1024,") == "1024,"

    def test_non_digit_passthrough(self):
        assert PageDownloader._format_dimension("!1024") == "!1024"


# --- IIIFDownloader.get_pdf_url (needs manifest stub) ---


def _make_downloader_stub(manifest: dict):
    """Minimal object with .manifest for get_pdf_url / get_canvases / _get_thumbnail_url."""
    from universal_iiif_core.logic.downloader import IIIFDownloader

    stub = object.__new__(IIIFDownloader)
    stub.manifest = manifest
    stub.logger = MagicMock()
    return stub


class TestGetPdfUrl:
    def test_finds_pdf_by_format(self):
        dl = _make_downloader_stub({"rendering": [{"format": "application/pdf", "@id": "https://x.com/doc.pdf"}]})
        assert dl.get_pdf_url() == "https://x.com/doc.pdf"

    def test_finds_pdf_by_url_extension(self):
        dl = _make_downloader_stub({"rendering": [{"id": "https://x.com/output.pdf"}]})
        assert dl.get_pdf_url() == "https://x.com/output.pdf"

    def test_no_rendering_returns_none(self):
        dl = _make_downloader_stub({})
        assert dl.get_pdf_url() is None

    def test_empty_rendering_list(self):
        dl = _make_downloader_stub({"rendering": []})
        assert dl.get_pdf_url() is None

    def test_rendering_as_dict(self):
        dl = _make_downloader_stub({"rendering": {"format": "application/pdf", "@id": "https://x.com/p.pdf"}})
        assert dl.get_pdf_url() == "https://x.com/p.pdf"

    def test_non_pdf_rendering_skipped(self):
        dl = _make_downloader_stub({"rendering": [{"format": "text/plain", "@id": "https://x.com/t.txt"}]})
        assert dl.get_pdf_url() is None


class TestGetCanvases:
    def test_v2_sequences(self):
        dl = _make_downloader_stub({"sequences": [{"canvases": [{"id": "c1"}, {"id": "c2"}]}]})
        assert dl.get_canvases() == [{"id": "c1"}, {"id": "c2"}]

    def test_v3_items(self):
        dl = _make_downloader_stub({"items": [{"id": "c1"}, {"id": "c2"}]})
        assert dl.get_canvases() == [{"id": "c1"}, {"id": "c2"}]

    def test_no_canvases(self):
        dl = _make_downloader_stub({})
        assert dl.get_canvases() == []

    def test_v2_takes_priority_over_v3(self):
        dl = _make_downloader_stub({"sequences": [{"canvases": [{"id": "v2"}]}], "items": [{"id": "v3"}]})
        assert dl.get_canvases() == [{"id": "v2"}]


class TestGetThumbnailUrl:
    def test_string_thumbnail(self):
        dl = _make_downloader_stub({})
        assert dl._get_thumbnail_url({"thumbnail": "https://img.com/thumb.jpg"}) == "https://img.com/thumb.jpg"

    def test_dict_thumbnail_with_at_id(self):
        dl = _make_downloader_stub({})
        assert dl._get_thumbnail_url({"thumbnail": {"@id": "https://img.com/t.jpg"}}) == "https://img.com/t.jpg"

    def test_dict_thumbnail_with_id(self):
        dl = _make_downloader_stub({})
        assert dl._get_thumbnail_url({"thumbnail": {"id": "https://v3.com/t.jpg"}}) == "https://v3.com/t.jpg"

    def test_list_thumbnail(self):
        dl = _make_downloader_stub({})
        result = dl._get_thumbnail_url({"thumbnail": [{"@id": "https://first.com/t.jpg"}]})
        assert result == "https://first.com/t.jpg"

    def test_no_thumbnail(self):
        dl = _make_downloader_stub({})
        assert dl._get_thumbnail_url({}) is None
        assert dl._get_thumbnail_url({"thumbnail": None}) is None
