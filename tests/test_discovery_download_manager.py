from studio_ui.routes import discovery_handlers
from universal_iiif_core.services.storage.vault_manager import VaultManager


def test_add_to_library_persists_saved_entry(monkeypatch):
    """Adding without download must persist a saved library entry."""
    monkeypatch.setattr(
        discovery_handlers,
        "analyze_manifest",
        lambda _url: {
            "label": "Test Manuscript",
            "description": "Desc",
            "pages": 12,
            "has_native_pdf": True,
        },
    )

    result = discovery_handlers.add_to_library("https://example.org/manifest.json", "DOC_A", "Gallica")
    assert "Aggiunto in Libreria" in repr(result)

    ms = VaultManager().get_manuscript("DOC_A") or {}
    assert ms.get("asset_state") == "saved"
    assert int(ms.get("total_canvases") or 0) == 12


def test_pdf_capability_badge_uses_manifest_analysis(monkeypatch):
    """PDF capability endpoint must render positive badge when manifest exposes PDF."""
    monkeypatch.setattr(discovery_handlers, "analyze_manifest", lambda _url: {"has_native_pdf": True})
    frag = discovery_handlers.pdf_capability("https://example.org/manifest.json")
    assert "PDF nativo disponibile" in repr(frag)


def test_retry_download_requeues_existing_job(monkeypatch):
    """Retry endpoint must enqueue a new download using stored job metadata."""
    vm = VaultManager()
    vm.create_download_job("retry_job_1", "DOC_R", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("retry_job_1", current=1, total=5, status="error", error="boom")

    called = {}

    def _fake_start(manifest_url, doc_id, library, target_pages=None):
        called["manifest_url"] = manifest_url
        called["doc_id"] = doc_id
        called["library"] = library
        return "new_job"

    monkeypatch.setattr(discovery_handlers, "start_downloader_thread", _fake_start)

    result = discovery_handlers.retry_download("retry_job_1")
    assert "Retry accodato" in repr(result)
    assert called["doc_id"] == "DOC_R"
