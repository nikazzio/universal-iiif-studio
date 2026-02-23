from pathlib import Path

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
