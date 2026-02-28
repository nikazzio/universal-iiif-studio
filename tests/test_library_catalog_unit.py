from universal_iiif_core import library_catalog


def test_normalize_item_type_maps_legacy_altro():
    """Legacy type values should map to the canonical fallback category."""
    assert library_catalog.normalize_item_type("altro") == "non classificato"
    assert library_catalog.normalize_item_type("") == "non classificato"


def test_infer_item_type_prefers_incunabolo():
    """Incunable signals should win over generic print/manuscript tokens."""
    item_type, confidence, reason = library_catalog.infer_item_type(
        "Raccolta storica",
        "Incunabolo miniato su pergamena",
        {"type": "print"},
    )
    assert item_type == "incunabolo"
    assert confidence > 0.9
    assert "incunab" in reason


def test_parse_manifest_catalog_extracts_see_also_reference(monkeypatch):
    """`seeAlso` detail pages should enrich reference text and catalog title."""
    manifest = {
        "label": "Urb.lat.1231",
        "description": "",
        "metadata": [
            {"label": "Shelfmark", "value": "Urb.lat.1231"},
            {"label": "Language", "value": ["Italiano"]},
        ],
        "seeAlso": ["https://digi.vatlib.it/mss/detail/Urb.lat.1231"],
    }

    class _Resp:
        text = (
            "<html><head><title>DigiVatLib</title></head>"
            "<body><h1>Orafo da Cremona, trattato di oreficeria</h1></body></html>"
        )

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(library_catalog.requests, "get", lambda *_a, **_k: _Resp())

    parsed = library_catalog.parse_manifest_catalog(
        manifest,
        manifest_url="https://digi.vatlib.it/iiif/MSS_Urb.lat.1231/manifest.json",
        doc_id="MSS_Urb.lat.1231",
        enrich_external_reference=True,
    )
    assert parsed["source_detail_url"] == "https://digi.vatlib.it/mss/detail/Urb.lat.1231"
    assert parsed["reference_text"].startswith("Orafo da Cremona")
    assert parsed["catalog_title"].startswith("Orafo da Cremona")
    assert parsed["shelfmark"] == "Urb.lat.1231"


def test_parse_manifest_catalog_ignores_generic_site_title_for_catalog_title(monkeypatch):
    """Generic site headers should not replace the manuscript title."""
    manifest = {
        "label": "Urb.lat.1779",
        "metadata": [{"label": "Shelfmark", "value": "Urb.lat.1779"}],
        "seeAlso": ["https://digi.vatlib.it/mss/detail/Urb.lat.1779"],
    }

    class _Resp:
        text = "<html><head><title>Digital Vatican Library</title></head><body></body></html>"

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(library_catalog.requests, "get", lambda *_a, **_k: _Resp())

    parsed = library_catalog.parse_manifest_catalog(
        manifest,
        manifest_url="https://digi.vatlib.it/iiif/MSS_Urb.lat.1779/manifest.json",
        doc_id="MSS_Urb.lat.1779",
        enrich_external_reference=True,
    )
    assert parsed["catalog_title"] == "Urb.lat.1779"


def test_parse_manifest_catalog_falls_back_from_generic_label_to_metadata_title():
    """Placeholder labels like OAIHandler should use metadata title when available."""
    manifest = {
        "label": "OAIHandler",
        "metadata": [
            {"label": "Title", "value": "Bestiaire médiéval"},
            {"label": "Shelfmark", "value": "ms.fr.123"},
        ],
    }

    parsed = library_catalog.parse_manifest_catalog(
        manifest,
        manifest_url="https://gallica.bnf.fr/iiif/ark:/12148/btv1b123/manifest.json",
        doc_id="btv1b123",
        enrich_external_reference=False,
    )
    assert parsed["label"] == "Bestiaire médiéval"
    assert parsed["catalog_title"] == "Bestiaire médiéval"


