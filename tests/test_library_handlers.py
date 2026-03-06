import json
from pathlib import Path

from fasthtml.common import Div
from PIL import Image

from studio_ui.routes import library_handlers
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.services.storage.vault_manager import VaultManager


def test_library_start_download_uses_manifest(monkeypatch):
    """Library download action should use the manuscript manifest URL from DB."""
    vm = VaultManager()
    vm.upsert_manuscript(
        "DOC_LIB",
        library="Gallica",
        manifest_url="https://example.org/m.json",
        status="saved",
        asset_state="saved",
    )

    called = {}

    def _fake_start(manifest_url, doc_id, library, target_pages=None):
        called["manifest_url"] = manifest_url
        called["doc_id"] = doc_id
        called["library"] = library
        return "jid"

    monkeypatch.setattr(library_handlers, "start_downloader_thread", _fake_start)

    result = library_handlers.library_start_download("DOC_LIB", "Gallica")
    assert "Download accodato" in repr(result)
    assert called["manifest_url"] == "https://example.org/m.json"


def test_library_cleanup_partial_resets_state(tmp_path):
    """Cleanup partial must clear scans and reset manuscript state to saved."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))

        vm = VaultManager()
        doc_id = "DOC_PART"
        library = "TestLib"

        scans = Path(tmp_downloads) / library / doc_id / "scans"
        scans.mkdir(parents=True, exist_ok=True)
        (scans / "pag_0000.jpg").write_text("x", encoding="utf-8")

        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(Path(tmp_downloads) / library / doc_id),
            status="partial",
            asset_state="partial",
            downloaded_canvases=1,
            total_canvases=10,
        )

        result = library_handlers.library_cleanup_partial(doc_id, library)
        assert "Pulizia parziale completata" in repr(result)

        ms = vm.get_manuscript(doc_id) or {}
        assert ms.get("asset_state") == "saved"
        assert int(ms.get("downloaded_canvases") or 0) == 0
        assert not any(scans.glob("pag_*.jpg"))
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_library_optimize_local_scans_updates_flags_and_metadata(tmp_path):
    """Optimize action should rewrite scans in-place and persist optimization metadata."""
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
        doc_id = "DOC_OPTIMIZE"
        library = "Gallica"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans = doc_root / "scans"
        scans.mkdir(parents=True, exist_ok=True)
        scan_path = scans / "pag_0000.jpg"
        Image.new("RGB", (2400, 1800), (210, 210, 210)).save(scan_path, format="JPEG", quality=95)
        before_size = scan_path.stat().st_size

        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="partial",
            asset_state="partial",
            downloaded_canvases=1,
            total_canvases=2,
        )

        result = library_handlers.library_optimize_local_scans(doc_id, library)
        assert "Ottimizzazione completata" in repr(result)

        row = vm.get_manuscript(doc_id) or {}
        assert int(row.get("local_optimized") or 0) == 1
        meta = json.loads(str(row.get("local_optimization_meta_json") or "{}"))
        assert int(meta.get("optimized_pages") or 0) >= 1
        assert int(meta.get("max_long_edge_px") or 0) == 900
        assert int(meta.get("jpeg_quality") or 0) == 55
        assert scan_path.stat().st_size <= before_size
    finally:
        cm.set_downloads_dir(str(old_downloads))
        cm.set_setting("images.local_optimize.max_long_edge_px", old_max_edge)
        cm.set_setting("images.local_optimize.jpeg_quality", old_quality)


def test_library_optimize_local_scans_keeps_local_flags_when_optimization_fails(tmp_path, monkeypatch):
    """If optimization fails on every page, local scan availability must remain local."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))

        vm = VaultManager()
        doc_id = "DOC_OPT_FAIL"
        library = "Gallica"
        doc_root = Path(tmp_downloads) / library / doc_id
        scans = doc_root / "scans"
        scans.mkdir(parents=True, exist_ok=True)
        scan_path = scans / "pag_0000.jpg"
        Image.new("RGB", (900, 700), (180, 180, 180)).save(scan_path, format="JPEG", quality=90)

        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="partial",
            asset_state="partial",
            downloaded_canvases=1,
            total_canvases=2,
            local_scans_available=1,
            read_source_mode="local",
        )

        def _always_fail(*_args, **_kwargs):
            raise RuntimeError("forced optimize failure")

        monkeypatch.setattr(library_handlers, "_optimize_scan_file", _always_fail)

        result = library_handlers.library_optimize_local_scans(doc_id, library)
        assert "Ottimizzazione non completata" in repr(result)

        row = vm.get_manuscript(doc_id) or {}
        assert int(row.get("local_scans_available") or 0) == 1
        assert str(row.get("read_source_mode") or "") == "local"
        assert scan_path.exists()
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_library_start_download_skips_complete_entries(monkeypatch):
    """Complete items should not enqueue a full re-download from Library."""
    vm = VaultManager()
    vm.upsert_manuscript(
        "DOC_COMPLETE",
        library="Gallica",
        manifest_url="https://example.org/m.json",
        status="complete",
        asset_state="complete",
        total_canvases=10,
        downloaded_canvases=10,
    )

    called = {"count": 0}

    def _fake_start(*_a, **_k):
        called["count"] += 1
        return "jid"

    monkeypatch.setattr(library_handlers, "start_downloader_thread", _fake_start)
    result = library_handlers.library_start_download("DOC_COMPLETE", "Gallica")
    assert "già completo" in repr(result)
    assert called["count"] == 0


