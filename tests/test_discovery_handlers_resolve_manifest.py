from studio_ui.routes import discovery_handlers
from universal_iiif_core.providers import get_provider
from universal_iiif_core.resolvers.discovery import ProviderResolution


def test_resolve_manifest_rejects_empty_input():
    """Ensure empty input returns a user-facing validation error."""
    result = discovery_handlers.resolve_manifest("Gallica", "   ")
    result_str = repr(result)
    assert "Input mancante" in result_str


def test_resolve_manifest_gallica_direct_match_renders_preview(monkeypatch):
    """Ensure a direct Gallica match renders a single preview card."""
    monkeypatch.setattr(
        discovery_handlers,
        "resolve_provider_input",
        lambda _library, _query, filters=None: ProviderResolution(
            provider=get_provider("Gallica"),
            status="results",
            results=[
                {
                    "id": "btv1b10033406t",
                    "title": "Dante Manuscript",
                    "manifest": "https://gallica.example/manifest.json",
                    "description": "Desc",
                    "thumbnail": "https://gallica.example/thumb.jpg",
                    "raw": {"_is_direct_match": True},
                }
            ],
        ),
    )

    result = discovery_handlers.resolve_manifest("Gallica", "btv1b10033406t")
    result_str = repr(result)
    assert "Dante Manuscript" in result_str
    assert "Aggiungi + Download" in result_str


def test_resolve_manifest_gallica_search_results_list(monkeypatch):
    """Ensure Gallica non-direct results render the result list component."""
    monkeypatch.setattr(
        discovery_handlers,
        "resolve_provider_input",
        lambda _library, _query, filters=None: ProviderResolution(
            provider=get_provider("Gallica"),
            status="results",
            results=[
                {"id": "A", "title": "Uno", "manifest": "u1", "raw": {}},
                {"id": "B", "title": "Due", "manifest": "u2", "raw": {}},
            ],
        ),
    )

    result = discovery_handlers.resolve_manifest("Gallica", "dante")
    result_str = repr(result)
    assert "Trovati 2 risultati" in result_str
    assert "PDF: verifica automatica" in result_str
    assert "/api/discovery/pdf_capability?manifest_url=" in result_str
    assert 'hx-trigger="load"' in result_str


def test_resolve_manifest_gallica_passes_optional_filter(monkeypatch):
    """Gallica optional filter from form must be forwarded to provider resolution."""
    captured: dict[str, str] = {}

    def _fake_resolution(library: str, query: str, filters=None):
        captured["library"] = library
        captured["query"] = query
        captured["gallica_type_filter"] = str((filters or {}).get("gallica_type") or "")
        return ProviderResolution(
            provider=get_provider("Gallica"),
            status="results",
            results=[
                {"id": "A", "title": "Uno", "manifest": "u1", "raw": {}},
                {"id": "B", "title": "Due", "manifest": "u2", "raw": {}},
            ],
        )

    monkeypatch.setattr(discovery_handlers, "resolve_provider_input", _fake_resolution)
    result = discovery_handlers.resolve_manifest("Gallica", "dante", gallica_type="manuscrit")
    result_str = repr(result)
    assert "Trovati 2 risultati" in result_str
    assert captured["library"] == "Gallica"
    assert captured["query"] == "dante"
    assert captured["gallica_type_filter"] == "manuscrit"


def test_resolve_manifest_vatican_single_search_result_renders_preview(monkeypatch):
    """Ensure Vatican single fallback result renders as preview."""
    monkeypatch.setattr(
        discovery_handlers,
        "resolve_provider_input",
        lambda _library, _query, filters=None: ProviderResolution(
            provider=get_provider("Vaticana"),
            status="results",
            results=[
                {
                    "id": "MSS_Urb.lat.77",
                    "title": "Vatican Result",
                    "manifest": "https://digi.vatlib.it/iiif/MSS_Urb.lat.77/manifest.json",
                    "description": "Test",
                    "thumbnail": "",
                    "raw": {"page_count": 12},
                }
            ],
        ),
    )

    result = discovery_handlers.resolve_manifest("Vaticana", "77")
    result_str = repr(result)
    assert "Vatican Result" in result_str
    assert "12 pagine" in result_str


def test_resolve_manifest_returns_not_found_with_vatican_hint(monkeypatch):
    """Ensure unresolved Vatican lookups include helpful format hint."""
    monkeypatch.setattr(
        discovery_handlers,
        "resolve_provider_input",
        lambda _library, _query, filters=None: ProviderResolution(
            provider=get_provider("Vaticana"),
            status="not_found",
            not_found_hint=get_provider("Vaticana").not_found_hint,
        ),
    )

    result = discovery_handlers.resolve_manifest("Vaticana", "invalid")
    result_str = str(result)
    assert "Documento non trovato" in result_str
    assert "Nessun risultato utile" in result_str
    assert "Urb.lat.1779" in result_str


