import json
from pathlib import Path

from PIL import Image
from starlette.requests import Request
from starlette.responses import RedirectResponse

from studio_ui.common.title_utils import truncate_title
from studio_ui.routes import studio_handlers
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.services.storage.vault_manager import VaultManager


def _request(path: str = "/studio", headers: dict[str, str] | None = None) -> Request:
    header_items = []
    for key, value in (headers or {}).items():
        header_items.append((key.lower().encode("latin-1"), value.encode("latin-1")))

    return Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "server": ("testserver", 80),
            "path": path,
            "query_string": b"",
            "headers": header_items,
        }
    )


def test_studio_redirects_to_library_without_context():
    """Studio endpoint without doc context must redirect to Library."""
    response = studio_handlers.studio_page(_request(), doc_id="", library="", page=1)
    assert isinstance(response, RedirectResponse)
    assert response.status_code == 303
    assert response.headers.get("location") == "/library"


def test_studio_redirects_to_library_when_context_is_partial():
    """Studio endpoint with partial context must redirect to Library."""
    response = studio_handlers.studio_page(_request(), doc_id="MSS_Urb.lat.1779", library="", page=1)
    assert isinstance(response, RedirectResponse)
    assert response.status_code == 303
    assert response.headers.get("location") == "/library"


def test_studio_renders_workspace_with_doc_context():
    """Studio endpoint with full context must render workspace content."""
    doc_id = "MSS_Urb.lat.1779"
    library = "Vaticana"
    cm = get_config_manager()
    doc_root = Path(cm.get_downloads_dir()) / library / doc_id
    scans_dir = doc_root / "scans"
    data_dir = doc_root / "data"
    scans_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    (scans_dir / "pag_0000.jpg").write_bytes(b"stub")
    (data_dir / "manifest.json").write_text(
        json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
        encoding="utf-8",
    )
    (data_dir / "metadata.json").write_text(
        json.dumps({"label": "Urb lat 1779"}),
        encoding="utf-8",
    )

    VaultManager().upsert_manuscript(
        doc_id,
        library=library,
        local_path=str(doc_root),
        status="saved",
        asset_state="saved",
        has_native_pdf=False,
        pdf_local_available=False,
    )

    response = studio_handlers.studio_page(_request(), doc_id=doc_id, library=library, page=1)
    assert not isinstance(response, RedirectResponse)
    rendered = str(response)
    assert "Urb lat 1779" in rendered
    assert "mirador-viewer" in rendered


def test_studio_uses_library_title_and_shows_full_title_in_info():
    """Studio header should use truncated library title while Info keeps full value."""
    doc_id = "MSS_Urb.lat.1888"
    library = "Vaticana"
    long_title = (
        "Oeuvres de Pierre de Bourdeille, sieur de Brantôme. XVIe et XVIIe siècles. "
        "XII Rodomontades espagnoles et Discours sur les Duels."
    )
    cm = get_config_manager()
    doc_root = Path(cm.get_downloads_dir()) / library / doc_id
    scans_dir = doc_root / "scans"
    data_dir = doc_root / "data"
    scans_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    (scans_dir / "pag_0000.jpg").write_bytes(b"stub")
    (data_dir / "manifest.json").write_text(
        json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
        encoding="utf-8",
    )
    (data_dir / "metadata.json").write_text(
        json.dumps({"label": "Urb lat 1888"}),
        encoding="utf-8",
    )

    VaultManager().upsert_manuscript(
        doc_id,
        library=library,
        local_path=str(doc_root),
        status="saved",
        asset_state="saved",
        title=long_title,
        display_title=long_title,
        catalog_title=long_title,
    )

    response = studio_handlers.studio_page(_request(), doc_id=doc_id, library=library, page=1)
    rendered = str(response)
    assert truncate_title(long_title, max_len=70, suffix="[...]") in rendered
    assert long_title in rendered


def test_studio_initial_render_keeps_export_lazy():
    """Initial studio render should not build the full export panel eagerly."""
    doc_id = "MSS_LAZY_EXPORT"
    library = "Vaticana"
    cm = get_config_manager()
    doc_root = Path(cm.get_downloads_dir()) / library / doc_id
    scans_dir = doc_root / "scans"
    data_dir = doc_root / "data"
    scans_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    Image.new("RGB", (600, 900), (250, 250, 250)).save(scans_dir / "pag_0000.jpg", format="JPEG")
    (data_dir / "manifest.json").write_text(
        json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
        encoding="utf-8",
    )
    (data_dir / "metadata.json").write_text(
        json.dumps({"label": "Lazy Export Title"}),
        encoding="utf-8",
    )

    VaultManager().upsert_manuscript(
        doc_id,
        library=library,
        local_path=str(doc_root),
        status="saved",
        asset_state="saved",
    )

    response = studio_handlers.studio_page(_request(), doc_id=doc_id, library=library, page=1)
    rendered = str(response)
    assert "Apri il tab Export per caricare miniature" in rendered
    assert "studio-export-form" not in rendered


