from __future__ import annotations

from universal_iiif_core.http_client import HTTPClient
from universal_iiif_core.resolvers import discovery


class _Resp:
    def __init__(
        self,
        *,
        status_code: int = 200,
        text: str = "",
        headers: dict[str, str] | None = None,
    ):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _patch_http_client(monkeypatch, fake_get):
    """Replace the discovery module's cached HTTPClient with one backed by *fake_get*."""

    class _MockClient:
        def get(self, *args, **kwargs):
            return fake_get(*args, **kwargs)

    monkeypatch.setattr(discovery, "_http_client_cache", _MockClient())


def test_search_loc_maps_loc_item_urls_to_manifests(monkeypatch):
    """LOC search should keep only entries that map to canonical IIIF item manifests."""
    payload = {
        "results": [
            {
                "id": "https://www.loc.gov/item/2021668145/",
                "title": "Sample LOC title",
                "image_url": ["https://example.org/thumb.jpg"],
            },
            {"id": "https://www.congress.gov/member/dante-fascell/F000041", "title": "Not IIIF"},
        ]
    }

    monkeypatch.setattr(HTTPClient, "get_json", lambda _self, *_a, **_k: payload)

    results = discovery.search_loc("dante", max_results=5)
    assert len(results) == 1
    assert results[0]["id"] == "2021668145"
    assert results[0]["manifest"] == "https://www.loc.gov/item/2021668145/manifest.json"


def test_search_harvard_extracts_iiif_manifest_tokens(monkeypatch):
    """Harvard search should surface manifests when payload contains IIIF manifest tokens."""
    payload = {
        "items": {
            "mods": [
                {
                    "note": [
                        "https://iiif.lib.harvard.edu/manifests/view/ids:504952783",
                        "https://iiif.lib.harvard.edu/manifests/drs:12345678",
                    ]
                }
            ]
        }
    }

    monkeypatch.setattr(HTTPClient, "get_json", lambda _self, *_a, **_k: payload)

    results = discovery.search_harvard("iiif", max_results=10)
    ids = {str(item["id"]) for item in results}
    assert "ids:504952783" in ids
    assert "drs:12345678" in ids


def test_search_harvard_prefers_structured_title_and_preview(monkeypatch):
    """Harvard search should read titleInfo and ids preview URL from structured records."""
    payload = {
        "items": {
            "mods": [
                {
                    "titleInfo": {"title": "Bol'shoi Ferganskii kanal"},
                    "location": {
                        "url": [
                            {"@access": "raw object", "#text": "https://iiif.lib.harvard.edu/manifests/drs:494880795"},
                            {
                                "@access": "preview",
                                "#text": "https://ids.lib.harvard.edu/ids/iiif/451239291/full/,150/0/default.jpg",
                            },
                        ]
                    },
                }
            ]
        }
    }

    monkeypatch.setattr(HTTPClient, "get_json", lambda _self, *_a, **_k: payload)
    results = discovery.search_harvard("manuscript", max_results=5)

    assert len(results) == 1
    assert results[0]["id"] == "drs:494880795"
    assert results[0]["title"] == "Bol'shoi Ferganskii kanal"
    assert "ids.lib.harvard.edu/ids/iiif/" in results[0]["thumbnail"]


def test_search_harvard_uses_fallback_query_when_primary_has_no_iiif(monkeypatch):
    """Harvard search should keep primary results and enrich with IIIF fallback query."""
    calls: list[str] = []

    def _fake_get_json(_self, url, **_kwargs):  # noqa: ANN001
        calls.append(url)
        if "q=dante+iiif.lib.harvard.edu" in url:
            return {"location": {"url": "https://iiif.lib.harvard.edu/manifests/drs:87654321"}}
        return {
            "items": {
                "mods": [
                    {
                        "titleInfo": {"title": "Dante"},
                        "location": {"url": "https://id.lib.harvard.edu/alma/990126667270203941/catalog"},
                    }
                ]
            }
        }

    monkeypatch.setattr(HTTPClient, "get_json", _fake_get_json)
    results = discovery.search_harvard("dante", max_results=10)

    assert any("q=dante+iiif.lib.harvard.edu" in call for call in calls)
    ids = {str(item["id"]) for item in results}
    assert "990126667270203941" in ids
    assert "drs:87654321" in ids


def test_search_harvard_keeps_non_iiif_records_as_consultation_entries(monkeypatch):
    """Harvard non-IIIF catalog records should remain visible as consult-only results."""
    payload = {
        "items": {
            "mods": [
                {
                    "titleInfo": {"title": "Opera noua de Achille Marozzo"},
                    "location": {"url": "https://id.lib.harvard.edu/alma/990126667270203941/catalog"},
                }
            ]
        }
    }
    monkeypatch.setattr(HTTPClient, "get_json", lambda _self, *_a, **_k: payload)

    results = discovery.search_harvard("achille marozzo", max_results=5)
    assert len(results) == 1
    assert results[0]["id"] == "990126667270203941"
    assert results[0]["viewer_url"] == "https://id.lib.harvard.edu/alma/990126667270203941/catalog"
    assert results[0].get("manifest", "") == ""
    assert bool(results[0]["raw"].get("consult_online_only")) is True


