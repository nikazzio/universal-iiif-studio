from pathlib import Path

from fasthtml.common import Div

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