def test_resolve_manifest_handles_manifest_analysis_errors(monkeypatch):
    """Ensure generic manifest failures are sanitized for users."""
    monkeypatch.setattr(
        discovery_handlers,
        "resolve_provider_input",
        lambda _library, _query, filters=None: ProviderResolution(
            provider=get_provider("Bodleian"),
            status="manifest",
            manifest_url="https://example.org/manifest.json",
            doc_id="DOCX",
        ),
    )

    def _raise_manifest(_manifest_url):
        raise RuntimeError("internal stack trace")

    monkeypatch.setattr(discovery_handlers, "analyze_manifest", _raise_manifest)

    result = discovery_handlers.resolve_manifest("Bodleian", "DOCX")
    result_str = str(result)
    assert "Errore Manifest" in result_str
    assert "stack trace" not in result_str


def test_resolve_manifest_institut_single_search_result_renders_preview(monkeypatch):
    """Ensure Institut single fallback result renders as preview."""
    monkeypatch.setattr(
        discovery_handlers,
        "resolve_provider_input",
        lambda _library, _query, filters=None: ProviderResolution(
            provider=get_provider("Institut de France"),
            status="results",
            results=[
                {
                    "id": "17837",
                    "title": "Oeuvres de Brantôme",
                    "manifest": "https://bibnum.institutdefrance.fr/iiif/17837/manifest",
                    "description": "Test",
                    "thumbnail": "",
                    "raw": {"page_count": 12},
                }
            ],
        ),
    )

    result = discovery_handlers.resolve_manifest("Institut de France", "Brantôme")
    result_str = repr(result)
    assert "Oeuvres de Brantôme" in result_str
    assert "12 pagine" in result_str


def test_resolve_manifest_institut_page_count_from_manifest_items(monkeypatch):
    """Institut fallback should derive pages from raw IIIF manifest when page_count is missing."""
    monkeypatch.setattr(
        discovery_handlers,
        "resolve_provider_input",
        lambda _library, _query, filters=None: ProviderResolution(
            provider=get_provider("Institut de France"),
            status="results",
            results=[
                {
                    "id": "17837",
                    "title": "Oeuvres de Brantôme",
                    "manifest": "https://bibnum.institutdefrance.fr/iiif/17837/manifest",
                    "description": "Test",
                    "thumbnail": "",
                    "raw": {"items": [{}, {}, {}, {}]},
                }
            ],
        ),
    )

    result = discovery_handlers.resolve_manifest("Institut de France", "Brantôme")
    result_str = repr(result)
    assert "Oeuvres de Brantôme" in result_str
    assert "4 pagine" in result_str


def test_resolve_manifest_archive_search_results_list(monkeypatch):
    """Archive.org free-text search should render a results list, not force preview."""
    monkeypatch.setattr(
        discovery_handlers,
        "resolve_provider_input",
        lambda _library, _query, filters=None: ProviderResolution(
            provider=get_provider("Archive.org"),
            status="results",
            results=[
                {
                    "id": "b29000427_0001",
                    "title": "Subject-index of the London Library",
                    "manifest": "https://iiif.archive.org/iiif/b29000427_0001/manifest.json",
                    "thumbnail": "https://iiif.archive.org/image/iiif/2/b29000427_0001%2F__ia_thumb.jpg/full/180,/0/default.jpg",
                    "viewer_url": "https://archive.org/details/b29000427_0001",
                    "raw": {"viewer_url": "https://archive.org/details/b29000427_0001"},
                }
            ],
        ),
    )

    result = discovery_handlers.resolve_manifest("Archive.org", "london library")
    result_str = repr(result)
    assert "Trovati 1 risultati" in result_str
    assert "Subject-index of the London Library" in result_str


