import json
import re
from pathlib import Path

import pytest
from PIL import Image
from starlette.requests import Request

from studio_ui.common.title_utils import truncate_title
from studio_ui.routes import studio_handlers
from studio_ui.routes._studio import scan_resolution as _scan_resolution_mod
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.http_client import HTTPClient
from universal_iiif_core.services.storage.vault_manager import VaultManager

# Mark as slow (extensive file I/O, image creation, vault operations)
pytestmark = pytest.mark.slow


def _request(
    path: str = "/studio",
    headers: dict[str, str] | None = None,
    query_string: str = "",
) -> Request:
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
            "query_string": query_string.encode("latin-1"),
            "headers": header_items,
        }
    )


def test_studio_without_context_renders_recent_hub():
    """Studio endpoint without context should render the recent-work hub."""
    response = studio_handlers.studio_page(_request(), doc_id="", library="", page=1)
    rendered = str(response)
    assert "Riprendi lavoro" in rendered
    assert "Riprendi ultimo" in rendered


def test_studio_partial_context_renders_recent_hub():
    """Studio endpoint with partial context should render recent-work hub."""
    response = studio_handlers.studio_page(_request(), doc_id="MSS_Urb.lat.1779", library="", page=1)
    rendered = str(response)
    assert "Riprendi lavoro" in rendered


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
    rendered = str(response)
    assert "Urb lat 1779" in rendered
    assert "mirador-viewer" in rendered


def test_save_studio_context_api_rejects_invalid_tab():
    """Context save API must reject unknown tab values."""
    response = studio_handlers.save_studio_context_api(
        doc_id="DOC_INVALID_TAB",
        library="Gallica",
        page=1,
        tab="not-a-tab",
    )
    assert int(response.status_code) == 400


def test_save_studio_context_api_persists_last_context():
    """Context save API should persist page and tab in app-ui preferences."""
    vm = VaultManager()
    vm.upsert_manuscript("DOC_CONTEXT", library="Gallica", status="saved", asset_state="saved")

    response = studio_handlers.save_studio_context_api(
        doc_id="DOC_CONTEXT",
        library="Gallica",
        page=4,
        tab="history",
    )
    assert int(response.status_code) == 204
    stored = vm.get_studio_last_context() or {}
    assert stored.get("doc_id") == "DOC_CONTEXT"
    assert stored.get("library") == "Gallica"
    assert int(stored.get("page") or 0) == 4
    assert stored.get("tab") == "history"


def test_studio_respects_active_tab_query_parameter():
    """Studio should render requested active tab and keep it in tab script state."""
    doc_id = "MSS_TAB_HISTORY"
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
        json.dumps({"label": "Tab History"}),
        encoding="utf-8",
    )
    VaultManager().upsert_manuscript(
        doc_id,
        library=library,
        local_path=str(doc_root),
        status="saved",
        asset_state="saved",
    )

    response = studio_handlers.studio_page(_request(), doc_id=doc_id, library=library, page=1, tab="history")
    rendered = str(response)
    assert 'id="tab-button-history" class="tab-button studio-tab studio-tab-active"' in rendered
    assert 'id="tab-content-history" class="tab-content h-full"' in rendered
    assert '"history"' in rendered


