from __future__ import annotations

import requests

from universal_iiif_core.resolvers import discovery


class _Resp:
    def __init__(self, *, json_data: dict | None = None, status_code: int = 200):
        self._json_data = json_data or {}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data


def test_search_bodleian_blank_input_returns_empty():
    """Blank query must return an empty result list without HTTP calls."""
    assert discovery.search_bodleian("") == []


def test_search_bodleian_maps_jsonld_member_results(monkeypatch):
    """Bodleian JSON-LD search results should map to canonical SearchResult entries."""
    payload = {
        "@context": "https://digital.bodleian.ox.ac.uk/api/1/context.json",
        "member": [
            {
                "type": "Object",
                "id": "https://digital.bodleian.ox.ac.uk/objects/cb1df5f1-7435-468b-8860-d56db988b929/",
                "shelfmark": "Bodleian Library MS. Canon. Ital. 108",
                "surfaceCount": 66,
                "thumbnail": [
                    {
                        "id": (
                            "https://iiif.bodleian.ox.ac.uk/iiif/image/"
                            "03b0efbc-9307-4597-9bb8-8fe2078e2181/full/255,/0/default.jpg"
                        )
                    }
                ],
                "manifest": {
                    "id": "https://iiif.bodleian.ox.ac.uk/iiif/manifest/cb1df5f1-7435-468b-8860-d56db988b929.json"
                },
                "displayFields": {
                    "title": ["Divine Comedy."],
                    "people": ["<em>Dante</em>"],
                    "dateStatement": ["14th century, second half"],
                    "snippet": ["... <em>Dante</em> ..."],
                },
            }
        ],
    }

    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: ARG001
        assert url == "https://digital.bodleian.ox.ac.uk/search/"
        assert params == {"q": "dante"}
        assert headers["Accept"] == "application/ld+json"
        return _Resp(json_data=payload)

    monkeypatch.setattr(discovery.requests, "get", fake_get)

    results = discovery.search_bodleian("dante", max_results=5)
    assert len(results) == 1

    first = results[0]
    assert first["id"] == "cb1df5f1-7435-468b-8860-d56db988b929"
    assert first["library"] == "Bodleian"
    assert first["title"] == "Divine Comedy."
    assert first["author"] == "Dante"
    assert first["date"] == "14th century, second half"
    assert first["description"] == "... Dante ..."
    assert first["publisher"] == "Bodleian Libraries"
    assert first["manifest"] == "https://iiif.bodleian.ox.ac.uk/iiif/manifest/cb1df5f1-7435-468b-8860-d56db988b929.json"
    assert first["thumbnail"].startswith("https://iiif.bodleian.ox.ac.uk/iiif/image/")
    assert (
        first["raw"]["viewer_url"] == "https://digital.bodleian.ox.ac.uk/objects/cb1df5f1-7435-468b-8860-d56db988b929/"
    )