def test_resolve_manifest_bodleian_results_include_provider_viewer_link(monkeypatch):
    """Bodleian search results should render the source viewer URL from provider data."""
    monkeypatch.setattr(
        discovery_handlers,
        "resolve_provider_input",
        lambda _library, _query, filters=None: ProviderResolution(
            provider=get_provider("Bodleian"),
            status="results",
            results=[
                {
                    "id": "cb1df5f1-7435-468b-8860-d56db988b929",
                    "title": "Divine Comedy.",
                    "manifest": "https://iiif.bodleian.ox.ac.uk/iiif/manifest/cb1df5f1-7435-468b-8860-d56db988b929.json",
                    "thumbnail": "https://iiif.bodleian.ox.ac.uk/iiif/image/test/full/255,/0/default.jpg",
                    "viewer_url": "https://digital.bodleian.ox.ac.uk/objects/cb1df5f1-7435-468b-8860-d56db988b929/",
                    "raw": {
                        "viewer_url": "https://digital.bodleian.ox.ac.uk/objects/cb1df5f1-7435-468b-8860-d56db988b929/"
                    },
                }
            ],
        ),
    )

    result = discovery_handlers.resolve_manifest("Bodleian", "dante")
    result_str = repr(result)
    assert "Apri viewer" in result_str
    assert "https://digital.bodleian.ox.ac.uk/objects/cb1df5f1-7435-468b-8860-d56db988b929/" in result_str


def test_resolve_manifest_ecodices_results_include_provider_viewer_link(monkeypatch):
    """e-codices search results should render the source viewer URL from provider data."""
    monkeypatch.setattr(
        discovery_handlers,
        "resolve_provider_input",
        lambda _library, _query, filters=None: ProviderResolution(
            provider=get_provider("e-codices"),
            status="results",
            results=[
                {
                    "id": "fmb-cb-0055",
                    "title": "Dante, Inferno e Purgatorio (Codex Guarneri)",
                    "manifest": "https://www.e-codices.unifr.ch/metadata/iiif/fmb-cb-0055/manifest.json",
                    "thumbnail": "https://www.e-codices.unifr.ch/loris/fmb/fmb-cb-0055/fmb-cb-0055_0021v.jp2/full/180,/0/default.jpg",
                    "viewer_url": "https://www.e-codices.unifr.ch/en/fmb/cb-0055",
                    "raw": {"viewer_url": "https://www.e-codices.unifr.ch/en/fmb/cb-0055"},
                }
            ],
        ),
    )

    result = discovery_handlers.resolve_manifest("e-codices", "dante")
    result_str = repr(result)
    assert "Apri viewer" in result_str
    assert "https://www.e-codices.unifr.ch/en/fmb/cb-0055" in result_str


def test_resolve_manifest_cambridge_consult_only_result_stays_in_results_list(monkeypatch):
    """Consult-only Cambridge handoff results should not be coerced into preview rendering."""
    monkeypatch.setattr(
        discovery_handlers,
        "resolve_provider_input",
        lambda _library, _query, filters=None: ProviderResolution(
            provider=get_provider("Cambridge"),
            status="results",
            results=[
                {
                    "id": "cambridge-search:dante",
                    "title": "Apri la ricerca Cambridge nel browser",
                    "description": "Apri CUDL nel browser e incolla qui signature o URL del record.",
                    "manifest": "",
                    "viewer_url": "https://cudl.lib.cam.ac.uk/search?keyword=dante",
                    "library": "Cambridge",
                    "raw": {"consult_online_only": True},
                }
            ],
        ),
    )

    result = discovery_handlers.resolve_manifest("Cambridge", "dante")
    result_str = repr(result)
    assert "Trovati 1 risultati" in result_str
    assert "Solo consultazione online" in result_str
    assert "https://cudl.lib.cam.ac.uk/search?keyword=dante" in result_str


def test_resolve_manifest_heidelberg_consult_only_result_stays_in_results_list(monkeypatch):
    """Consult-only Heidelberg handoff results should remain in the results list renderer."""
    monkeypatch.setattr(
        discovery_handlers,
        "resolve_provider_input",
        lambda _library, _query, filters=None: ProviderResolution(
            provider=get_provider("Heidelberg"),
            status="results",
            results=[
                {
                    "id": "heidelberg-search:dante",
                    "title": "Apri la ricerca Heidelberg nel browser",
                    "description": "Apri Heidelberg nel browser e incolla qui ID o URL del record digitalizzato.",
                    "manifest": "",
                    "viewer_url": (
                        "https://www.ub.uni-heidelberg.de/cgi-bin/search.cgi?query=dante&q=homepage&sprache=ger&wo=w"
                    ),
                    "library": "Heidelberg",
                    "raw": {"consult_online_only": True},
                }
            ],
        ),
    )

    result = discovery_handlers.resolve_manifest("Heidelberg", "dante")
    result_str = repr(result)
    assert "Trovati 1 risultati" in result_str
    assert "Solo consultazione online" in result_str
    assert "search.cgi?query=dante" in result_str
