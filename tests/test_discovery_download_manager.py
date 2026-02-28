from studio_ui.common.title_utils import truncate_title
from studio_ui.routes import discovery_handlers, discovery_helpers
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


def test_download_manager_shows_live_progress_counts():
    """Manager cards must render DB progress values, not always 0/0."""
    vm = VaultManager()
    vm.create_download_job("poll_progress_1", "DOC_PROGRESS", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("poll_progress_1", current=1, total=10, status="running")

    fragment = discovery_handlers.download_manager()
    text = repr(fragment)
    assert "1/10 (10%)" in text


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


def test_download_manager_completed_job_shows_studio_button():
    """Completed jobs should expose a styled Studio action button."""
    vm = VaultManager()
    vm.upsert_manuscript("DOC_STUDIO", title="Doc Studio", library="Vaticana", status="saved")
    vm.create_download_job("job_completed_studio", "DOC_STUDIO", "Vaticana", "https://example.org/manifest.json")
    vm.update_download_job("job_completed_studio", current=10, total=10, status="completed")

    fragment = discovery_handlers.download_manager()
    text = repr(fragment)
    assert "Vai allo Studio" in text


def test_download_manager_running_job_shows_pause_and_cancel():
    """Running jobs must expose pause and cancel actions."""
    vm = VaultManager()
    vm.upsert_manuscript("DOC_PAUSE_UI", title="Doc Pause", library="Gallica", status="saved")
    vm.create_download_job("job_pause_ui", "DOC_PAUSE_UI", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("job_pause_ui", current=2, total=10, status="running")

    fragment = discovery_handlers.download_manager()
    text = repr(fragment)
    assert "Pausa" in text
    assert "Annulla" in text


def test_download_manager_paused_job_shows_resume_and_remove():
    """Paused jobs must expose resume and remove actions."""
    vm = VaultManager()
    vm.upsert_manuscript("DOC_RESUME_UI", title="Doc Resume", library="Gallica", status="saved")
    vm.create_download_job("job_resume_ui", "DOC_RESUME_UI", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("job_resume_ui", current=2, total=10, status="paused", error="Paused by user")

    fragment = discovery_handlers.download_manager()
    text = repr(fragment)
    assert "Riprendi" in text
    assert "Rimuovi" in text


def test_download_manager_uses_truncated_display_title():
    """Manager must render truncated library title instead of bare doc_id."""
    vm = VaultManager()
    long_title = (
        "Oeuvres de Pierre de Bourdeille, sieur de Brantôme. XVIe et XVIIe siècles. "
        "XII Rodomontades espagnoles et Discours sur les Duels."
    )
    vm.upsert_manuscript(
        "DOC_LONG_TITLE",
        title=long_title,
        display_title=long_title,
        catalog_title=long_title,
        library="Gallica",
        status="saved",
    )
    vm.create_download_job("job_long_title", "DOC_LONG_TITLE", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("job_long_title", current=1, total=10, status="running")

    fragment = discovery_handlers.download_manager()
    text = repr(fragment)
    assert truncate_title(long_title, max_len=70, suffix="[...]") in text


def test_pause_download_requests_pause(monkeypatch):
    """Pause endpoint should delegate to job manager and return feedback."""
    vm = VaultManager()
    vm.create_download_job("job_pause_api", "DOC_PAUSE_API", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("job_pause_api", current=1, total=10, status="running")

    monkeypatch.setattr(discovery_handlers.job_manager, "request_pause", lambda _job_id: True)
    result = discovery_handlers.pause_download("job_pause_api")
    assert "Pausa richiesta" in repr(result)


def test_resume_download_requeues_paused_job(monkeypatch):
    """Resume endpoint should enqueue a new job and remove paused one."""
    vm = VaultManager()
    vm.upsert_manuscript("DOC_RESUME_API", title="Doc Resume API", library="Gallica", status="saved")
    vm.create_download_job("job_resume_api", "DOC_RESUME_API", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("job_resume_api", current=2, total=10, status="paused", error="Paused by user")

    monkeypatch.setattr(discovery_handlers, "start_downloader_thread", lambda *_a, **_k: "new_resume_job")
    result = discovery_handlers.resume_download("job_resume_api")
    assert "Resume avviato" in repr(result)
    assert vm.get_download_job("job_resume_api") is None


def test_start_downloader_thread_reuses_existing_active_job(monkeypatch):
    """Starting the same doc/library twice should reuse the active job id."""
    vm = VaultManager()
    vm.create_download_job("active_job_1", "DOC_ACTIVE", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("active_job_1", current=1, total=10, status="running")

    called = {"submit": 0}

    def _fake_submit(*_a, **_k):
        called["submit"] += 1
        return "new_job"

    monkeypatch.setattr(discovery_helpers.job_manager, "submit_job", _fake_submit)
    jid = discovery_helpers.start_downloader_thread(
        "https://example.org/manifest.json",
        "DOC_ACTIVE",
        "Gallica",
    )
    assert jid == "active_job_1"
    assert called["submit"] == 0
