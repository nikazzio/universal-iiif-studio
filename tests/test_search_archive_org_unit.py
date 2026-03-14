from __future__ import annotations

from universal_iiif_core.providers import get_provider
from universal_iiif_core.resolvers import discovery
from universal_iiif_core.resolvers.archive_org import ArchiveOrgResolver


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

    def fake_get_json(url, headers=None, retries=3):  # noqa: ARG001
        if "advancedsearch.php" in url:
            assert "mediatype%3Atexts" in url
            return payload
        assert url == "https://iiif.archive.org/iiif/b29000427_0001/manifest.json"
        return {"type": "Manifest", "items": [{}]}

    monkeypatch.setattr(discovery, "get_json", fake_get_json)

    results = discovery.search_archive_org("london library", max_results=5)
    assert len(results) == 1

    first = results[0]
    assert first["id"] == "b29000427_0001"
    assert first["library"] == "Archive.org"
    assert first["manifest"] == "https://iiif.archive.org/iiif/b29000427_0001/manifest.json"
    assert first["publisher"] == "Internet Archive"
    assert first["date"] == "1909"
    assert "Subject-index" in first["title"]
    assert first["viewer_url"] == "https://archive.org/details/b29000427_0001"
    assert "archive.org/details/b29000427_0001" in first["raw"]["viewer_url"]
    assert first["thumbnail"].startswith("https://iiif.archive.org/image/iiif/2/")


def test_search_archive_org_skips_broken_manifests(monkeypatch):
    """Archive search should drop results whose IIIF manifest probe fails."""
    payload = {
        "response": {
            "docs": [
                {
                    "identifier": "broken_item_0001",
                    "title": "Broken item",
                    "creator": ["Archive Bot"],
                    "date": "1901",
                    "mediatype": "texts",
                },
                {
                    "identifier": "working_item_0002",
                    "title": "Working item",
                    "creator": ["Archive Bot"],
                    "date": "1902",
                    "mediatype": "texts",
                },
            ]
        }
    }

    def fake_get_json(url, headers=None, retries=3):  # noqa: ARG001
        if "advancedsearch.php" in url:
            return payload
        if url.endswith("/broken_item_0001/manifest.json"):
            return None
        if url.endswith("/working_item_0002/manifest.json"):
            return {"type": "Manifest", "items": [{}]}
        raise AssertionError(f"Unexpected URL {url}")

    monkeypatch.setattr(discovery, "get_json", fake_get_json)

    results = discovery.search_archive_org("archive bot", max_results=2)
    assert len(results) == 1
    assert results[0]["id"] == "working_item_0002"


def test_archive_org_resolver_rejects_ambiguous_free_text():
    """Generic free-text terms should not be misread as Archive identifiers."""
    resolver = ArchiveOrgResolver()

    assert resolver.can_resolve("dante") is False
    assert resolver.get_manifest_url("dante") == (None, None)
    assert resolver.can_resolve("b29000427_0001") is True


def test_resolve_provider_input_archive_search_first_skips_bogus_direct_resolution(monkeypatch):
    """Archive provider must not turn generic search terms into manifest URLs."""
    provider = get_provider("Archive.org")

    monkeypatch.setattr(discovery, "_search_with_provider", lambda *_args, **_kwargs: [])

    def _fail_if_called(*_args, **_kwargs):
        raise AssertionError("resolve_shelfmark should not be called for ambiguous free-text")

    monkeypatch.setattr(discovery, "resolve_shelfmark", _fail_if_called)

    result = discovery.resolve_provider_input("Archive.org", "dante")
    assert result.provider == provider
    assert result.status == "not_found"


def test_resolve_provider_input_archive_search_first_falls_back_to_direct_url(monkeypatch):
    """Archive provider should still resolve direct URLs after search misses."""
    monkeypatch.setattr(discovery, "_search_with_provider", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        discovery,
        "resolve_shelfmark",
        lambda library, text: (
            "https://iiif.archive.org/iiif/b29000427_0001/manifest.json",
            "b29000427_0001",
        )
        if library == "Archive.org" and text == "https://archive.org/details/b29000427_0001"
        else (None, None),
    )

    result = discovery.resolve_provider_input("Archive.org", "https://archive.org/details/b29000427_0001")
    assert result.status == "manifest"
    assert result.doc_id == "b29000427_0001"
    assert result.manifest_url == "https://iiif.archive.org/iiif/b29000427_0001/manifest.json"
