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

    monkeypatch.setattr(discovery, "_search_vatican_official_site", lambda *_args, **_kwargs: [])
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

    monkeypatch.setattr(discovery, "_search_vatican_official_site", lambda *_args, **_kwargs: [])

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

    monkeypatch.setattr(discovery, "_search_vatican_official_site", lambda *_args, **_kwargs: [])

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


def test_search_vatican_uses_official_text_search_for_free_text(monkeypatch):
    """Free-text Vatican queries should fall back to the official DigiVatLib search flow."""
    def raise_normalize(_q):
        raise ValueError("cannot normalize")

    monkeypatch.setattr("universal_iiif_core.resolvers.vatican.normalize_shelfmark", raise_normalize)
    monkeypatch.setattr("universal_iiif_core.resolvers.vatican.VaticanResolver", lambda: object())
    monkeypatch.setattr(discovery, "_verify_vatican_manifest", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        discovery,
        "_search_vatican_official_site",
        lambda query, max_results=5: [
            {
                "id": "MSS_Arch.Cap.S.Pietro.H.14",
                "title": "Arch.Cap.S.Pietro.H.14",
                "author": "",
                "description": "Dante Alighieri, La Divina Commedia.",
                "manifest": "https://digi.vatlib.it/iiif/MSS_Arch.Cap.S.Pietro.H.14/manifest.json",
                "thumbnail": "https://digi.vatlib.it/pub/digit/MSS_Arch.Cap.S.Pietro.H.14/cover/cover.jpg",
                "thumb": "https://digi.vatlib.it/pub/digit/MSS_Arch.Cap.S.Pietro.H.14/cover/cover.jpg",
                "viewer_url": "https://digi.vatlib.it/view/MSS_Arch.Cap.S.Pietro.H.14",
                "library": "Vaticana",
                "raw": {"viewer_url": "https://digi.vatlib.it/view/MSS_Arch.Cap.S.Pietro.H.14"},
            }
        ]
        if query == "dante" and max_results == 5
        else [],
    )

    results = discovery.search_vatican("dante", max_results=5)

    assert len(results) == 1
    assert results[0]["id"] == "MSS_Arch.Cap.S.Pietro.H.14"


def test_build_vatican_html_result_parses_search_record():
    """Official Vaticana HTML search results should map into canonical SearchResult data."""
    chunk = """
    <div class="block-search-result-record-header">
      <span class="block-search-result-record-title">
        <a href="/mss/detail/Arch.Cap.S.Pietro.H.14" class="link-search-result-record-view">Arch.Cap.S.Pietro.H.14</a>
      </span>
    </div>
    <div class="block-search-result-record-body collection-mss">
      <a href="/mss/edition/MSS_Arch.Cap.S.Pietro.H.14" class="box-search-result-view-link">
        <span class="box-search-result-thumbnail">
          <img src="/pub/digit/MSS_Arch.Cap.S.Pietro.H.14/cover/cover.jpg" />
        </span>
      </a>
      <div class="box-search-result-details">
        <ul>
          <li>
            <a href="/mss/detail/230424">
              <div class="row-mss-title">
                <div class="order">1)</div>
                <div class="title"><strong>Dante Alighieri, La Divina Commedia. Sec. XV in.</strong></div>
              </div>
            </a>
          </li>
        </ul>
      </div>
    </div>
    """

    result = discovery._build_vatican_html_result(chunk)
    assert result is not None
    assert result["id"] == "MSS_Arch.Cap.S.Pietro.H.14"
    assert result["title"] == "Arch.Cap.S.Pietro.H.14"
    assert "Dante Alighieri" in result["description"]
    assert result["manifest"] == "https://digi.vatlib.it/iiif/MSS_Arch.Cap.S.Pietro.H.14/manifest.json"
    assert result["thumbnail"] == "https://digi.vatlib.it/pub/digit/MSS_Arch.Cap.S.Pietro.H.14/cover/cover.jpg"
    assert result["viewer_url"] == "https://digi.vatlib.it/view/MSS_Arch.Cap.S.Pietro.H.14"
    assert result["raw"]["viewer_url"] == "https://digi.vatlib.it/view/MSS_Arch.Cap.S.Pietro.H.14"


def test_resolve_provider_input_vatican_free_text_skips_direct_resolver(monkeypatch):
    """Free-text Vatican queries should go straight to search without resolver crashes."""
    monkeypatch.setattr(discovery, "_search_with_provider", lambda *_args, **_kwargs: [])

    def _fail_if_called(*_args, **_kwargs):
        raise AssertionError("resolve_shelfmark should not run for Vaticana free-text")

    monkeypatch.setattr(discovery, "resolve_shelfmark", _fail_if_called)

    result = discovery.resolve_provider_input("Vaticana", "dante")
    assert result.status == "not_found"
