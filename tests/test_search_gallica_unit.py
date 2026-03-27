from pathlib import Path

from universal_iiif_core.resolvers import discovery
from universal_iiif_core.resolvers.discovery import search_gallica


class _DummyResp:
    def __init__(self, content_bytes: bytes):
        self.content = content_bytes
        self.status_code = 200
        self.headers = {"Content-Type": "application/xml"}

    def raise_for_status(self):
        return None


def _patch_http_client(monkeypatch, fake_get):
    """Replace the discovery module's cached HTTPClient with one backed by *fake_get*."""

    class _MockClient:
        def get(self, *args, **kwargs):
            return fake_get(*args, **kwargs)

    monkeypatch.setattr(discovery, "_http_client_cache", _MockClient())


def test_search_gallica_parsing(monkeypatch):
    """Parse a saved SRU XML response and ensure we extract ARK and title."""
    fixture = Path(__file__).parent / "fixtures" / "gallica_sample.xml"
    content = fixture.read_bytes()

    def fake_get(url, **kwargs):
        return _DummyResp(content)

    _patch_http_client(monkeypatch, fake_get)

    results = search_gallica("dante", max_records=5)
    assert results, "Expected at least one result from fixture"
    first = results[0]
    assert first["id"] == "btv1b10033406t"
    assert "Dante" in first["title"] or "Dante" in first["title"].capitalize()


def test_search_gallica_applies_printed_filter_when_requested(monkeypatch):
    """Printed filter should retain only records marked as printed types."""
    fixture = Path(__file__).parent / "fixtures" / "gallica_sample.xml"
    content = fixture.read_bytes()
    calls: list[str] = []

    def fake_get(url, params=None, **kwargs):
        calls.append(str((params or {}).get("query") or ""))
        return _DummyResp(content)

    _patch_http_client(monkeypatch, fake_get)

    results = search_gallica("Les voyages du seigneur de Villamont", max_records=5, gallica_type_filter="printed")
    assert results == []
    assert len(calls) == 1
    assert calls[0].startswith('dc.title all "')


def test_search_gallica_default_is_free_search(monkeypatch):
    """Default search should not force manuscript-only filter."""
    fixture = Path(__file__).parent / "fixtures" / "gallica_sample.xml"
    content = fixture.read_bytes()
    calls: list[str] = []

    def fake_get(url, params=None, **kwargs):
        calls.append(str((params or {}).get("query") or ""))
        return _DummyResp(content)

    _patch_http_client(monkeypatch, fake_get)
    results = search_gallica("villamont", max_records=5)
    assert results
    assert calls
    assert calls[0] == 'dc.title all "villamont"'


def test_search_gallica_applies_manuscript_filter_when_requested(monkeypatch):
    """Manuscript filter should keep manuscript records from parsed dc:type."""
    fixture = Path(__file__).parent / "fixtures" / "gallica_sample.xml"
    content = fixture.read_bytes()
    calls: list[str] = []

    def fake_get(url, params=None, **kwargs):
        calls.append(str((params or {}).get("query") or ""))
        return _DummyResp(content)

    _patch_http_client(monkeypatch, fake_get)
    results = search_gallica("villamont", max_records=5, gallica_type_filter="manuscrit")
    assert results
    assert calls
    assert calls[0] == 'dc.title all "villamont"'


def test_search_gallica_printed_filter_matches_printed_monograph(monkeypatch):
    """Printed filter should match records with monographie imprimée / printed monograph."""
    printed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<srw:searchRetrieveResponse
  xmlns:srw="http://www.loc.gov/zing/srw/"
  xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <srw:records>
    <srw:record>
      <srw:recordData>
        <oai_dc:dc>
          <dc:title>Les Voyages du seigneur de Villamont</dc:title>
          <dc:identifier>https://gallica.bnf.fr/ark:/12148/bpt6k87126379</dc:identifier>
          <dc:type>text</dc:type>
          <dc:type>monographie imprimée</dc:type>
          <dc:type>printed monograph</dc:type>
        </oai_dc:dc>
      </srw:recordData>
    </srw:record>
  </srw:records>
</srw:searchRetrieveResponse>
""".encode()

    def fake_get(url, **kwargs):
        return _DummyResp(printed_xml)

    _patch_http_client(monkeypatch, fake_get)
    results = search_gallica("villamont", max_records=5, gallica_type_filter="printed")
    assert results
    assert results[0]["id"] == "bpt6k87126379"
