from __future__ import annotations

from universal_iiif_core.resolvers import discovery


class _Resp:
    def __init__(self, *, text: str = "", json_data: dict | None = None, status_code: int = 200):
        self.text = text
        self._json_data = json_data or {}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data


def test_search_institut_blank_input_returns_empty():
    """Blank query must return an empty result list without HTTP calls."""
    assert discovery.search_institut("") == []


def test_search_institut_extracts_results_and_manifest_metadata(monkeypatch):
    """Search parser must deduplicate IDs and hydrate metadata from manifests."""
    html = """
    <div class="records-list">
      <a href="/records/item/17837-oeuvres-de-brantome">Oeuvres de Brantôme</a>
      <a href="/records/item/17837-oeuvres-de-brantome">Duplicate</a>
      <a href="/records/item/18000-manuscrit-test"><span>Manuscrit</span> test</a>
    </div>
    """

    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: ARG001
        if "records/default" in url:
            return _Resp(text=html)
        if "/iiif/17837/manifest" in url:
            return _Resp(
                json_data={
                    "label": "Oeuvres de Brantôme",
                    "metadata": [{"label": "creator", "value": "Pierre de Bourdeille"}],
                    "thumbnail": {"@id": "https://bibnum.institutdefrance.fr/thumb/17837.jpg"},
                }
            )
        if "/iiif/18000/manifest" in url:
            return _Resp(status_code=404)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(discovery.requests, "get", fake_get)

    results = discovery.search_institut("brantome", max_results=5)

    assert len(results) == 2

    first = results[0]
    assert first["id"] == "17837"
    assert first["title"] == "Oeuvres de Brantôme"
    assert first["author"] == "Pierre de Bourdeille"
    assert first["library"] == "Institut de France"
    assert first["manifest"] == "https://bibnum.institutdefrance.fr/iiif/17837/manifest"

    second = results[1]
    assert second["id"] == "18000"
    assert second["title"] == "Manuscrit test"
    assert second["library"] == "Institut de France"
    assert second["manifest"] == "https://bibnum.institutdefrance.fr/iiif/18000/manifest"
