from universal_iiif_core.resolvers.parsers import IIIFManifestParser


def test_extract_thumbnail_from_top_level_thumbnail():
    """Ensure top-level thumbnail is returned before other fallbacks."""
    manifest = {"thumbnail": {"id": "https://example.org/thumb.jpg"}}
    thumb = IIIFManifestParser._extract_thumbnail(manifest, "https://example.org/manifest.json", doc_id="DOC1")
    assert thumb == "https://example.org/thumb.jpg"


def test_extract_thumbnail_from_v3_annotation_body():
    """Ensure v3 annotation body image is used when direct thumbnail is missing."""
    manifest = {
        "items": [
            {
                "items": [
                    {
                        "items": [{"body": {"id": "https://example.org/v3-body.jpg"}}],
                    }
                ]
            }
        ]
    }
    thumb = IIIFManifestParser._extract_thumbnail(manifest, "https://example.org/manifest.json", doc_id="DOC2")
    assert thumb == "https://example.org/v3-body.jpg"


def test_extract_thumbnail_from_v2_sequences():
    """Ensure v2 canvas image resource is used as thumbnail fallback."""
    manifest = {
        "sequences": [
            {
                "canvases": [
                    {
                        "images": [{"resource": {"@id": "https://example.org/v2-resource.jpg"}}],
                    }
                ]
            }
        ]
    }
    thumb = IIIFManifestParser._extract_thumbnail(manifest, "https://example.org/manifest.json", doc_id="DOC3")
    assert thumb == "https://example.org/v2-resource.jpg"


def test_extract_thumbnail_from_heuristics():
    """Ensure known library URLs use heuristic thumbnail generation."""
    bodleian_thumb = IIIFManifestParser._extract_thumbnail(
        {},
        "https://iiif.bodleian.ox.ac.uk/iiif/manifest/123.json",
        doc_id="ABC123",
    )
    assert bodleian_thumb == "https://iiif.bodleian.ox.ac.uk/iiif/thumbnail/ABC123.jpg"

    vatlib_thumb = IIIFManifestParser._extract_thumbnail(
        {},
        "https://digi.vatlib.it/iiif/MSS_Vat.lat.1/manifest.json",
        doc_id="MSS_Vat.lat.1",
    )
    assert vatlib_thumb == "https://digi.vatlib.it/iiif/MSS_Vat.lat.1/full/!200,200/0/default.jpg"


def test_parse_manifest_maps_core_and_optional_fields():
    """Ensure parse_manifest maps label, metadata, and optional fields correctly."""
    manifest = {
        "label": {"en": ["Titolo Test"]},
        "metadata": [
            {"label": "creator", "value": "Autore Test"},
            {"label": "date", "value": "1450"},
            {"label": "publisher", "value": "Biblioteca Test"},
            {"label": "language", "value": "la"},
            {"label": "description", "value": "Descrizione breve"},
        ],
        "thumbnail": "https://example.org/thumb-main.jpg",
    }
    result = IIIFManifestParser.parse_manifest(
        manifest,
        "https://example.org/manifest.json",
        library="Gallica",
        doc_id="DOC4",
    )
    assert result is not None
    assert result["id"] == "DOC4"
    assert result["title"] == "Titolo Test"
    assert result["author"] == "Autore Test"
    assert result["date"] == "1450"
    assert result["publisher"] == "Biblioteca Test"
    assert result["language"] == "la"
    assert result["description"] == "Descrizione breve"
    assert result["thumbnail"] == "https://example.org/thumb-main.jpg"
    assert result["library"] == "Gallica"


def test_parse_manifest_uses_doc_id_as_title_fallback():
    """Ensure missing labels fall back to provided document id."""
    result = IIIFManifestParser.parse_manifest({}, "https://example.org/manifest.json", doc_id="DOC_FALLBACK")
    assert result is not None
    assert result["title"] == "DOC_FALLBACK"
