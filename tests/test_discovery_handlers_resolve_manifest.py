from studio_ui.routes import discovery_handlers


def test_resolve_manifest_rejects_empty_input():
    """Ensure empty input returns a user-facing validation error."""
    result = discovery_handlers.resolve_manifest("Gallica", "   ")
    result_str = repr(result)
    assert "Input mancante" in result_str


def test_resolve_manifest_gallica_direct_match_renders_preview(monkeypatch):
    """Ensure a direct Gallica match renders a single preview card."""
    monkeypatch.setattr(
        discovery_handlers,
        "smart_search",
        lambda _query: [
            {
                "id": "btv1b10033406t",
                "title": "Dante Manuscript",
                "manifest": "https://gallica.example/manifest.json",
                "description": "Desc",
                "thumbnail": "https://gallica.example/thumb.jpg",
                "raw": {"_is_direct_match": True},
            }
        ],
    )

    result = discovery_handlers.resolve_manifest("Gallica", "btv1b10033406t")
    result_str = repr(result)
    assert "Dante Manuscript" in result_str
    assert "Aggiungi + Download" in result_str


def test_resolve_manifest_gallica_search_results_list(monkeypatch):
    """Ensure Gallica non-direct results render the result list component."""
    monkeypatch.setattr(
        discovery_handlers,
        "smart_search",
        lambda _query: [
            {"id": "A", "title": "Uno", "manifest": "u1", "raw": {}},
            {"id": "B", "title": "Due", "manifest": "u2", "raw": {}},
        ],
    )

    result = discovery_handlers.resolve_manifest("Gallica", "dante")
    result_str = repr(result)
    assert "Trovati 2 risultati" in result_str


def test_resolve_manifest_vatican_fallback_search(monkeypatch):
    """Ensure Vatican fallback search is used when direct resolve fails."""
    monkeypatch.setattr(discovery_handlers, "resolve_shelfmark", lambda _library, _shelfmark: (None, None))
    monkeypatch.setattr(
        "universal_iiif_core.resolvers.discovery.search_vatican",
        lambda _query, max_results=5: [
            {
                "id": "MSS_Urb.lat.77",
                "title": "Vatican Result",
                "manifest": "https://digi.vatlib.it/iiif/MSS_Urb.lat.77/manifest.json",
                "description": "Test",
                "thumbnail": "",
                "raw": {"page_count": 12},
            }
        ],
    )

    result = discovery_handlers.resolve_manifest("Vaticana", "77")
    result_str = repr(result)
    assert "Vatican Result" in result_str
    assert "12 pagine" in result_str


def test_resolve_manifest_returns_not_found_with_vatican_hint(monkeypatch):
    """Ensure unresolved Vatican lookups include helpful format hint."""
    monkeypatch.setattr(discovery_handlers, "resolve_shelfmark", lambda _library, _shelfmark: (None, None))
    monkeypatch.setattr(
        "universal_iiif_core.resolvers.discovery.search_vatican",
        lambda _query, max_results=5: [],
    )

    result = discovery_handlers.resolve_manifest("Vaticana", "invalid")
    result_str = str(result)
    assert "Manoscritto non trovato" in result_str
    assert "Urb.lat.1779" in result_str


def test_resolve_manifest_handles_manifest_analysis_errors(monkeypatch):
    """Ensure generic manifest failures are sanitized for users."""
    monkeypatch.setattr(
        discovery_handlers,
        "resolve_shelfmark",
        lambda _library, _shelfmark: ("https://example.org/manifest.json", "DOCX"),
    )

    def _raise_manifest(_manifest_url):
        raise RuntimeError("internal stack trace")

    monkeypatch.setattr(discovery_handlers, "analyze_manifest", _raise_manifest)

    result = discovery_handlers.resolve_manifest("Oxford", "DOCX")
    result_str = str(result)
    assert "Errore Manifest" in result_str
    assert "stack trace" not in result_str


def test_resolve_manifest_institut_fallback_search(monkeypatch):
    """Ensure Institut search fallback is used when direct resolve fails."""
    monkeypatch.setattr(discovery_handlers, "resolve_shelfmark", lambda _library, _shelfmark: (None, None))
    monkeypatch.setattr(
        discovery_handlers,
        "search_institut",
        lambda _query, max_results=10: [
            {
                "id": "17837",
                "title": "Oeuvres de Brantôme",
                "manifest": "https://bibnum.institutdefrance.fr/iiif/17837/manifest",
                "description": "Test",
                "thumbnail": "",
                "raw": {"page_count": 12},
            }
        ],
    )

    result = discovery_handlers.resolve_manifest("Institut de France", "Brantôme")
    result_str = repr(result)
    assert "Oeuvres de Brantôme" in result_str
    assert "12 pagine" in result_str


def test_resolve_manifest_institut_fallback_derives_page_count_from_manifest(monkeypatch):
    """Institut fallback should derive pages from raw IIIF manifest when page_count is missing."""
    monkeypatch.setattr(discovery_handlers, "resolve_shelfmark", lambda _library, _shelfmark: (None, None))
    monkeypatch.setattr(
        discovery_handlers,
        "search_institut",
        lambda _query, max_results=10: [
            {
                "id": "17837",
                "title": "Oeuvres de Brantôme",
                "manifest": "https://bibnum.institutdefrance.fr/iiif/17837/manifest",
                "description": "Test",
                "thumbnail": "",
                "raw": {"items": [{}, {}, {}, {}]},
            }
        ],
    )

    result = discovery_handlers.resolve_manifest("Institut de France", "Brantôme")
    result_str = repr(result)
    assert "Oeuvres de Brantôme" in result_str
    assert "4 pagine" in result_str
