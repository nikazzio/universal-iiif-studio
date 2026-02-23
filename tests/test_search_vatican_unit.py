from universal_iiif_core.resolvers import discovery


def _result_for(ms_id: str):
    return {
        "id": ms_id,
        "title": ms_id,
        "author": "",
        "manifest": f"https://digi.vatlib.it/iiif/{ms_id}/manifest.json",
        "thumbnail": "",
        "thumb": "",
        "library": "Vaticana",
        "raw": {},
    }


def test_search_vatican_returns_empty_for_blank_input():
    """Ensure blank input short-circuits without network checks."""
    assert discovery.search_vatican("") == []


def test_search_vatican_uses_normalized_direct_candidate(monkeypatch):
    """Ensure normalized shelfmark is checked first and returned when available."""
    calls: list[str] = []

    monkeypatch.setattr("universal_iiif_core.resolvers.vatican.normalize_shelfmark", lambda _q: "MSS_Urb.lat.123")
    monkeypatch.setattr("universal_iiif_core.resolvers.vatican.VaticanResolver", lambda: object())

    def fake_verify(_url, ms_id, _resolver):
        calls.append(ms_id)
        return _result_for(ms_id) if ms_id == "MSS_Urb.lat.123" else None

    monkeypatch.setattr(discovery, "_verify_vatican_manifest", fake_verify)

    results = discovery.search_vatican("Urb lat 123", max_results=5)

    assert [entry["id"] for entry in results] == ["MSS_Urb.lat.123"]
    assert calls == ["MSS_Urb.lat.123"]


def test_search_vatican_numeric_candidates_respect_max_results(monkeypatch):
    """Ensure numeric variants stop once max_results is reached."""
    calls: list[str] = []

    def raise_normalize(_q):
        raise ValueError("bad format")

    monkeypatch.setattr("universal_iiif_core.resolvers.vatican.normalize_shelfmark", raise_normalize)
    monkeypatch.setattr("universal_iiif_core.resolvers.vatican.VaticanResolver", lambda: object())

    def fake_verify(_url, ms_id, _resolver):
        calls.append(ms_id)
        return _result_for(ms_id)

    monkeypatch.setattr(discovery, "_verify_vatican_manifest", fake_verify)

    results = discovery.search_vatican("1223", max_results=2)

    assert len(results) == 2
    assert calls == ["MSS_Urb.lat.1223", "MSS_Vat.lat.1223"]


def test_search_vatican_text_variants_when_prefix_missing(monkeypatch):
    """Ensure textual input with number generates prefix-based candidates."""
    calls: list[str] = []

    def raise_normalize(_q):
        raise ValueError("cannot normalize")

    monkeypatch.setattr("universal_iiif_core.resolvers.vatican.normalize_shelfmark", raise_normalize)
    monkeypatch.setattr("universal_iiif_core.resolvers.vatican.VaticanResolver", lambda: object())

    def fake_verify(_url, ms_id, _resolver):
        calls.append(ms_id)
        return _result_for(ms_id) if ms_id == "MSS_Urb.lat.77" else None

    monkeypatch.setattr(discovery, "_verify_vatican_manifest", fake_verify)

    results = discovery.search_vatican("manoscritto 77", max_results=5)

    assert [entry["id"] for entry in results] == ["MSS_Urb.lat.77"]
    assert calls[0] == "MSS_Urb.lat.77"


def test_search_vatican_skips_text_variants_when_prefix_already_present(monkeypatch):
    """Ensure prefixed inputs do not produce duplicate text-variant candidates."""
    calls: list[str] = []

    def raise_normalize(_q):
        raise ValueError("cannot normalize")

    monkeypatch.setattr("universal_iiif_core.resolvers.vatican.normalize_shelfmark", raise_normalize)
    monkeypatch.setattr("universal_iiif_core.resolvers.vatican.VaticanResolver", lambda: object())

    def fake_verify(_url, ms_id, _resolver):
        calls.append(ms_id)
        return None

    monkeypatch.setattr(discovery, "_verify_vatican_manifest", fake_verify)

    results = discovery.search_vatican("Vat.lat.77", max_results=5)

    assert results == []
    assert calls == []