def test_studio_blocks_mirador_when_local_images_are_incomplete():
    """Studio should gate Mirador until local pages match manifest pages."""
    doc_id = "MSS_PARTIAL_LOCAL"
    library = "Vaticana"
    cm = get_config_manager()
    old_gate = cm.get_setting("viewer.mirador.require_complete_local_images", True)
    doc_root = Path(cm.get_downloads_dir()) / library / doc_id
    scans_dir = doc_root / "scans"
    data_dir = doc_root / "data"
    scans_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    (scans_dir / "pag_0000.jpg").write_bytes(b"stub")
    (data_dir / "manifest.json").write_text(
        json.dumps(
            {
                "items": [
                    {"id": "https://example.org/canvas/1"},
                    {"id": "https://example.org/canvas/2"},
                ]
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "metadata.json").write_text(
        json.dumps({"label": "Partial Local"}),
        encoding="utf-8",
    )

    VaultManager().upsert_manuscript(
        doc_id,
        library=library,
        local_path=str(doc_root),
        status="partial",
        asset_state="partial",
        total_canvases=2,
        downloaded_canvases=1,
    )

    try:
        cm.set_setting("viewer.mirador.require_complete_local_images", True)
        response = studio_handlers.studio_page(_request(), doc_id=doc_id, library=library, page=1)
        rendered = str(response)
        assert 'data-mirador-gated="1"' in rendered
        assert "Viewer bloccato finche non sono disponibili tutte le immagini locali." in rendered
        assert "Pagine temporanee" in rendered
        assert 'const containerId = "mirador-viewer";' not in rendered
    finally:
        cm.set_setting("viewer.mirador.require_complete_local_images", old_gate)


def test_studio_allows_mirador_override_with_query_flag():
    """Manual override should bypass local-readiness Mirador gating."""
    doc_id = "MSS_PARTIAL_LOCAL_OVERRIDE"
    library = "Vaticana"
    cm = get_config_manager()
    old_gate = cm.get_setting("viewer.mirador.require_complete_local_images", True)
    doc_root = Path(cm.get_downloads_dir()) / library / doc_id
    scans_dir = doc_root / "scans"
    data_dir = doc_root / "data"
    scans_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    (scans_dir / "pag_0000.jpg").write_bytes(b"stub")
    (data_dir / "manifest.json").write_text(
        json.dumps(
            {
                "items": [
                    {"id": "https://example.org/canvas/1"},
                    {"id": "https://example.org/canvas/2"},
                ]
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "metadata.json").write_text(
        json.dumps({"label": "Partial Override"}),
        encoding="utf-8",
    )

    VaultManager().upsert_manuscript(
        doc_id,
        library=library,
        local_path=str(doc_root),
        status="partial",
        asset_state="partial",
        total_canvases=2,
        downloaded_canvases=1,
    )

    try:
        cm.set_setting("viewer.mirador.require_complete_local_images", True)
        response = studio_handlers.studio_page(
            _request(query_string="allow_remote_preview=1"),
            doc_id=doc_id,
            library=library,
            page=1,
        )
        rendered = str(response)
        assert 'data-mirador-gated="1"' not in rendered
        assert 'const containerId = "mirador-viewer";' in rendered
    finally:
        cm.set_setting("viewer.mirador.require_complete_local_images", old_gate)


def test_studio_saved_remote_first_bypasses_local_gate(monkeypatch):
    """Saved items should open in remote mode when saved-mode policy is remote_first."""
    doc_id = "MSS_SAVED_REMOTE_FIRST"
    library = "Vaticana"
    cm = get_config_manager()
    old_gate = cm.get_setting("viewer.mirador.require_complete_local_images", True)
    old_policy = cm.get_setting("viewer.source_policy.saved_mode", "remote_first")
    doc_root = Path(cm.get_downloads_dir()) / library / doc_id
    scans_dir = doc_root / "scans"
    data_dir = doc_root / "data"
    scans_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "manifest.json").write_text(
        json.dumps(
            {
                "items": [
                    {"id": "https://example.org/canvas/1"},
                    {"id": "https://example.org/canvas/2"},
                ]
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "metadata.json").write_text(json.dumps({"label": "Saved Remote First"}), encoding="utf-8")

    VaultManager().upsert_manuscript(
        doc_id,
        library=library,
        local_path=str(doc_root),
        manifest_url="https://example.org/remote-manifest.json",
        status="saved",
        asset_state="saved",
        total_canvases=2,
        downloaded_canvases=0,
        manifest_local_available=1,
    )

    try:
        cm.set_setting("viewer.mirador.require_complete_local_images", True)
        cm.set_setting("viewer.source_policy.saved_mode", "remote_first")
        remote_manifest = {
            "items": [
                {"id": "https://example.org/canvas/1"},
                {"id": "https://example.org/canvas/2"},
            ]
        }
        original_get_json = HTTPClient.get_json
        monkeypatch.setattr(
            HTTPClient,
            "get_json",
            lambda _self, url, **_kw: remote_manifest
            if "remote-manifest.json" in url
            else original_get_json(_self, url, **_kw),
        )
        response = studio_handlers.studio_page(_request(), doc_id=doc_id, library=library, page=1)
        rendered = str(response)
        assert 'data-mirador-gated="1"' not in rendered
        assert 'const containerId = "mirador-viewer";' in rendered
        assert "remote" in rendered
    finally:
        cm.set_setting("viewer.mirador.require_complete_local_images", old_gate)
        cm.set_setting("viewer.source_policy.saved_mode", old_policy)


def test_studio_saved_remote_first_renders_degraded_remote_when_manifest_unavailable(monkeypatch):
    """Saved remote items should still open Studio when remote manifest fetch fails."""
    doc_id = "MSS_REMOTE_DEGRADED"
    library = "Vaticana"
    cm = get_config_manager()
    old_gate = cm.get_setting("viewer.mirador.require_complete_local_images", True)
    old_policy = cm.get_setting("viewer.source_policy.saved_mode", "remote_first")
    doc_root = Path(cm.get_downloads_dir()) / library / doc_id
    scans_dir = doc_root / "scans"
    data_dir = doc_root / "data"
    scans_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "metadata.json").write_text(json.dumps({"label": "Remote degraded"}), encoding="utf-8")

    VaultManager().upsert_manuscript(
        doc_id,
        library=library,
        local_path=str(doc_root),
        manifest_url="https://example.org/unavailable-remote-manifest.json",
        status="saved",
        asset_state="saved",
        total_canvases=120,
        downloaded_canvases=0,
        manifest_local_available=0,
    )

    try:
        cm.set_setting("viewer.mirador.require_complete_local_images", True)
        cm.set_setting("viewer.source_policy.saved_mode", "remote_first")
        monkeypatch.setattr(HTTPClient, "get_json", lambda _self, _url, **_kw: None)
        response = studio_handlers.studio_page(_request(), doc_id=doc_id, library=library, page=7)
        rendered = str(response)
        assert "mirador-viewer" in rendered
        assert "versione online del documento" in rendered
        assert "Manifesto non trovato." not in rendered
        assert '"manifestId": "https://example.org/unavailable-remote-manifest.json"' in rendered
        assert "const initialPage = 7;" in rendered
    finally:
        cm.set_setting("viewer.mirador.require_complete_local_images", old_gate)
        cm.set_setting("viewer.source_policy.saved_mode", old_policy)


def test_studio_remote_first_uses_local_manifest_context_when_remote_fetch_fails(monkeypatch):
    """Remote-first should keep Studio usable by falling back to cached local manifest context."""
    doc_id = "MSS_REMOTE_LOCAL_FALLBACK"
    library = "Vaticana"
    cm = get_config_manager()
    old_policy = cm.get_setting("viewer.source_policy.saved_mode", "remote_first")
    doc_root = Path(cm.get_downloads_dir()) / library / doc_id
    scans_dir = doc_root / "scans"
    data_dir = doc_root / "data"
    scans_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "manifest.json").write_text(
        json.dumps({"items": [{"id": "https://example.org/canvas/1"}, {"id": "https://example.org/canvas/2"}]}),
        encoding="utf-8",
    )
    (data_dir / "metadata.json").write_text(json.dumps({"label": "Remote local fallback"}), encoding="utf-8")

    VaultManager().upsert_manuscript(
        doc_id,
        library=library,
        local_path=str(doc_root),
        manifest_url="https://example.org/remote-manifest-missing.json",
        status="saved",
        asset_state="saved",
        total_canvases=2,
        downloaded_canvases=0,
        manifest_local_available=1,
    )

    try:
        cm.set_setting("viewer.source_policy.saved_mode", "remote_first")
        monkeypatch.setattr(HTTPClient, "get_json", lambda _self, _url, **_kw: None)
        response = studio_handlers.studio_page(_request(), doc_id=doc_id, library=library, page=2)
        rendered = str(response)
        assert "mirador-viewer" in rendered
        assert "Pagine attese (manifest)" in rendered
        assert "2" in rendered
        assert '"manifestId": "http://testserver/iiif/manifest/Vaticana/MSS_REMOTE_LOCAL_FALLBACK"' in rendered
        assert '"canvasId": "https://example.org/canvas/2"' in rendered
        assert "remote-manifest-missing.json" not in rendered
    finally:
        cm.set_setting("viewer.source_policy.saved_mode", old_policy)


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
    assert "Apri il tab Immagini per gestire miniature e ottimizzazione." in rendered
    assert 'id="tab-button-images"' in rendered
    assert 'id="tab-button-output"' in rendered
    assert 'id="tab-button-jobs"' in rendered
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

    panel_images = studio_handlers.get_export_tab(doc_id=doc_id, library=library, page=1, tab="images")
    rendered_images = repr(panel_images)
    assert "studio-export-page-checkbox" not in rendered_images
    assert 'data-thumbs-endpoint="/api/studio/export/thumbs' in rendered_images
    assert 'id="studio-export-thumbs-slot"' in rendered_images
    assert 'hx-trigger="load"' in rendered_images
    assert "Sto preparando le miniature della pagina visibile" in rendered_images
    assert 'id="studio-export-subtab-pages"' in rendered_images
    assert 'id="studio-export-open-build"' in rendered_images
    assert 'id="studio-export-optimize-btn"' in rendered_images
    assert "/api/studio/export/thumbs?doc_id=" in rendered_images

    panel_output = studio_handlers.get_export_tab(doc_id=doc_id, library=library, page=1, tab="output")
    rendered_output = repr(panel_output)
    assert 'hx-trigger="submit"' in rendered_output
    assert 'id="studio-export-form"' in rendered_output
    assert 'form="studio-export-form"' in rendered_output
    assert 'id="studio-export-subtab-build"' in rendered_output
    assert 'id="studio-export-open-pages-custom"' in rendered_output
    assert 'id="studio-export-scope-all"' in rendered_output
    assert 'id="studio-export-scope-custom"' in rendered_output
    assert 'id="studio-export-range"' in rendered_output
    assert 'id="studio-export-apply-range"' in rendered_output
    assert 'id="studio-export-subtab-state"' in rendered_output
    assert 'id="studio-export-selection-mode"' in rendered_output
    assert 'id="studio-export-overrides-toggle"' in rendered_output
    assert 'id="studio-export-overrides-panel"' in rendered_output
    assert 'id="studio-export-pdf-list"' in rendered_output
    assert "Crea PDF rapido (tutte le pagine)" not in rendered_output
    assert "Crea PDF selezionato" not in rendered_output
    assert "studio-export-profile-form" not in rendered_output
    assert "window.__studioExportListenersBound" in rendered_output
    assert "initStudioExport();" in rendered_output
    assert "cfg.include_cover" in rendered_output
    assert "cfg.include_colophon" in rendered_output
    assert "cfg.force_remote_refetch" in rendered_output
    assert "cfg.cleanup_temp_after_export" in rendered_output


def test_studio_optimize_scans_updates_metadata_and_feedback(tmp_path):
    """Studio optimize action should rewrite scans and expose optimization summary."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    old_max_edge = cm.get_setting("images.local_optimize.max_long_edge_px", 2600)
    old_quality = cm.get_setting("images.local_optimize.jpeg_quality", 82)
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))
        cm.set_setting("images.local_optimize.max_long_edge_px", 900)
        cm.set_setting("images.local_optimize.jpeg_quality", 55)

        vm = VaultManager()
        doc_id = "DOC_STUDIO_OPTIMIZE"
        library = "Gallica"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans = doc_root / "scans"
        data_dir = doc_root / "data"
        scans.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        scan_path = scans / "pag_0000.jpg"
        Image.new("RGB", (2400, 1800), (210, 210, 210)).save(scan_path, format="JPEG", quality=95)
        before_size = scan_path.stat().st_size
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}), encoding="utf-8"
        )

        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="partial",
            asset_state="partial",
            downloaded_canvases=1,
            total_canvases=2,
        )

        result = studio_handlers.optimize_studio_export_scans(doc_id, library, thumb_page=1, page_size=24)
        rendered = repr(result)
        assert "Ottimizzazione completata" in rendered
        assert "Ultimo:" in rendered

        row = vm.get_manuscript(doc_id) or {}
        assert int(row.get("local_optimized") or 0) == 1
        meta = json.loads(str(row.get("local_optimization_meta_json") or "{}"))
        assert int(meta.get("optimized_pages") or 0) >= 1
        assert int(meta.get("max_long_edge_px") or 0) == 900
        assert int(meta.get("jpeg_quality") or 0) == 55
        assert isinstance(meta.get("page_deltas"), list)
        assert scan_path.stat().st_size <= before_size
    finally:
        cm.set_downloads_dir(str(old_downloads))
        cm.set_setting("images.local_optimize.max_long_edge_px", old_max_edge)
        cm.set_setting("images.local_optimize.jpeg_quality", old_quality)


def test_studio_optimize_scans_rejects_path_traversal(tmp_path):
    """Studio optimize endpoint must reject paths resolving outside downloads root."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))
        result = studio_handlers.optimize_studio_export_scans("DOC_TRAV", "../outside")
        rendered = repr(result)
        assert "Percorso documento non valido" in rendered
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_studio_export_page_highres_button_has_feedback_hooks(tmp_path):
    """Thumbs endpoint should expose per-page action buttons once the lazy loader completes."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))
        doc_id = "DOC_HIGHRES_HOOKS"
        library = "Vaticana"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans_dir = doc_root / "scans"
        data_dir = doc_root / "data"
        scans_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (600, 900), (240, 240, 240)).save(scans_dir / "pag_0000.jpg", format="JPEG")
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}), encoding="utf-8"
        )
        VaultManager().upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="saved",
            asset_state="saved",
        )
        panel = studio_handlers.get_studio_export_thumbs(doc_id=doc_id, library=library, thumb_page=1, page_size=24)
    finally:
        cm.set_downloads_dir(str(old_downloads))
    rendered = repr(panel)
    assert "studio-thumb-download-btn" in rendered
    assert "studio-thumb-highres-btn" in rendered
    assert "studio-thumb-opt-btn" in rendered
    assert "studio-thumb-progress-" in rendered
    assert 'hx-target="#studio-thumb-card-1"' in rendered
    assert "/api/studio/export/page_stitch" in rendered
    assert "/api/studio/export/page_highres" in rendered
    assert "/api/studio/export/page_optimize" in rendered
    assert "studio-thumb-progress htmx-indicator" not in rendered


def test_studio_optimize_scans_selected_scope_only_updates_selected_pages(tmp_path):
    """Selected optimize scope should process selected pages and report skipped ones."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))

        vm = VaultManager()
        doc_id = "DOC_OPTIMIZE_SELECTED_SCOPE"
        library = "Gallica"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans_dir = doc_root / "scans"
        data_dir = doc_root / "data"
        scans_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1800, 1400), (240, 240, 240)).save(scans_dir / "pag_0000.jpg", format="JPEG", quality=94)
        Image.new("RGB", (1800, 1400), (210, 210, 210)).save(scans_dir / "pag_0001.jpg", format="JPEG", quality=94)
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
            encoding="utf-8",
        )
        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="partial",
            asset_state="partial",
        )

        result = studio_handlers.optimize_studio_export_scans(
            doc_id,
            library,
            thumb_page=1,
            page_size=24,
            selected_pages="1",
            optimize_scope="selected",
        )
        rendered = repr(result)
        assert "Ultimo: (sel.)" in rendered

        row = vm.get_manuscript(doc_id) or {}
        meta = json.loads(str(row.get("local_optimization_meta_json") or "{}"))
        assert int(meta.get("optimized_pages") or 0) == 1
        assert int(meta.get("skipped_pages") or 0) >= 1
        source_pref = vm.get_manuscript_ui_pref(doc_id, "studio_export_page_sources", {})
        assert isinstance(source_pref, dict)
        assert str((source_pref.get("1") or {}).get("source") or "") == "optimized"
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_studio_highres_queue_persists_page_job_without_toast(tmp_path, monkeypatch):
    """Queuing high-res should persist per-page job state and render inline feedback only."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))
        doc_id = "DOC_HIGHRES_QUEUE_STATE"
        library = "Vaticana"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans_dir = doc_root / "scans"
        data_dir = doc_root / "data"
        scans_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (600, 900), (240, 240, 240)).save(scans_dir / "pag_0000.jpg", format="JPEG")
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
            encoding="utf-8",
        )
        VaultManager().upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            manifest_url="https://example.org/manifest.json",
            status="saved",
            asset_state="saved",
        )
        captured = {}

        def _fake_start(**kwargs):
            captured.update(kwargs)
            return "job_highres_test"

        monkeypatch.setattr(studio_handlers, "start_downloader_thread", _fake_start)

        result = studio_handlers.download_highres_export_page(doc_id, library, page=1, thumb_page=1, page_size=24)
        rendered = repr(result)
        assert 'aria-label="Hi-res"' in rendered
        assert 'aria-label="Scarica"' in rendered
        assert "studio-thumb-progress-active" in rendered
        assert isinstance(result, list)
        assert 'hx-swap-oob="outerHTML:#studio-export-live-state-poller"' in rendered

        pref = VaultManager().get_manuscript_ui_pref(doc_id, "studio_export_highres_jobs", {})
        assert isinstance(pref, dict)
        assert str((pref.get("1") or {}).get("job_id") or "") == "job_highres_test"
        assert captured["job_origin"] == "studio_export_page"
        assert captured["force_max_resolution"] is True
        assert captured["stitch_mode"] == "direct_only"
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_studio_stitch_queue_persists_page_job_without_toast(tmp_path, monkeypatch):
    """Queuing stitch should persist per-page job state and render inline feedback only."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))
        doc_id = "DOC_STITCH_QUEUE_STATE"
        library = "Vaticana"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans_dir = doc_root / "scans"
        data_dir = doc_root / "data"
        scans_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (600, 900), (240, 240, 240)).save(scans_dir / "pag_0000.jpg", format="JPEG")
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
            encoding="utf-8",
        )
        VaultManager().upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            manifest_url="https://example.org/manifest.json",
            status="saved",
            asset_state="saved",
        )
        captured = {}

        def _fake_start(**kwargs):
            captured.update(kwargs)
            return "job_stitch_test"

        monkeypatch.setattr(studio_handlers, "start_downloader_thread", _fake_start)

        result = studio_handlers.download_stitch_export_page(doc_id, library, page=1, thumb_page=1, page_size=24)
        rendered = repr(result)
        assert 'aria-label="Scarica"' in rendered
        assert "studio-thumb-progress-active" in rendered
        assert isinstance(result, list)
        assert 'hx-swap-oob="outerHTML:#studio-export-live-state-poller"' in rendered

        pref = VaultManager().get_manuscript_ui_pref(doc_id, "studio_export_stitch_jobs", {})
        assert isinstance(pref, dict)
        assert str((pref.get("1") or {}).get("job_id") or "") == "job_stitch_test"
        assert captured["job_origin"] == "studio_export_page"
        assert "stitch_mode" not in captured
        assert "force_max_resolution" not in captured
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_studio_highres_completed_updates_page_source_pref(tmp_path):
    """Resolving completed high-res job should persist page source as highres."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))
        doc_id = "DOC_HIGHRES_SOURCE_PREF"
        library = "Vaticana"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans_dir = doc_root / "scans"
        data_dir = doc_root / "data"
        scans_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (600, 900), (240, 240, 240)).save(scans_dir / "pag_0000.jpg", format="JPEG")
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
            encoding="utf-8",
        )
        vm = VaultManager()
        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="saved",
            asset_state="saved",
        )
        vm.create_download_job("job_hi_done_source", doc_id, library, "https://example.org/manifest.json")
        vm.update_download_job("job_hi_done_source", current=1, total=1, status="completed")
        vm.set_manuscript_ui_pref(
            doc_id,
            "studio_export_highres_jobs",
            {"1": {"job_id": "job_hi_done_source", "state": "completed"}},
        )

        _ = studio_handlers.get_studio_export_thumbs(doc_id=doc_id, library=library, thumb_page=1, page_size=24)
        source_pref = vm.get_manuscript_ui_pref(doc_id, "studio_export_page_sources", {})
        assert isinstance(source_pref, dict)
        assert str((source_pref.get("1") or {}).get("source") or "") == "highres"
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_studio_stitch_completed_updates_page_source_pref(tmp_path):
    """Resolving completed stitch job should persist page source as stitched."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))
        doc_id = "DOC_STITCH_SOURCE_PREF"
        library = "Vaticana"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans_dir = doc_root / "scans"
        data_dir = doc_root / "data"
        scans_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (600, 900), (240, 240, 240)).save(scans_dir / "pag_0000.jpg", format="JPEG")
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
            encoding="utf-8",
        )
        vm = VaultManager()
        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="saved",
            asset_state="saved",
        )
        vm.create_download_job("job_stitch_done_source", doc_id, library, "https://example.org/manifest.json")
        vm.update_download_job("job_stitch_done_source", current=1, total=1, status="completed")
        vm.set_manuscript_ui_pref(
            doc_id,
            "studio_export_stitch_jobs",
            {"1": {"job_id": "job_stitch_done_source", "state": "completed"}},
        )

        _ = studio_handlers.get_studio_export_thumbs(doc_id=doc_id, library=library, thumb_page=1, page_size=24)
        source_pref = vm.get_manuscript_ui_pref(doc_id, "studio_export_page_sources", {})
        assert isinstance(source_pref, dict)
        assert str((source_pref.get("1") or {}).get("source") or "") == "stitched"
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_studio_export_live_state_returns_restructured_panel():
    """Live-state endpoint should render image/pdf layout plus jobs panel."""
    doc_id = "MSS_LIVE_STATE_SUBTAB"
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
    VaultManager().upsert_manuscript(
        doc_id,
        library=library,
        local_path=str(doc_root),
        status="saved",
        asset_state="saved",
    )
    panel = studio_handlers.get_studio_export_live_state(doc_id=doc_id, library=library, subtab="jobs")
    rendered = repr(panel)
    assert re.search(r'id="studio-export-subtab-jobs" class="space-y-3"', rendered)
    assert re.search(r'id="studio-export-subtab-pages" class="hidden', rendered)
    assert re.search(r'id="studio-export-subtab-build" class="hidden', rendered)


