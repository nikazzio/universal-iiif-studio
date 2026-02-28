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


def test_download_manager_polls_only_with_active_jobs():
    """Download manager polling should run only while active jobs exist."""
    vm = VaultManager()
    vm.create_download_job("poll_active_1", "DOC_POLL_ACTIVE", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("poll_active_1", current=1, total=10, status="running")

    active_fragment = discovery_handlers.download_manager()
    active_text = repr(active_fragment)
    assert 'hx-get="/api/download_manager"' in active_text
    assert 'hx-trigger="every 1s"' in active_text

    vm.update_download_job("poll_active_1", current=10, total=10, status="completed")
    idle_fragment = discovery_handlers.download_manager()
    idle_text = repr(idle_fragment)
    assert 'hx-get="/api/download_manager"' not in idle_text
    assert 'hx-trigger="every 1s"' not in idle_text


def test_remove_download_removes_terminal_job():
    """Terminal jobs should be removable from the download manager."""
    vm = VaultManager()
    vm.create_download_job("remove_job_1", "DOC_REMOVE", "Vaticana", "https://example.org/manifest.json")
    vm.update_download_job("remove_job_1", current=0, total=0, status="error", error="boom")

    result = discovery_handlers.remove_download("remove_job_1")
    rendered = repr(result)
    assert "Job rimosso: DOC_REMOVE." in rendered
    assert vm.get_download_job("remove_job_1") is None


def test_remove_download_rejects_active_job():
    """Active jobs should require cancellation before removal."""
    vm = VaultManager()
    vm.create_download_job("remove_job_2", "DOC_REMOVE_ACTIVE", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("remove_job_2", current=1, total=10, status="running")

    result = discovery_handlers.remove_download("remove_job_2")
    rendered = repr(result)
    assert "Rimozione non disponibile" in rendered
    assert vm.get_download_job("remove_job_2") is not None
