from __future__ import annotations

import requests

from universal_iiif_core.resolvers import discovery


class _Resp:
    def __init__(self, *, text: str = "", status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_search_ecodices_blank_input_returns_empty():
    """Blank query must return an empty result list without HTTP calls."""
    assert discovery.search_ecodices("") == []


def test_search_ecodices_maps_html_results(monkeypatch):
    """e-codices HTML search results should map to canonical SearchResult entries."""
    html = """
    <div class="search-result">
      <a href="https://www.e-codices.unifr.ch/en/searchresult/list/one/csg/0573" class="search-result-preview-image">
        <iiif-image image-server-base-url="https://www.e-codices.unifr.ch/loris"
                    image-file-path="csg/csg-0573/csg-0573_002.jp2"></iiif-image>
      </a>
      <div class="collection-shelfmark">
        St. Gallen, Stiftsbibliothek, Cod. Sang. 573
      </div>
      <div class="document-headline">
        Dante, Commedia
      </div>
      <p class="document-summary-search">
        Manuscript mentioning <em>Dante</em>.
        <span class="summary-author" data-original-title="Stiftsbibliothek St. Gallen"> <em>(sg)</em></span>
      </p>
      <div class="btn-box clearfix">
        <a href="https://www.e-codices.unifr.ch/en/searchresult/list/one/csg/0573">Overview</a>
        <a href="https://www.e-codices.unifr.ch/en/csg/0573">Facsimile</a>
        <a href="https://www.e-codices.unifr.ch/en/description/csg/0573/Hendrix">Description</a>
      </div>
    </div>
    """

    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: ARG001
        assert url == "https://www.e-codices.unifr.ch/en/search/all"
        assert params["sQueryString"] == "dante"
        assert params["sSearchField"] == "fullText"
        return _Resp(text=html)

    monkeypatch.setattr(discovery.requests, "get", fake_get)

    results = discovery.search_ecodices("dante", max_results=5)
    assert len(results) == 1

    first = results[0]
    assert first["id"] == "csg-0573"
    assert first["library"] == "e-codices"
    assert first["title"] == "Dante, Commedia"
    assert first["description"] == "Manuscript mentioning Dante."
    assert first["publisher"] == "St. Gallen, Stiftsbibliothek, Cod. Sang. 573"
    assert first["manifest"] == "https://www.e-codices.unifr.ch/metadata/iiif/csg-0573/manifest.json"
    assert (
        first["thumbnail"]
        == "https://www.e-codices.unifr.ch/loris/csg/csg-0573/csg-0573_002.jp2/full/180,/0/default.jpg"
    )
    assert first["raw"]["viewer_url"] == "https://www.e-codices.unifr.ch/en/csg/0573"