def test_export_thumbs_endpoint_preserves_highres_feedback_on_pagination(tmp_path):
    """Thumb pagination endpoint should keep per-page high-res in-flight feedback."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))

        vm = VaultManager()
        doc_id = "DOC_THUMBS_STATE"
        library = "Vaticana"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans_dir = doc_root / "scans"
        data_dir = doc_root / "data"
        scans_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        for idx in range(4):
            Image.new("RGB", (1600, 1200), (220, 220, 220)).save(scans_dir / f"pag_{idx:04d}.jpg", format="JPEG")
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
            encoding="utf-8",
        )

        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="saved",
            asset_state="saved",
            local_optimization_meta_json=json.dumps(
                {"page_deltas": [{"page": 3, "bytes_saved": 2048, "status": "ok"}]},
                ensure_ascii=False,
            ),
        )
        vm.create_download_job("job_highres_running", doc_id, library, "https://example.org/manifest.json")
        vm.update_download_job("job_highres_running", current=1, total=4, status="running")
        vm.set_manuscript_ui_pref(
            doc_id,
            "studio_export_highres_jobs",
            {"3": {"job_id": "job_highres_running", "state": "queued"}},
        )

        panel = studio_handlers.get_studio_export_thumbs(doc_id=doc_id, library=library, thumb_page=3, page_size=1)
        rendered = repr(panel)
        assert "Pag. 3" in rendered
        assert 'aria-label="Hi-res"' in rendered
        assert 'aria-label="Scarica"' in rendered
        assert 'aria-label="Ottimizza"' in rendered
        assert "studio-thumb-progress-active" in rendered
        assert "studio-thumb-progress-done" in rendered
        # All buttons disabled when busy
        assert re.search(
            r"<button[^>]*(?:studio-thumb-download-btn[^>]*disabled|disabled[^>]*studio-thumb-download-btn)",
            rendered,
        )
        assert re.search(
            r"<button[^>]*(?:studio-thumb-opt-btn[^>]*disabled|disabled[^>]*studio-thumb-opt-btn)",
            rendered,
        )
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_export_thumbs_done_state_does_not_force_remote_probe_every_refresh(tmp_path, monkeypatch):
    """Completed high-res state should reuse remote cache and avoid repeated probes."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))

        vm = VaultManager()
        doc_id = "DOC_THUMBS_NO_REPEAT_PROBE"
        library = "Vaticana"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans_dir = doc_root / "scans"
        data_dir = doc_root / "data"
        scans_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1600, 1200), (220, 220, 220)).save(scans_dir / "pag_0000.jpg", format="JPEG")
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
            encoding="utf-8",
        )
        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="saved",
            asset_state="saved",
        )
        vm.set_manuscript_ui_pref(
            doc_id,
            "studio_export_highres_jobs",
            {"1": {"job_id": "job_done_no_probe_repeat", "state": "completed", "source_ts": "2026-03-08 12:00:00"}},
        )

        calls = {"count": 0}

        def _fake_probe(_manifest_json, _page_num):
            calls["count"] += 1
            return 3200, 2400, "https://example.org/iiif/page-1"

        monkeypatch.setattr(_scan_resolution_mod, "probe_remote_max_dimensions", _fake_probe)

        _ = studio_handlers.get_studio_export_thumbs(doc_id=doc_id, library=library, thumb_page=1, page_size=24)
        _ = studio_handlers.get_studio_export_thumbs(doc_id=doc_id, library=library, thumb_page=1, page_size=24)
        assert calls["count"] == 1
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_export_thumbs_poller_disables_when_no_active_page_jobs(tmp_path):
    """Thumbs endpoint should render live poller only while page jobs are active."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))

        vm = VaultManager()
        doc_id = "DOC_THUMBS_POLLER_AUTO_STOP"
        library = "Vaticana"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans_dir = doc_root / "scans"
        data_dir = doc_root / "data"
        scans_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1600, 1200), (220, 220, 220)).save(scans_dir / "pag_0000.jpg", format="JPEG")
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
            encoding="utf-8",
        )
        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="saved",
            asset_state="saved",
        )

        vm.set_manuscript_ui_pref(
            doc_id,
            "studio_export_highres_jobs",
            {"1": {"job_id": "job_poll_active", "state": "queued", "source_ts": ""}},
        )
        active_panel = studio_handlers.get_studio_export_thumbs(
            doc_id=doc_id,
            library=library,
            thumb_page=1,
            page_size=24,
        )
        active_rendered = repr(active_panel)
        assert 'id="studio-export-live-state-poller"' in active_rendered
        assert 'hx-trigger="load, every 2s"' in active_rendered
        assert "/api/studio/export/thumbs/live?doc_id=" in active_rendered
        assert 'hx-swap="none"' in active_rendered

        vm.set_manuscript_ui_pref(
            doc_id,
            "studio_export_highres_jobs",
            {"1": {"job_id": "job_poll_done", "state": "completed", "source_ts": "2026-03-08 12:00:00"}},
        )
        idle_panel = studio_handlers.get_studio_export_thumbs(
            doc_id=doc_id,
            library=library,
            thumb_page=1,
            page_size=24,
        )
        idle_rendered = repr(idle_panel)
        assert 'id="studio-export-live-state-poller"' in idle_rendered
        assert 'hx-trigger="load, every 2s"' not in idle_rendered
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_export_thumbs_live_returns_oob_card_updates_only(tmp_path, monkeypatch):
    """Live thumbs poller should refresh visible cards via OOB swaps instead of replacing the whole slot."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))

        vm = VaultManager()
        doc_id = "DOC_THUMBS_LIVE_OOB"
        library = "Vaticana"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans_dir = doc_root / "scans"
        data_dir = doc_root / "data"
        scans_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        for idx in range(2):
            Image.new("RGB", (1600, 1200), (220, 220, 220)).save(scans_dir / f"pag_{idx:04d}.jpg", format="JPEG")
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}, {"id": "https://example.org/canvas/2"}]}),
            encoding="utf-8",
        )
        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="saved",
            asset_state="saved",
        )
        vm.create_download_job("job_live_oob", doc_id, library, "https://example.org/manifest.json")
        vm.update_download_job("job_live_oob", current=1, total=2, status="running")
        vm.set_manuscript_ui_pref(
            doc_id,
            "studio_export_highres_jobs",
            {"1": {"job_id": "job_live_oob", "state": "queued", "source_ts": ""}},
        )

        monkeypatch.setattr(
            _scan_resolution_mod,
            "probe_remote_max_dimensions",
            lambda _manifest_json, _page_num: (3200, 2400, "https://example.org/iiif/page"),
        )

        result = studio_handlers.get_studio_export_thumbs_live(
            doc_id=doc_id,
            library=library,
            thumb_page=1,
            page_size=24,
        )
        rendered = repr(result)
        assert 'hx-swap-oob="outerHTML:#studio-thumb-card-1"' in rendered
        assert 'hx-swap-oob="outerHTML:#studio-thumb-card-2"' in rendered
        assert 'hx-swap-oob="outerHTML:#studio-export-pages-summary"' in rendered
        assert 'hx-swap-oob="outerHTML:#studio-export-live-state-poller"' in rendered
        assert 'id="studio-export-thumbs-slot"' not in rendered
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_export_tab_does_not_show_stitch_badge_when_stats_mark_tile_stitch(tmp_path):
    """Thumbnail cards should rely on the progress indicator instead of a stale stitch badge."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))
        doc_id = "DOC_STITCH_BADGE"
        library = "Vaticana"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans_dir = doc_root / "scans"
        data_dir = doc_root / "data"
        scans_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1200, 1600), (240, 240, 240)).save(scans_dir / "pag_0000.jpg", format="JPEG")
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
            encoding="utf-8",
        )
        (data_dir / "image_stats.json").write_text(
            json.dumps(
                {
                    "doc_id": doc_id,
                    "pages": [{"page_index": 0, "download_method": "tile_stitch", "original_url": "stub"}],
                }
            ),
            encoding="utf-8",
        )
        VaultManager().upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="saved",
            asset_state="saved",
        )

        panel = studio_handlers.get_studio_export_thumbs(doc_id=doc_id, library=library, thumb_page=1, page_size=24)
        rendered = repr(panel)
        assert ">STITCH<" not in rendered
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_export_thumbs_marks_single_green_by_current_image_source(tmp_path):
    """Only one completed indicator should remain green based on latest source timestamp."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))

        vm = VaultManager()
        doc_id = "DOC_THUMBS_SINGLE_GREEN"
        library = "Vaticana"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans_dir = doc_root / "scans"
        data_dir = doc_root / "data"
        scans_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        for idx in range(2):
            Image.new("RGB", (1600, 1200), (220, 220, 220)).save(scans_dir / f"pag_{idx:04d}.jpg", format="JPEG")
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
            encoding="utf-8",
        )

        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="saved",
            asset_state="saved",
            local_optimization_meta_json=json.dumps(
                {
                    "optimized_at": "2026-03-08 11:00:00",
                    "page_deltas": [
                        {"page": 1, "bytes_saved": 2048, "status": "ok"},
                        {"page": 2, "bytes_saved": 2048, "status": "ok"},
                    ],
                },
                ensure_ascii=False,
            ),
        )
        vm.set_manuscript_ui_pref(
            doc_id,
            "studio_export_highres_jobs",
            {
                "1": {"job_id": "job_hi_old", "state": "completed", "source_ts": "2026-03-08 10:00:00"},
                "2": {"job_id": "job_hi_new", "state": "completed", "source_ts": "2026-03-08 12:00:00"},
            },
        )
        vm.set_manuscript_ui_pref(doc_id, "studio_export_page_sources", {})

        panel = studio_handlers.get_studio_export_thumbs(doc_id=doc_id, library=library, thumb_page=1, page_size=2)
        rendered = repr(panel)
        assert re.search(
            r'id="studio-thumb-progress-hi-1"[^>]*studio-thumb-progress-idle',
            rendered,
        )
        assert re.search(
            r'id="studio-thumb-progress-opt-1"[^>]*studio-thumb-progress-done',
            rendered,
        )
        assert re.search(
            r'id="studio-thumb-progress-hi-2"[^>]*studio-thumb-progress-done',
            rendered,
        )
        assert re.search(
            r'id="studio-thumb-progress-opt-2"[^>]*studio-thumb-progress-idle',
            rendered,
        )
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_export_thumbs_switches_green_from_opt_to_hi_after_new_highres_done(tmp_path):
    """After optimize marked current source, a new completed high-res should move green back to Hi."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))

        vm = VaultManager()
        doc_id = "DOC_THUMBS_SWITCH_OPT_TO_HI"
        library = "Vaticana"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans_dir = doc_root / "scans"
        data_dir = doc_root / "data"
        scans_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1600, 1200), (220, 220, 220)).save(scans_dir / "pag_0000.jpg", format="JPEG")
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
            encoding="utf-8",
        )
        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="saved",
            asset_state="saved",
            local_optimization_meta_json=json.dumps(
                {"optimized_at": "2026-03-08 11:00:00", "page_deltas": [{"page": 1, "status": "ok"}]},
                ensure_ascii=False,
            ),
        )
        vm.set_manuscript_ui_pref(
            doc_id,
            "studio_export_page_sources",
            {"1": {"source": "optimized", "source_ts": "123"}},
        )
        vm.create_download_job("job_hi_switch", doc_id, library, "https://example.org/manifest.json")
        vm.update_download_job("job_hi_switch", current=1, total=1, status="completed")
        vm.set_manuscript_ui_pref(
            doc_id,
            "studio_export_highres_jobs",
            {"1": {"job_id": "job_hi_switch", "state": "queued", "source_ts": ""}},
        )

        panel = studio_handlers.get_studio_export_thumbs(doc_id=doc_id, library=library, thumb_page=1, page_size=24)
        rendered = repr(panel)
        assert re.search(r'id="studio-thumb-progress-hi-1"[^>]*studio-thumb-progress-done', rendered)
        assert re.search(r'id="studio-thumb-progress-opt-1"[^>]*studio-thumb-progress-idle', rendered)
        source_pref = vm.get_manuscript_ui_pref(doc_id, "studio_export_page_sources", {})
        assert str((source_pref.get("1") or {}).get("source") or "") == "highres"
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_export_thumbs_preserves_running_highres_when_preferred_source_is_highres(tmp_path):
    """Preferred source must not mask an actively running high-res job."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))

        vm = VaultManager()
        doc_id = "DOC_THUMBS_PREF_HI_RUNNING"
        library = "Vaticana"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans_dir = doc_root / "scans"
        data_dir = doc_root / "data"
        scans_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1600, 1200), (220, 220, 220)).save(scans_dir / "pag_0000.jpg", format="JPEG")
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
            encoding="utf-8",
        )

        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="saved",
            asset_state="saved",
        )
        vm.set_manuscript_ui_pref(
            doc_id,
            "studio_export_page_sources",
            {"1": {"source": "highres", "source_ts": "2026-03-08 11:00:00"}},
        )
        vm.create_download_job("job_hi_pref_running", doc_id, library, "https://example.org/manifest.json")
        vm.update_download_job("job_hi_pref_running", current=1, total=4, status="running")
        vm.set_manuscript_ui_pref(
            doc_id,
            "studio_export_highres_jobs",
            {"1": {"job_id": "job_hi_pref_running", "state": "queued", "source_ts": "2026-03-08 11:00:00"}},
        )

        panel = studio_handlers.get_studio_export_thumbs(doc_id=doc_id, library=library, thumb_page=1, page_size=24)
        rendered = repr(panel)
        assert re.search(r'id="studio-thumb-progress-hi-1"[^>]*studio-thumb-progress-active', rendered)
        # All buttons disabled when hi-res job is active
        assert re.search(
            r"<button[^>]*(?:studio-thumb-download-btn[^>]*disabled|disabled[^>]*studio-thumb-download-btn)",
            rendered,
        )
    finally:
        cm.set_downloads_dir(str(old_downloads))


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
    panel_output = studio_handlers.get_export_tab(doc_id=doc_id, library=library, page=1, page_size=0, tab="output")
    rendered_output = repr(panel_output)
    assert 'name="page_size" value="24" id="studio-export-page-size"' in rendered_output
    panel_images = studio_handlers.get_export_tab(doc_id=doc_id, library=library, page=1, page_size=0, tab="images")
    rendered_images = repr(panel_images)
    assert 'name="page_size" value="24" id="studio-export-page-size"' in rendered_images
    assert 'data-page-size="24"' in rendered_images


