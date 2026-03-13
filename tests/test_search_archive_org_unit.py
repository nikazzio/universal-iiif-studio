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


def test_search_archive_org_blank_input_returns_empty():
    """Blank query must return an empty result list without HTTP calls."""
    assert discovery.search_archive_org("") == []


def test_search_archive_org_parses_advancedsearch_docs(monkeypatch):
    """Archive.org search should map advancedsearch docs into SearchResult entries."""
    payload = {
        "response": {
            "docs": [
                {
                    "identifier": "b29000427_0001",
                    "title": "Subject-index of the London Library",
                    "creator": ["Charles Theodore Hagberg Wright"],
                    "date": "1909",
                    "mediatype": "texts",
                }
            ]
        }
    }

    def fake_get(url, params=None, headers=None, timeout=None):  # noqa: ARG001
        assert "advancedsearch.php" in url
        assert "mediatype:texts" in str((params or {}).get("q") or "")
        return _Resp(json_data=payload)

    monkeypatch.setattr(discovery.requests, "get", fake_get)

    results = discovery.search_archive_org("london library", max_results=5)
    assert len(results) == 1

    first = results[0]
    assert first["id"] == "b29000427_0001"
    assert first["library"] == "Archive.org"
    assert first["manifest"] == "https://iiif.archive.org/iiif/b29000427_0001/manifest.json"
    assert first["publisher"] == "Internet Archive"
    assert first["date"] == "1909"
    assert "Subject-index" in first["title"]
    assert "archive.org/details/b29000427_0001" in first["raw"]["viewer_url"]
    assert first["thumbnail"].startswith("https://iiif.archive.org/image/iiif/2/")

