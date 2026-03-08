import json
from pathlib import Path

from PIL import Image
from starlette.requests import Request

from studio_ui.common.title_utils import truncate_title
from studio_ui.routes import studio_handlers
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.services.storage.vault_manager import VaultManager


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
        assert "const containerId = 'mirador-viewer';" not in rendered
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
        assert "const containerId = 'mirador-viewer';" in rendered
    finally:
        cm.set_setting("viewer.mirador.require_complete_local_images", old_gate)


def test_studio_saved_remote_first_bypasses_local_gate():
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
        response = studio_handlers.studio_page(_request(), doc_id=doc_id, library=library, page=1)
        rendered = str(response)
        assert 'data-mirador-gated="1"' not in rendered
        assert "const containerId = 'mirador-viewer';" in rendered
        assert "read_source:" in rendered
        assert "remote" in rendered
    finally:
        cm.set_setting("viewer.mirador.require_complete_local_images", old_gate)
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
    assert "Apri il tab Output per caricare miniature" in rendered
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
    assert rendered.find('id="studio-export-pdf-list"') < rendered.find('id="studio-export-form"')
    assert 'id="studio-export-thumb-size-select"' in rendered
    assert 'name="page_size"' in rendered
    assert 'hx-trigger="change"' in rendered
    assert 'id="studio-export-subtab-btn-build"' in rendered
    assert 'id="studio-export-subtab-btn-pages"' in rendered
    assert 'id="studio-export-subtab-btn-jobs"' in rendered
    assert 'id="studio-export-subtab-build"' in rendered
    assert 'id="studio-export-subtab-pages"' in rendered
    assert 'id="studio-export-subtab-jobs"' in rendered
    assert 'class="studio-export-subtabs' in rendered
    assert 'class="studio-export-subtab studio-export-subtab-active"' in rendered
    assert 'id="studio-export-scope-all"' in rendered
    assert 'id="studio-export-scope-custom"' in rendered
    assert 'id="studio-export-selection-mode"' in rendered
    assert 'id="studio-export-overrides-toggle"' in rendered
    assert 'id="studio-export-overrides-panel"' in rendered
    assert "Crea PDF rapido (tutte le pagine)" not in rendered
    assert "Crea PDF selezionato" not in rendered
    assert "studio-thumb-meta" in rendered
    assert "studio-thumb-highres-btn" in rendered
    assert 'id="studio-export-optimize-btn"' in rendered
    assert 'id="studio-export-live-state-poller"' in rendered
    assert 'hx-target="#studio-export-thumbs-slot"' in rendered
    assert "/api/studio/export/thumbs?doc_id=" in rendered
    assert "data-export-subtab" in rendered
    assert "studio-export-profile-form" not in rendered
    assert "window.__studioExportListenersBound" in rendered
    assert "initStudioExport();" in rendered


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
        assert "Ultimo run:" in rendered

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
    """High-res button should include panel state and indicator hooks."""
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
        panel = studio_handlers.get_export_tab(doc_id=doc_id, library=library, page=1)
    finally:
        cm.set_downloads_dir(str(old_downloads))
    rendered = repr(panel)
    assert "studio-thumb-highres-btn" in rendered
    assert "studio-thumb-progress-" in rendered
    assert 'hx-include="#studio-export-selected-pages,#studio-export-thumb-page,#studio-export-page-size"' in rendered


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
        assert "Ultimo run: (selezione)" in rendered

        row = vm.get_manuscript(doc_id) or {}
        meta = json.loads(str(row.get("local_optimization_meta_json") or "{}"))
        assert int(meta.get("optimized_pages") or 0) == 1
        assert int(meta.get("skipped_pages") or 0) >= 1
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
        monkeypatch.setattr(studio_handlers, "start_downloader_thread", lambda **_kwargs: "job_highres_test")

        result = studio_handlers.download_highres_export_page(doc_id, library, page=1, thumb_page=1, page_size=24)
        rendered = repr(result)
        assert "⬇ Hi" in rendered
        assert "studio-thumb-progress-active" in rendered
        assert not isinstance(result, list)

        pref = VaultManager().get_manuscript_ui_pref(doc_id, "studio_export_highres_jobs", {})
        assert isinstance(pref, dict)
        assert str((pref.get("1") or {}).get("job_id") or "") == "job_highres_test"
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_studio_export_live_state_keeps_requested_subtab():
    """Live-state endpoint should preserve requested subtab instead of forcing pages."""
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
    assert 'id="studio-export-subtab-jobs" class="mt-3"' in rendered


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
                {"page_deltas": [{"page": 3, "bytes_saved": 2048}]},
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
        assert "⬇ Hi" in rendered
        assert "studio-thumb-progress-active" in rendered
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
    panel = studio_handlers.get_export_tab(doc_id=doc_id, library=library, page=1, page_size=0)
    rendered = repr(panel)
    assert 'name="page_size" value="24" id="studio-export-page-size"' in rendered
    assert 'id="studio-export-thumb-size-select"' in rendered
