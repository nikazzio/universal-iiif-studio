from universal_iiif_core.resolvers.discovery import resolve_shelfmark


def test_discovery_gallica_integration():
    """Test Gallica resolution via the main dispatcher."""
    # Test Short ID
    manifest, doc_id = resolve_shelfmark("Gallica", "bpt6k9761787t")
    # Il nuovo resolver Gallica ricostruisce sempre l'URL completo con ARK
    assert manifest == "https://gallica.bnf.fr/iiif/ark:/12148/bpt6k9761787t/manifest.json"
    assert doc_id == "bpt6k9761787t"

    # Test Full URL
    url = "https://gallica.bnf.fr/ark:/12148/btv1b84260335"
    m2, d2 = resolve_shelfmark("Gallica", url)
    assert m2 == "https://gallica.bnf.fr/iiif/ark:/12148/btv1b84260335/manifest.json"
    assert d2 == "btv1b84260335"


def test_discovery_oxford_integration():
    """Test Oxford resolution via the main dispatcher."""
    uuid = "080f88f5-7586-4b8a-8064-63ab3495393c"

    # Direct UUID
    m1, d1 = resolve_shelfmark("Oxford", uuid)
    assert d1 == uuid
    assert isinstance(m1, str) and "iiif.bodleian.ox.ac.uk" in m1

    # Case insensitive check (New Feature)
    m2, d2 = resolve_shelfmark("Oxford", uuid.upper())
    assert d2 == uuid  # Should be lowercased by logic if implemented, or just match
    assert m2 == m1


def test_discovery_institut_integration():
    """Test Institut de France resolution via the main dispatcher."""
    manifest, doc_id = resolve_shelfmark("Institut de France", "17837")
    assert manifest == "https://bibnum.institutdefrance.fr/iiif/17837/manifest"
    assert doc_id == "17837"

    viewer = "https://bibnum.institutdefrance.fr/viewer/17837?viewer=picture"
    m2, d2 = resolve_shelfmark("Institut de France", viewer)
    assert m2 == "https://bibnum.institutdefrance.fr/iiif/17837/manifest"
    assert d2 == "17837"