def test_library_retry_missing_queues_specific_pages(monkeypatch):
    """Retry missing should enqueue only missing pages from missing_pages_json."""
    vm = VaultManager()
    vm.upsert_manuscript(
        "DOC_MISS",
        library="Vaticana",
        manifest_url="https://example.org/missing.json",
        status="partial",
        asset_state="partial",
        total_canvases=8,
        downloaded_canvases=6,
        missing_pages_json="[2, 7]",
    )

    called = {}

    def _fake_start(manifest_url, doc_id, library, target_pages=None):
        called["manifest_url"] = manifest_url
        called["doc_id"] = doc_id
        called["library"] = library
        called["target_pages"] = set(target_pages or set())
        return "jid-missing"

    monkeypatch.setattr(library_handlers, "start_downloader_thread", _fake_start)
    result = library_handlers.library_retry_missing("DOC_MISS", "Vaticana")
    assert "Retry missing accodato" in repr(result)
    assert called["manifest_url"] == "https://example.org/missing.json"
    assert called["target_pages"] == {2, 7}


def test_library_refresh_metadata_card_only_returns_single_card(monkeypatch):
    """Card-only metadata refresh should return a single card fragment + toast."""
    vm = VaultManager()
    vm.upsert_manuscript(
        "DOC_META_CARD",
        library="Vaticana",
        manifest_url="https://example.org/meta.json",
        status="saved",
        asset_state="saved",
    )

    monkeypatch.setattr(library_handlers, "_update_catalog_metadata", lambda *_a, **_k: {})

    called = {}

    def _fake_render_library_card(doc, compact=False):
        called["doc_id"] = str(doc.get("id") or "")
        called["library"] = str(doc.get("library") or "")
        called["compact"] = bool(compact)
        return Div("CARD_FRAGMENT")

    monkeypatch.setattr(library_handlers, "render_library_card", _fake_render_library_card)

    result = library_handlers.library_refresh_metadata(
        "DOC_META_CARD",
        "Vaticana",
        card_only="1",
        view="list",
    )
    rendered = repr(result)
    assert "CARD_FRAGMENT" in rendered
    assert "Metadati aggiornati per DOC_META_CARD." in rendered
    assert called["doc_id"] == "DOC_META_CARD"
    assert called["library"] == "Vaticana"
    assert called["compact"] is True


def test_library_refresh_metadata_without_card_only_returns_full_page(monkeypatch):
    """Default metadata refresh should rebuild the full Library page fragment."""
    vm = VaultManager()
    vm.upsert_manuscript(
        "DOC_META_FULL",
        library="Gallica",
        manifest_url="https://example.org/meta-full.json",
        status="saved",
        asset_state="saved",
    )

    monkeypatch.setattr(library_handlers, "_update_catalog_metadata", lambda *_a, **_k: {})

    result = library_handlers.library_refresh_metadata("DOC_META_FULL", "Gallica")
    rendered = repr(result)
    assert "Libreria Locale" in rendered
    assert "Metadati aggiornati per DOC_META_FULL." in rendered


def test_row_to_view_model_detects_local_pdf_from_filesystem(tmp_path):
    """Local PDF badge data should be correct even when DB flag is stale/false."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(tmp_downloads))

        doc_id = "DOC_PDF_LOCAL"
        library = "Gallica"
        doc_root = tmp_downloads / library / doc_id
        pdf_dir = doc_root / "pdf"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        (pdf_dir / f"{doc_id}.pdf").write_bytes(b"%PDF-1.4\n%test\n")

        vm = VaultManager()
        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="complete",
            asset_state="complete",
            has_native_pdf=1,
            pdf_local_available=0,
        )
        row = vm.get_manuscript(doc_id) or {}
        model = library_handlers._row_to_view_model(row)
        assert model["pdf_local_available"] is True
        assert int(model["pdf_local_count"]) >= 1
        assert model["pdf_source"] == "native"
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_row_to_view_model_exposes_temp_pages_count(tmp_path):
    """Library rows should include temporary pages count from temp staging."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    old_temp = cm.get_temp_dir()
    try:
        tmp_downloads = tmp_path / "downloads"
        tmp_temp = tmp_path / "temp_images"
        cm.set_downloads_dir(str(tmp_downloads))
        cm.set_temp_dir(str(tmp_temp))

        doc_id = "DOC_TEMP_PAGES"
        library = "Gallica"
        doc_root = tmp_downloads / library / doc_id
        scans_dir = doc_root / "scans"
        scans_dir.mkdir(parents=True, exist_ok=True)
        (scans_dir / "pag_0000.jpg").write_bytes(b"scan")

        temp_doc_dir = tmp_temp / doc_id
        temp_doc_dir.mkdir(parents=True, exist_ok=True)
        (temp_doc_dir / "pag_0001.jpg").write_bytes(b"temp")
        (temp_doc_dir / "pag_0002.jpg").write_bytes(b"temp")

        vm = VaultManager()
        vm.upsert_manuscript(
            doc_id,
            library=library,
            local_path=str(doc_root),
            status="partial",
            asset_state="partial",
            total_canvases=3,
            downloaded_canvases=1,
        )
        row = vm.get_manuscript(doc_id) or {}
        model = library_handlers._row_to_view_model(row)
        assert int(model["local_pages_count"]) == 1
        assert int(model["temp_pages_count"]) == 2
    finally:
        cm.set_downloads_dir(str(old_downloads))
        cm.set_temp_dir(str(old_temp))


def test_library_fragment_uses_config_default_mode_when_missing_mode():
    """When mode is missing, Library should use configurable default mode."""
    cm = get_config_manager()
    old_default_mode = cm.get_setting("library.default_mode", "operativa")
    try:
        cm.set_setting("library.default_mode", "archivio")
        rendered = repr(library_handlers._render_page_fragment(mode=""))
        assert "Vista Archivio" in rendered
        assert 'const DEFAULT_MODE = "archivio";' in rendered
    finally:
        cm.set_setting("library.default_mode", old_default_mode)
