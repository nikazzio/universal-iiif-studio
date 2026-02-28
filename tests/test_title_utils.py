from studio_ui.common.title_utils import resolve_preferred_title, truncate_title


def test_resolve_preferred_title_prefers_catalog_title():
    """Catalog/display titles must win over shelfmark-like values."""
    row = {
        "id": "MSS_Urb.lat.1779",
        "shelfmark": "Urb.lat.1779",
        "catalog_title": "Bestiario miniato di Urbino",
        "display_title": "Bestiario miniato di Urbino",
    }
    assert resolve_preferred_title(row, fallback_doc_id="MSS_Urb.lat.1779") == "Bestiario miniato di Urbino"


def test_resolve_preferred_title_falls_back_to_doc_id():
    """Doc id fallback is used when no descriptive title exists."""
    row = {"id": "DOC_1234", "shelfmark": ""}
    assert resolve_preferred_title(row, fallback_doc_id="DOC_1234") == "DOC_1234"


def test_truncate_title_keeps_short_values():
    """Short values should be returned unchanged."""
    assert truncate_title("Titolo breve", max_len=70, suffix="[...]") == "Titolo breve"


def test_truncate_title_appends_suffix():
    """Long values should be truncated with the configured suffix."""
    value = "A" * 120
    out = truncate_title(value, max_len=70, suffix="[...]")
    assert out.endswith("[...]")
    assert len(out) <= 70
