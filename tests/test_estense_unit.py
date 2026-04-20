"""Unit tests for the Biblioteca Estense (Jarvis) provider."""

import json
from pathlib import Path

from universal_iiif_core.resolvers.estense import (
    JARVIS_BASE,
    EstenseResolver,
    build_manifest_url,
    build_viewer_url,
    extract_uuid,
)
from universal_iiif_core.resolvers.search import _common as _search_common
from universal_iiif_core.resolvers.search.estense import search_estense


def _fixture_bytes() -> bytes:
    return (Path(__file__).parent / "fixtures" / "estense_search_sample.json").read_bytes()


_UUID = "08bea380-6af7-4b77-aebe-e81fa315e8f4"


class _DummyResp:
    def __init__(self, content_bytes: bytes, status_code: int = 200):
        self.content = content_bytes
        self.status_code = status_code
        self.headers = {"Content-Type": "application/hal+json"}

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return json.loads(self.content)


def _patch_http_client(monkeypatch, fake_get):
    class _Client:
        def get(self, *args, **kwargs):
            return fake_get(*args, **kwargs)

    monkeypatch.setattr(_search_common, "_http_client_cache", _Client())


def test_extract_uuid_from_v2_manifest_url():
    url = f"{JARVIS_BASE}/meta/iiif/{_UUID}/manifest"
    assert extract_uuid(url) == _UUID


def test_extract_uuid_from_v3_manifest_url():
    url = f"{JARVIS_BASE}/meta/iiif/v3/{_UUID}/manifest"
    assert extract_uuid(url) == _UUID


def test_extract_uuid_from_mirador_viewer_url():
    inner = f"{JARVIS_BASE}/meta/iiif/{_UUID}/manifest"
    url = f"{JARVIS_BASE}/images/viewers/mirador/?manifest={inner.replace(':', '%3A').replace('/', '%2F')}"
    assert extract_uuid(url) == _UUID


def test_extract_uuid_from_bare_uuid():
    assert extract_uuid(_UUID) == _UUID
    assert extract_uuid(_UUID.upper()) == _UUID  # case-insensitive


def test_extract_uuid_rejects_unknown_input():
    assert extract_uuid("") is None
    assert extract_uuid("not a uuid") is None
    assert extract_uuid("https://example.org/manifest.json") is None
    assert extract_uuid("https://jarvis.edl.beniculturali.it/meta/") is None


def test_build_manifest_and_viewer_urls():
    v2 = build_manifest_url(_UUID)
    v3 = build_manifest_url(_UUID, v3=True)
    assert v2.endswith(f"/meta/iiif/{_UUID}/manifest")
    assert v3.endswith(f"/meta/iiif/v3/{_UUID}/manifest")
    assert f"manifest={v3}" in build_viewer_url(_UUID)


def test_resolver_returns_manifest_for_known_inputs():
    r = EstenseResolver()
    assert r.can_resolve(_UUID)
    manifest_url, uuid = r.get_manifest_url(_UUID)
    assert uuid == _UUID
    assert manifest_url == build_manifest_url(_UUID)


def test_resolver_rejects_unrelated_inputs():
    r = EstenseResolver()
    assert not r.can_resolve("")
    assert not r.can_resolve("https://gallica.bnf.fr/ark:/12148/btv1b123")


def test_search_parses_live_fixture_and_surfaces_pagination(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        return _DummyResp(_fixture_bytes())

    _patch_http_client(monkeypatch, fake_get)

    results = search_estense("dante", max_results=2, page=1)
    assert len(results) == 2
    assert "findBySgttOrAutnOrPressmark" in captured["url"]
    assert "text=dante" in captured["url"]
    assert "page=0" in captured["url"]  # Spring Pageable is 0-based

    first = results[0]
    assert first["library"] == "Biblioteca Estense (Modena)"
    assert first["manifest"].startswith(JARVIS_BASE)
    assert "/meta/iiif/" in first["manifest"]
    assert first["manifest_status"] == "pending"

    raw = first.get("raw") or {}
    assert raw.get("uuid")
    assert isinstance(raw.get("_search_total_results"), int) and raw["_search_total_results"] > 0
    assert isinstance(raw.get("_search_total_pages"), int) and raw["_search_total_pages"] > 0
    assert raw.get("_search_page") == 1


def test_search_returns_empty_on_blank_query(monkeypatch):
    def fake_get(url, **kwargs):
        raise AssertionError("search should not be invoked for blank query")

    _patch_http_client(monkeypatch, fake_get)
    assert search_estense("   ", max_results=5) == []


def test_search_maps_page_argument_to_zero_based(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        return _DummyResp(_fixture_bytes())

    _patch_http_client(monkeypatch, fake_get)
    search_estense("dante", max_results=2, page=4)
    assert "page=3" in captured["url"]
