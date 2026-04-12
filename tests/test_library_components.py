from studio_ui.components.library import render_library_card, render_library_page
from studio_ui.components.library_cards import _card_action_flags


def _base_doc(**overrides):
    doc = {
        "id": "DOC_CARD_PDF",
        "library": "Gallica",
        "display_title": "Test card PDF",
        "asset_state": "complete",
        "item_type": "manoscritto",
        "total_canvases": 12,
        "downloaded_canvases": 12,
        "missing_pages": [],
        "reference_text": "",
        "source_detail_url": "",
        "date_label": "",
        "language_label": "",
        "shelfmark": "Shelf.1",
        "thumbnail_url": "",
        "has_native_pdf": None,
        "pdf_local_available": False,
    }
    doc.update(overrides)
    return doc


def test_library_card_hides_pdf_badges_from_card_technical_rows():
    """Library cards should avoid PDF-source badges to reduce state ambiguity."""
    rendered = repr(
        render_library_card(
            _base_doc(
                pdf_source="native",
                has_native_pdf=True,
                pdf_local_available=True,
                pdf_local_count=3,
            )
        )
    )
    assert "Sorgente PDF:" not in rendered
    assert "PDF locali:" not in rendered


def test_library_card_includes_temp_page_technical_row():
    """Card technical rows should still expose local/temp page inventory."""
    rendered = repr(
        render_library_card(
            _base_doc(
                temp_pages_count=2,
            )
        )
    )
    assert "Pagine temporanee:" in rendered
    assert "2" in rendered


def test_library_card_shows_temporary_pages_count():
    """Cards should display temporary page count from staging area."""
    rendered = repr(render_library_card(_base_doc(temp_pages_count=4)))
    assert "Pagine temporanee:" in rendered
    assert "4" in rendered


def test_library_page_includes_filter_persistence_script():
    """Library page should include client-side filter persistence bootstrap."""
    rendered = repr(render_library_page([]))
    assert "ui.library.filters.v1" in rendered
    assert "ui.library.collapsible.v1" in rendered
    assert "__libraryFiltersPersistenceBootstrapped" in rendered
    assert "htmx.ajax('GET', url" in rendered
    assert 'const DEFAULT_MODE = "operativa";' in rendered


def test_library_page_reset_control_clears_persisted_filters():
    """Reset action must expose a stable id used by persistence script."""
    rendered = repr(render_library_page([]))
    assert 'id="library-reset-filters"' in rendered


def test_library_page_has_mode_switch_and_collapsible_filters():
    """Library page should expose mode switch in header and collapsible filter panel."""
    rendered = repr(render_library_page([]))
    assert "Vista Operativa" in rendered
    assert "Vista Archivio" in rendered
    assert 'id="library-filters-panel"' in rendered
    assert 'data-collapsible-key="filters"' in rendered
    assert 'name="mode"' in rendered
    assert 'type="hidden"' in rendered
    assert 'value="operativa"' in rendered


def test_library_page_uses_configurable_default_mode_in_script():
    """Persistence script should honor current default mode for query serialization."""
    rendered = repr(render_library_page([], default_mode="archivio", mode="archivio"))
    assert 'const DEFAULT_MODE = "archivio";' in rendered


def test_library_delete_uses_styled_modal_instead_of_native_confirm():
    """Delete action should use the app modal instead of browser confirm dialogs."""
    rendered = repr(render_library_card(_base_doc()))
    assert "openLibraryDeleteModal(" in rendered
    assert "hx_confirm" not in rendered


def test_library_page_includes_delete_modal_shell():
    """Library page should include the shared delete modal and script hooks."""
    rendered = repr(render_library_page([_base_doc()]))
    assert 'id="library-delete-overlay"' in rendered
    assert 'id="library-delete-sheet"' in rendered
    assert 'id="library-delete-confirm"' in rendered
    assert "window.openLibraryDeleteModal" in rendered
    assert "window.closeLibraryDeleteModal" in rendered


def test_library_card_truncates_long_title():
    """Card title should be truncated for very long labels."""
    long_title = "Titolo molto lungo " * 10
    rendered = repr(render_library_card(_base_doc(display_title=long_title)))
    assert "[...]" in rendered


def test_library_card_places_metadata_links_in_media_column():
    """Metadata/catalog links should live under thumbnail and technical rows."""
    rendered = repr(render_library_card(_base_doc(source_detail_url="https://example.org/catalog")))
    assert 'data-library-meta-links="1"' in rendered
    assert rendered.index("Pagine mancanti:") < rendered.index('data-library-meta-links="1"')


def test_library_card_category_select_uses_readable_text_colors():
    """Category selector should keep readable text in both themes."""
    rendered = repr(render_library_card(_base_doc(item_type="musica/spartito")))
    assert "text-slate-900 dark:text-slate-100" in rendered


def test_library_archive_view_has_persisted_collapsible_sections():
    """Archive sections should expose stable collapsible keys for persistence."""
    rendered = repr(render_library_page([_base_doc()], mode="archivio", default_mode="operativa"))
    assert 'data-collapsible-key="archive:' in rendered


def test_card_action_flags_enable_download_full_only_for_remote_state():
    """'Scarica locale' must be enabled only for saved/remote items."""
    assert _card_action_flags({"asset_state": "saved"}).get("download_full") is True
    assert _card_action_flags({"asset_state": "partial"}).get("download_full") is False
    assert _card_action_flags({"asset_state": "complete"}).get("download_full") is False
    assert _card_action_flags({"asset_state": "error"}).get("download_full") is False


def test_base_layout_bootstraps_library_filter_navigation():
    """Layout should pre-resolve Library URL from persisted filters to avoid flash."""
    from fasthtml.common import Div

    from studio_ui.components.layout import base_layout

    rendered = repr(base_layout("Test", Div("content"), active_page="library"))
    assert "ui.library.filters.v1" in rendered
    assert "window.location.replace('/library?' + query)" in rendered
    assert 'data-nav-key="library"' in rendered
    assert 'data-nav-key="studio"' in rendered
    assert "new URL(target || '', window.location.origin).pathname" in rendered