def test_parse_manifest_catalog_ignores_search_and_discover_placeholder(monkeypatch):
    """Vatican UI placeholder titles should not replace shelfmark label."""
    manifest = {
        "label": "Urb.lat.1777",
        "metadata": [{"label": "Shelfmark", "value": "Urb.lat.1777"}],
        "seeAlso": ["https://digi.vatlib.it/mss/detail/Urb.lat.1777"],
    }

    class _Resp:
        text = "<html><head><title>Search and discover manuscripts</title></head><body></body></html>"

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(library_catalog.requests, "get", lambda *_a, **_k: _Resp())

    parsed = library_catalog.parse_manifest_catalog(
        manifest,
        manifest_url="https://digi.vatlib.it/iiif/MSS_Urb.lat.1777/manifest.json",
        doc_id="MSS_Urb.lat.1777",
        enrich_external_reference=True,
    )
    assert parsed["catalog_title"] == "Urb.lat.1777"


def test_parse_manifest_catalog_prefers_detail_see_also_over_search_url():
    """SeeAlso should pick detail page for the manuscript, not generic search pages."""
    manifest = {
        "label": "Urb.lat.1777",
        "metadata": [{"label": "Shelfmark", "value": "Urb.lat.1777"}],
        "seeAlso": [
            "https://digi.vatlib.it/advanced-search",
            "https://digi.vatlib.it/mss/detail/Urb.lat.1777",
        ],
    }

    parsed = library_catalog.parse_manifest_catalog(
        manifest,
        manifest_url="https://digi.vatlib.it/iiif/MSS_Urb.lat.1777/manifest.json",
        doc_id="MSS_Urb.lat.1777",
        enrich_external_reference=False,
    )
    assert parsed["source_detail_url"] == "https://digi.vatlib.it/mss/detail/Urb.lat.1777"


def test_parse_manifest_catalog_search_see_also_still_uses_vatican_detail_fallback():
    """Vatican manifests should ignore search links and use derived detail URL."""
    manifest = {
        "label": "Urb.lat.1777",
        "metadata": [{"label": "Shelfmark", "value": "Urb.lat.1777"}],
        "seeAlso": ["https://digi.vatlib.it/advanced-search"],
    }

    parsed = library_catalog.parse_manifest_catalog(
        manifest,
        manifest_url="https://digi.vatlib.it/iiif/MSS_Urb.lat.1777/manifest.json",
        doc_id="MSS_Urb.lat.1777",
        enrich_external_reference=False,
    )
    assert parsed["source_detail_url"] == "https://digi.vatlib.it/mss/detail/Urb.lat.1777"
    assert parsed["reference_text"] == "Urb lat 1777"
    assert parsed["catalog_title"] == "Urb.lat.1777"


def test_parse_manifest_catalog_derives_vatican_detail_url_from_manifest_url():
    """Vatican manifests should map to /mss/detail even without explicit seeAlso links."""
    manifest = {
        "label": "Urb.lat.1777",
        "metadata": [{"label": "Shelfmark", "value": "Urb.lat.1777"}],
    }

    parsed = library_catalog.parse_manifest_catalog(
        manifest,
        manifest_url="https://digi.vatlib.it/iiif/MSS_Urb.lat.1777/manifest.json",
        doc_id="MSS_Urb.lat.1777",
        enrich_external_reference=False,
    )
    assert parsed["source_detail_url"] == "https://digi.vatlib.it/mss/detail/Urb.lat.1777"


def test_parse_manifest_catalog_prefers_gallica_notice_over_oai_url():
    """Gallica should prefer human catalog notice URLs over OAI endpoints."""
    manifest = {
        "label": "OAIHandler",
        "metadata": [
            {"label": "Title", "value": "Bestiaire médiéval"},
            {
                "label": "Relation",
                "value": "Notice du catalogue : https://archivesetmanuscrits.bnf.fr/ark:/12148/cc10108b",
            },
        ],
        "seeAlso": [
            "http://oai.bnf.fr/oai2/OAIHandler?verb=GetRecord&metadataPrefix=oai_dc&identifier=oai:bnf.fr:gallica/ark:/12148/btv1b123",
        ],
    }

    parsed = library_catalog.parse_manifest_catalog(
        manifest,
        manifest_url="https://gallica.bnf.fr/iiif/ark:/12148/btv1b123/manifest.json",
        doc_id="btv1b123",
        enrich_external_reference=False,
    )
    assert parsed["source_detail_url"] == "https://archivesetmanuscrits.bnf.fr/ark:/12148/cc10108b"