def test_search_cambridge_parses_view_links(monkeypatch):
    """Cambridge search should map `/view/...` links to CUDL IIIF manifests."""
    html = """
    <a href="/view/MS-ADD-03996">MS ADD 03996</a>
    <a href="/view/MS-ADD-12345">MS ADD 12345</a>
    """
    _patch_http_client(monkeypatch, lambda *_a, **_k: _Resp(status_code=200, text=html))

    results = discovery.search_cambridge("ms add", max_results=10)
    assert len(results) == 2
    assert results[0]["manifest"] == "https://cudl.lib.cam.ac.uk/iiif/MS-ADD-03996"


def test_search_cambridge_handles_waf_challenge(monkeypatch):
    """Cambridge WAF challenge responses should produce a browser handoff result."""
    _patch_http_client(
        monkeypatch,
        lambda *_a, **_k: _Resp(status_code=202, text="", headers={"x-amzn-waf-action": "challenge"}),
    )

    results = discovery.search_cambridge("dante", max_results=10)
    assert len(results) == 1
    assert results[0]["manifest"] == ""
    assert "cudl.lib.cam.ac.uk/search?keyword=dante" in results[0]["viewer_url"]
    assert bool(results[0]["raw"].get("consult_online_only")) is True


def test_search_cambridge_inline_id_fallback():
    """Cambridge search should resolve inline shelfmark-style IDs without endpoint search."""
    results = discovery.search_cambridge("please open MS-ADD-03996", max_results=10)
    assert len(results) == 1
    assert results[0]["id"] == "MS-ADD-03996"


def test_search_cambridge_signature_normalization_without_http():
    """Cambridge search should normalize shelfmark punctuation into resolver-compatible IDs."""
    results = discovery.search_cambridge("MS Add.9597/9/1", max_results=10)
    assert len(results) == 1
    assert results[0]["id"] == "MS-ADD-09597-00009-00001"


def test_search_cambridge_ms_free_text_does_not_take_direct_path(monkeypatch):
    """`MS ...` free text without numeric shelfmark parts should not become a direct manifest ID."""
    _patch_http_client(monkeypatch, lambda *_a, **_k: _Resp(status_code=200, text="<html></html>"))
    results = discovery.search_cambridge("MS Add Dante", max_results=10)
    assert len(results) == 1
    assert results[0]["manifest"] == ""
    assert "search?keyword=MS+Add+Dante" in results[0]["viewer_url"]


def test_search_heidelberg_maps_diglit_links(monkeypatch):
    """Heidelberg search should map `diglit/<id>` links to IIIF manifest URLs."""
    html = '<a href="https://digi.ub.uni-heidelberg.de/diglit/cpg123">Cod. Pal. germ. 123</a>'
    _patch_http_client(monkeypatch, lambda *_a, **_k: _Resp(status_code=200, text=html))

    results = discovery.search_heidelberg("cpg", max_results=10)
    assert len(results) == 1
    assert results[0]["id"] == "cpg123"
    assert results[0]["manifest"] == "https://digi.ub.uni-heidelberg.de/diglit/iiif/cpg123/manifest.json"


def test_search_heidelberg_returns_browser_handoff_when_no_hits(monkeypatch):
    """Heidelberg free-text without diglit hits should degrade to a consult-only browser result."""
    _patch_http_client(monkeypatch, lambda *_a, **_k: _Resp(status_code=200, text="<html></html>"))

    results = discovery.search_heidelberg("dante", max_results=10)
    assert len(results) == 1
    assert results[0]["manifest"] == ""
    assert "search.cgi?query=dante" in results[0]["viewer_url"]
    assert bool(results[0]["raw"].get("consult_online_only")) is True


def test_search_heidelberg_inline_id_fallback():
    """Heidelberg search should resolve inline cpg/cpl IDs without site-search dependency."""
    results = discovery.search_heidelberg("manoscritto cpg123", max_results=10)
    assert len(results) == 1
    assert results[0]["id"] == "cpg123"


def test_search_heidelberg_cod_pal_germ_normalization():
    """Heidelberg search should normalize `Cod. Pal. germ.` shelfmarks into cpg IDs."""
    results = discovery.search_heidelberg("Cod. Pal. germ. 123", max_results=10)
    assert len(results) == 1
    assert results[0]["id"] == "cpg123"
