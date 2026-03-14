from universal_iiif_core.discovery.orchestrator import resolve_provider_input


def test_orchestrator_search_first_prefers_search_results():
    """Search-first providers should return search hits without forcing direct resolution."""
    calls: dict[str, int] = {"resolve": 0}

    def _resolve_shelfmark(_library: str, _value: str):
        calls["resolve"] += 1
        return "https://example.org/manifest.json", "DOC1"

    result = resolve_provider_input(
        "Gallica",
        "dante",
        search_handlers={"gallica": lambda _query, _payload: [{"id": "R1", "manifest": "u1"}]},
        resolve_shelfmark_fn=_resolve_shelfmark,
    )

    assert result.status == "results"
    assert len(result.results) == 1
    assert calls["resolve"] == 0


def test_orchestrator_fallback_tries_direct_then_search():
    """Fallback providers should search when direct resolution does not match."""
    def _resolve_shelfmark(_library: str, _value: str):
        return None, None

    result = resolve_provider_input(
        "Vaticana",
        "dante",
        search_handlers={"vatican": lambda _query, _payload: [{"id": "MSS_X", "manifest": "u2"}]},
        resolve_shelfmark_fn=_resolve_shelfmark,
    )

    assert result.status == "results"
    assert result.results[0]["id"] == "MSS_X"


def test_orchestrator_returns_manifest_when_direct_resolution_hits():
    """Direct-capable providers should return a manifest resolution when can_resolve matches."""
    def _resolve_shelfmark(_library: str, _value: str):
        return "https://example.org/m.json", "DOC42"

    result = resolve_provider_input(
        "Library of Congress",
        "https://www.loc.gov/item/2021668145/",
        search_handlers={},
        resolve_shelfmark_fn=_resolve_shelfmark,
    )

    assert result.status == "manifest"
    assert result.manifest_url == "https://example.org/m.json"
    assert result.doc_id == "DOC42"
