from universal_iiif_core.providers import (
    PROVIDERS,
    get_provider,
    get_search_handlers,
    is_known_provider,
    iter_providers,
    provider_library_options,
    resolve_with_provider,
)


def test_get_provider_accepts_legacy_values_and_labels():
    """Provider normalization must preserve legacy stored library values."""
    assert get_provider("Vaticana").key == "Vaticana"
    assert get_provider("Vaticana (BAV)").key == "Vaticana"
    assert get_provider("Bodleian (Oxford)").key == "Bodleian"
    assert get_provider("Altro / URL Diretto").key == "Unknown"
    assert get_provider("", fallback="DoesNotExist").key == "Unknown"


def test_is_known_provider_distinguishes_invalid_values():
    """Route handlers should be able to reject invalid provider names at the boundary."""
    assert is_known_provider("Vaticana") is True
    assert is_known_provider("Altro / URL Diretto") is True
    assert is_known_provider("InvalidLibrary") is False


def test_provider_library_options_exposes_new_direct_providers():
    """Discovery options should be generated from provider metadata."""
    options = dict(provider_library_options())
    assert options["Universitaetsbibliothek Heidelberg"] == "Heidelberg"
    assert options["Cambridge University Digital Library"] == "Cambridge"
    assert options["e-codices"] == "e-codices"
    assert options["Internet Archive"] == "Archive.org"


def test_provider_search_capabilities_cover_supported_search_libraries():
    """Provider registry should expose search capabilities for wired provider adapters."""
    assert get_provider("Bodleian").supports_search() is True
    assert get_provider("e-codices").supports_search() is True
    assert get_provider("Cambridge").supports_search() is True
    assert get_provider("Heidelberg").supports_search() is True
    assert get_provider("Harvard").supports_search() is True
    assert get_provider("Library of Congress").supports_search() is True


def test_cambridge_provider_exposes_browser_handoff_metadata():
    """Cambridge provider should advertise the browser-driven fallback UX."""
    provider = get_provider("Cambridge")
    assert "{query}" in provider.metadata["browser_search_url"]
    assert "browser" in provider.metadata["helper_text"].lower()


def test_heidelberg_provider_exposes_browser_handoff_metadata():
    """Heidelberg provider should advertise the browser-driven fallback UX."""
    provider = get_provider("Heidelberg")
    assert "{query}" in provider.metadata["browser_search_url"]
    assert "browser" in provider.metadata["helper_text"].lower()


def test_iter_providers_respects_explicit_sort_order():
    """UI/CLI ordering should follow provider metadata rather than tuple declaration luck."""
    ordered_keys = [provider.key for provider in iter_providers()]
    assert ordered_keys[:5] == ["Vaticana", "Gallica", "Institut de France", "Bodleian", "Heidelberg"]
    assert ordered_keys[-1] == "Unknown"


def test_resolve_with_provider_uses_shared_registry_for_new_resolvers():
    """CLI/web shared registry must resolve new providers consistently."""
    manifest_url, doc_id, provider = resolve_with_provider("https://digi.ub.uni-heidelberg.de/diglit/cpg123")
    assert provider.key == "Heidelberg"
    assert doc_id == "cpg123"
    assert manifest_url == "https://digi.ub.uni-heidelberg.de/diglit/iiif/cpg123/manifest.json"

    manifest_url2, doc_id2, provider2 = resolve_with_provider("MS-ADD-03996")
    assert provider2.key == "Cambridge"
    assert doc_id2 == "MS-ADD-03996"
    assert manifest_url2 == "https://cudl.lib.cam.ac.uk/iiif/MS-ADD-03996"

    manifest_url3, doc_id3, provider3 = resolve_with_provider("https://archive.org/details/b29000427_0001")
    assert provider3.key == "Archive.org"
    assert doc_id3 == "b29000427_0001"
    assert manifest_url3 == "https://iiif.archive.org/iiif/b29000427_0001/manifest.json"

    manifest_url4, doc_id4, provider4 = resolve_with_provider("b29000427_0001")
    assert provider4.key == "Archive.org"
    assert doc_id4 == "b29000427_0001"
    assert manifest_url4 == "https://iiif.archive.org/iiif/b29000427_0001/manifest.json"


def test_resolve_with_provider_keeps_direct_manifest_when_loc_pattern_is_non_loc():
    """Non-LOC URLs with /item/ in the path must fall through to the generic resolver."""
    manifest_url, doc_id, provider = resolve_with_provider("https://example.org/item/not-loc/manifest.json")
    assert provider.key == "Unknown"
    assert doc_id == "not-loc"
    assert manifest_url == "https://example.org/item/not-loc/manifest.json"


def test_resolve_with_provider_prefers_ecodices_over_cambridge_for_compound_ids():
    """e-codices compound identifiers must not be misclassified as Cambridge."""
    manifest_url, doc_id, provider = resolve_with_provider("csg-0001")
    assert provider.key == "e-codices"
    assert doc_id == "csg-0001"
    assert manifest_url == "https://www.e-codices.unifr.ch/metadata/iiif/csg-0001/manifest.json"


def test_resolve_with_provider_does_not_misclassify_archive_free_text():
    """Archive resolver must not steal generic one-word searches in shared detection."""
    manifest_url, doc_id, provider = resolve_with_provider("dante")
    assert provider.key == "Unknown"
    assert doc_id is None
    assert manifest_url is None


def test_get_search_handlers_returns_all_searchable_strategies():
    """get_search_handlers must cover every provider that declares a search_strategy."""
    handlers = get_search_handlers()
    expected_keys = {p.search_strategy for p in PROVIDERS if p.search_strategy and p.search_fn}
    assert set(handlers.keys()) == expected_keys


def test_get_search_handlers_is_cached():
    """Repeated calls must return the same dict instance (lazy-init caching)."""
    assert get_search_handlers() is get_search_handlers()


def test_provider_search_fn_matches_search_strategy():
    """Every provider with a search_strategy must also declare search_fn."""
    for provider in PROVIDERS:
        if provider.search_strategy:
            assert provider.search_fn is not None, (
                f"Provider {provider.key} has search_strategy={provider.search_strategy!r} but no search_fn"
            )
