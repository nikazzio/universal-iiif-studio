from universal_iiif_core.discovery.search_adapters import build_search_strategy_handlers


def test_search_adapters_forward_gallica_filter_payload():
    """Gallica adapter must forward `gallica_type` from filters to smart_search."""
    captured: dict[str, str] = {}

    def _smart_search(query: str, *, max_records: int = 20, page: int = 1, gallica_type_filter: str = "all"):
        captured["query"] = query
        captured["gallica_type_filter"] = gallica_type_filter
        return [{"id": "G1", "manifest": "u1"}]

    handlers = build_search_strategy_handlers(
        smart_search_fn=_smart_search,
        search_vatican_fn=lambda _q, _n, _p=1: [],
        search_institut_fn=lambda _q, _n, _p=1: [],
        search_archive_org_fn=lambda _q, _n, _p=1: [],
        search_bodleian_fn=lambda _q, _n, _p=1: [],
        search_ecodices_fn=lambda _q, _n, _p=1: [],
        search_cambridge_fn=lambda _q, _n, _p=1: [],
        search_harvard_fn=lambda _q, _n, _p=1: [],
        search_loc_fn=lambda _q, _n, _p=1: [],
        search_heidelberg_fn=lambda _q, _n, _p=1: [],
    )

    results = handlers["gallica"]("dante", {"gallica_type": "manuscrit"})
    assert len(results) == 1
    assert captured["query"] == "dante"
    assert captured["gallica_type_filter"] == "manuscrit"


def test_search_adapters_use_expected_provider_result_limits():
    """Adapters should preserve current provider-specific max_results defaults."""
    captured: dict[str, int] = {}

    def _track(name: str):
        def _inner(_query: str, max_results: int, page: int = 1):
            captured[name] = max_results
            return []

        return _inner

    handlers = build_search_strategy_handlers(
        smart_search_fn=lambda _q, **_k: [],
        search_vatican_fn=_track("vatican"),
        search_institut_fn=_track("institut"),
        search_archive_org_fn=_track("archive"),
        search_bodleian_fn=_track("bodleian"),
        search_ecodices_fn=_track("ecodices"),
        search_cambridge_fn=_track("cambridge"),
        search_harvard_fn=_track("harvard"),
        search_loc_fn=_track("loc"),
        search_heidelberg_fn=_track("heidelberg"),
    )

    handlers["vatican"]("q", {})
    handlers["institut"]("q", {})
    handlers["archive_org"]("q", {})
    handlers["bodleian"]("q", {})
    handlers["ecodices"]("q", {})
    handlers["cambridge"]("q", {})
    handlers["harvard"]("q", {})
    handlers["loc"]("q", {})
    handlers["heidelberg"]("q", {})

    assert captured["vatican"] == 20
    assert captured["institut"] == 20
    assert captured["archive"] == 20
    assert captured["bodleian"] == 20
    assert captured["ecodices"] == 20
    assert captured["cambridge"] == 20
    assert captured["harvard"] == 20
    assert captured["loc"] == 20
    assert captured["heidelberg"] == 20