def test_export_thumbs_show_iiif_and_verified_dimensions_separately(tmp_path, monkeypatch):
    """Studio cards should distinguish IIIF-declared dimensions from verified direct download dimensions."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))
        doc_id = "DOC_VERIFIED_DIRECT_DIMS"
        library = "Vaticana"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans_dir = doc_root / "scans"
        data_dir = doc_root / "data"
        scans_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (3000, 3931), (240, 240, 240)).save(scans_dir / "pag_0000.jpg", format="JPEG")
        (data_dir / "manifest.json").write_text(
            json.dumps({"items": [{"id": "https://example.org/canvas/1"}]}),
            encoding="utf-8",
        )
        (data_dir / "image_stats.json").write_text(
            json.dumps(
                {
                    "doc_id": doc_id,
                    "pages": [
                        {
                            "page_index": 0,
                            "download_method": "direct",
                            "original_url": "https://example.org/full/3000,/0/default.jpg",
                            "width": 3000,
                            "height": 3931,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        VaultManager().upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="saved",
            asset_state="saved",
        )

        monkeypatch.setattr(
            _scan_resolution_mod,
            "probe_remote_max_dimensions",
            lambda _manifest_json, _page_num: (1447, 1896, "https://example.org/iiif/page-1"),
        )

        panel = studio_handlers.get_studio_export_thumbs(doc_id=doc_id, library=library, thumb_page=1, page_size=24)
        rendered = repr(panel)
        assert "Locale 3000x3931" in rendered
        assert "Remote 1447x1896" in rendered
        assert "Dimensione verificata via download diretto: 3000x3931" in rendered
    finally:
        cm.set_downloads_dir(str(old_downloads))