def test_parse_manifest_catalog_enrichment_merges_external_fields(monkeypatch):
    """External parser data should be merged into metadata_map using ext_* keys."""
    manifest = {
        "label": "Urb.lat.1231",
        "metadata": [{"label": "Shelfmark", "value": "Urb.lat.1231"}],
        "seeAlso": ["https://digi.vatlib.it/mss/detail/Urb.lat.1231"],
    }

    class _Resp:
        text = (
            "<html><head>"
            '<meta name="author" content="Giovanni Boccaccio"/>'
            "<title>DigiVatLib</title>"
            "</head><body><h1>Tractatus de astronomia</h1></body></html>"
        )

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(library_catalog.requests, "get", lambda *_a, **_k: _Resp())

    parsed = library_catalog.parse_manifest_catalog(
        manifest,
        manifest_url="https://digi.vatlib.it/iiif/MSS_Urb.lat.1231/manifest.json",
        doc_id="MSS_Urb.lat.1231",
        enrich_external_reference=True,
    )
    assert parsed["reference_text"] == "Tractatus de astronomia"
    assert parsed["metadata_map"].get("ext_author") == "Giovanni Boccaccio"
    assert parsed["metadata_map"].get("ext_repository") == "Biblioteca Apostolica Vaticana"


def test_parse_manifest_catalog_extracts_vatican_bibliographic_references(monkeypatch):
    """Vatican detail pages should expose bibliographic references in ext_* metadata."""
    manifest = {
        "label": "Urb.lat.1777",
        "metadata": [{"label": "Shelfmark", "value": "Urb.lat.1777"}],
        "seeAlso": ["https://digi.vatlib.it/mss/detail/Urb.lat.1777"],
    }

    class _Resp:
        text = (
            "<html><head><title>Manuscript - Urb.lat.1777</title></head>"
            "<body>"
            "<a href='#'>1) Cencio, atto del 1370</a>"
            "<a href='#'>2) Vittorelli, Descrizione codicum 1777</a>"
            "</body></html>"
        )

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(library_catalog.requests, "get", lambda *_a, **_k: _Resp())

    parsed = library_catalog.parse_manifest_catalog(
        manifest,
        manifest_url="https://digi.vatlib.it/iiif/MSS_Urb.lat.1777/manifest.json",
        doc_id="MSS_Urb.lat.1777",
        enrich_external_reference=True,
    )
    assert parsed["metadata_map"].get("ext_bibliographic_references_count") == "2"
    assert "Cencio" in str(parsed["metadata_map"].get("ext_bibliographic_reference_1") or "")


def test_parse_manifest_catalog_extracts_vatican_bibliographic_references_from_detail_dom(monkeypatch):
    """Live-like Vatican detail DOM should still yield bibliographic references."""
    manifest = {
        "label": "Urb.lat.1777",
        "metadata": [{"label": "Shelfmark", "value": "Urb.lat.1777"}],
        "seeAlso": ["https://digi.vatlib.it/mss/detail/Urb.lat.1777"],
    }

    class _Resp:
        text = (
            "<html><head><title>DigiVatLib</title></head>"
            "<body>"
            "<div id='region-detail-body'>"
            "<div class='block-detail-record'>"
            "Bibliographic References: 1) Peruzzi, Marcella, La Vaticana nel Seicento, 2014"
            "</div>"
            "<div class='block-detail-record'>"
            "2) Vian, Paolo, Miscellanea Bibliothecae Apostolicae Vaticanae, 2017"
            "</div>"
            "</div>"
            "</body></html>"
        )

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(library_catalog.requests, "get", lambda *_a, **_k: _Resp())

    parsed = library_catalog.parse_manifest_catalog(
        manifest,
        manifest_url="https://digi.vatlib.it/iiif/MSS_Urb.lat.1777/manifest.json",
        doc_id="MSS_Urb.lat.1777",
        enrich_external_reference=True,
    )
    assert parsed["metadata_map"].get("ext_bibliographic_references_count") == "2"
    assert "Peruzzi" in str(parsed["metadata_map"].get("ext_bibliographic_reference_1") or "")