def test_export_thumbs_endpoint_returns_requested_slice():
    """Thumbnails endpoint should render only the requested page slice."""
    doc_id = "MSS_THUMB_SLICE"
    library = "Vaticana"
    cm = get_config_manager()
    doc_root = Path(cm.get_downloads_dir()) / library / doc_id
    scans_dir = doc_root / "scans"
    data_dir = doc_root / "data"
    scans_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    for idx in range(5):
        Image.new("RGB", (600, 900), (250, 250, 250)).save(scans_dir / f"pag_{idx:04d}.jpg", format="JPEG")
    (data_dir / "manifest.json").write_text(
        json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
        encoding="utf-8",
    )
    (data_dir / "metadata.json").write_text(
        json.dumps({"label": "Thumb Slice Title"}),
        encoding="utf-8",
    )

    VaultManager().upsert_manuscript(
        doc_id,
        library=library,
        local_path=str(doc_root),
        status="saved",
        asset_state="saved",
    )

    panel = studio_handlers.get_studio_export_thumbs(doc_id=doc_id, library=library, thumb_page=2, page_size=2)
    rendered = repr(panel)
    assert "Miniature: pagina 2/3" in rendered
    assert "Pag. 3" in rendered
    assert "Pag. 4" in rendered


def test_export_panel_uses_submit_trigger_and_card_based_thumbnail_selection():
    """Export form should submit only on submit and use card buttons for thumbnail selection."""
    doc_id = "MSS_EXPORT_TRIGGER_GUARD"
    library = "Vaticana"
    cm = get_config_manager()
    doc_root = Path(cm.get_downloads_dir()) / library / doc_id
    scans_dir = doc_root / "scans"
    data_dir = doc_root / "data"
    scans_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    for idx in range(2):
        Image.new("RGB", (600, 900), (250, 250, 250)).save(scans_dir / f"pag_{idx:04d}.jpg", format="JPEG")
    (data_dir / "manifest.json").write_text(
        json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
        encoding="utf-8",
    )
    (data_dir / "metadata.json").write_text(
        json.dumps({"label": "Trigger Guard Title"}),
        encoding="utf-8",
    )

    VaultManager().upsert_manuscript(
        doc_id,
        library=library,
        local_path=str(doc_root),
        status="saved",
        asset_state="saved",
    )

    panel = studio_handlers.get_export_tab(doc_id=doc_id, library=library, page=1)
    rendered = repr(panel)
    assert 'hx-trigger="submit"' in rendered
    assert 'class="studio-export-page-card' in rendered
    assert "studio-export-page-checkbox" not in rendered
    assert 'data-thumbs-endpoint="/api/studio/export/thumbs' in rendered
    assert 'form="studio-export-form"' in rendered
    assert rendered.find('id="studio-export-thumbs-slot"') > rendered.find("</form>")
    assert 'id="studio-export-thumb-size-select"' in rendered
    assert 'name="page_size"' in rendered
    assert 'hx-trigger="change"' in rendered
    assert "window.__studioExportListenersBound" in rendered
    assert "initStudioExport();" in rendered


def test_export_thumb_page_size_preference_is_persisted_per_item():
    """Changing thumb page size should persist and be reused when reopening export tab."""
    doc_id = "MSS_EXPORT_SIZE_PREF"
    library = "Vaticana"
    cm = get_config_manager()
    doc_root = Path(cm.get_downloads_dir()) / library / doc_id
    scans_dir = doc_root / "scans"
    data_dir = doc_root / "data"
    scans_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    for idx in range(4):
        Image.new("RGB", (600, 900), (250, 250, 250)).save(scans_dir / f"pag_{idx:04d}.jpg", format="JPEG")
    (data_dir / "manifest.json").write_text(
        json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
        encoding="utf-8",
    )
    (data_dir / "metadata.json").write_text(
        json.dumps({"label": "Thumb Size Pref Title"}),
        encoding="utf-8",
    )

    VaultManager().upsert_manuscript(
        doc_id,
        library=library,
        local_path=str(doc_root),
        status="saved",
        asset_state="saved",
    )

    _ = studio_handlers.get_studio_export_thumbs(doc_id=doc_id, library=library, thumb_page=1, page_size=24)
    panel = studio_handlers.get_export_tab(doc_id=doc_id, library=library, page=1, page_size=0)
    rendered = repr(panel)
    assert 'name="page_size" value="24" id="studio-export-page-size"' in rendered
    assert 'id="studio-export-thumb-size-select"' in rendered
