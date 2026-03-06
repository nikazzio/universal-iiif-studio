from studio_ui.common.title_utils import truncate_title
from studio_ui.routes import discovery_handlers, discovery_helpers
from universal_iiif_core.config_manager import get_config_manager
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
    monkeypatch.setattr(
        discovery_handlers,
        "get_json",
        lambda _url, retries=2: {"items": [{"id": "canvas-1"}, {"id": "canvas-2"}]},
    )

    result = discovery_handlers.add_to_library("https://example.org/manifest.json", "DOC_A", "Gallica")
    assert "Aggiunto in Libreria" in repr(result)

    ms = VaultManager().get_manuscript("DOC_A") or {}
    assert ms.get("asset_state") == "saved"
    assert int(ms.get("total_canvases") or 0) == 12
    assert int(ms.get("manifest_local_available") or 0) == 1
    doc_data = get_config_manager().get_downloads_dir() / "Gallica" / "DOC_A" / "data"
    assert (doc_data / "metadata.json").exists()
    assert (doc_data / "manifest.json").exists()


def test_add_to_library_rejects_path_traversal_and_does_not_write(monkeypatch, tmp_path):
    """Traversal in library/doc_id must be rejected before any filesystem write."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    tmp_downloads = tmp_path / "downloads"
    cm.set_downloads_dir(str(tmp_downloads))
    try:
        monkeypatch.setattr(
            discovery_handlers,
            "analyze_manifest",
            lambda _url: {"label": "Unsafe", "description": "", "pages": 1},
        )
        called = {"count": 0}

        def _fake_get_json(_url, retries=2):
            called["count"] += 1
            return {"items": [{"id": "canvas-1"}]}

        monkeypatch.setattr(discovery_handlers, "get_json", _fake_get_json)

        result = discovery_handlers.add_to_library(
            "https://example.org/manifest.json",
            "DOC_TRAVERSAL",
            "../outside",
        )
        rendered = repr(result)
        assert "Errore Input" in rendered
        assert "Identificatore documento non valido." in rendered
        assert called["count"] == 0
        assert not (tmp_path / "outside").exists()
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_pdf_capability_badge_uses_quick_probe(monkeypatch):
    """PDF capability endpoint should use lightweight probe path."""
    monkeypatch.setattr(discovery_handlers, "_quick_manifest_has_native_pdf", lambda _url: True)
    frag = discovery_handlers.pdf_capability("https://example.org/manifest.json")
    assert "PDF nativo disponibile" in repr(frag)


def test_add_and_download_skips_already_complete_item(monkeypatch):
    """Discovery should not queue a new download when item is already complete."""
    vm = VaultManager()
    vm.upsert_manuscript(
        "DOC_ALREADY_COMPLETE",
        library="Gallica",
        manifest_url="https://example.org/manifest.json",
        status="complete",
        asset_state="complete",
        total_canvases=10,
        downloaded_canvases=10,
    )

    called = {"count": 0}

    def _fake_start(*_a, **_k):
        called["count"] += 1
        return "jid"

    monkeypatch.setattr(discovery_handlers, "start_downloader_thread", _fake_start)

    result = discovery_handlers.add_and_download(
        "https://example.org/manifest.json",
        "DOC_ALREADY_COMPLETE",
        "Gallica",
    )
    assert "Documento già completo in libreria" in repr(result)
    assert called["count"] == 0


def test_retry_download_requeues_existing_job(monkeypatch):
    """Retry endpoint must reuse the same job id using stored job metadata."""
    vm = VaultManager()
    vm.create_download_job("retry_job_1", "DOC_R", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("retry_job_1", current=1, total=5, status="error", error="boom")

    called = {}

    def _fake_start(manifest_url, doc_id, library, target_pages=None, existing_job_id=None):
        called["manifest_url"] = manifest_url
        called["doc_id"] = doc_id
        called["library"] = library
        called["existing_job_id"] = existing_job_id
        return existing_job_id or "new_job"

    monkeypatch.setattr(discovery_handlers, "start_downloader_thread", _fake_start)

    result = discovery_handlers.retry_download("retry_job_1")
    assert "Retry accodato" in repr(result)
    assert called["doc_id"] == "DOC_R"
    assert called["existing_job_id"] == "retry_job_1"


def test_download_manager_polls_only_with_active_jobs():
    """Download manager polling should run only while active jobs exist."""
    vm = VaultManager()
    vm.create_download_job("poll_active_1", "DOC_POLL_ACTIVE", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("poll_active_1", current=1, total=10, status="running")

    active_fragment = discovery_handlers.download_manager()
    active_text = repr(active_fragment)
    assert 'hx-get="/api/download_manager"' in active_text
    assert 'hx-trigger="every 3s"' in active_text

    vm.update_download_job("poll_active_1", current=10, total=10, status="completed")
    idle_fragment = discovery_handlers.download_manager()
    idle_text = repr(idle_fragment)
    assert 'hx-get="/api/download_manager"' not in idle_text
    assert 'hx-trigger="every 3s"' not in idle_text


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
    assert "2/10 pagine" in text


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


def test_pause_download_fallback_clears_error_field(monkeypatch):
    """Queued fallback pause should not persist an error message."""
    vm = VaultManager()
    vm.create_download_job("job_pause_fallback", "DOC_PAUSE_FB", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("job_pause_fallback", current=0, total=10, status="queued")

    monkeypatch.setattr(discovery_handlers.job_manager, "request_pause", lambda _job_id: False)
    result = discovery_handlers.pause_download("job_pause_fallback")
    assert "Pausa richiesta" in repr(result)

    row = vm.get_download_job("job_pause_fallback") or {}
    assert str(row.get("status") or "").lower() == "paused"
    assert row.get("error") is None


def test_cancel_download_marks_cancelling_without_error(monkeypatch):
    """Cancelling state should not be represented as an error message."""
    vm = VaultManager()
    vm.create_download_job("job_cancel_api", "DOC_CANCEL_API", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("job_cancel_api", current=2, total=10, status="running")

    monkeypatch.setattr(discovery_handlers.job_manager, "request_cancel", lambda _job_id: True)
    monkeypatch.setattr(
        discovery_handlers.job_manager,
        "list_jobs",
        lambda active_only=False: {"runtime_1": {"db_job_id": "job_cancel_api", "status": "running"}},
    )
    result = discovery_handlers.cancel_download("job_cancel_api")
    assert "Annullamento richiesto" in repr(result)

    row = vm.get_download_job("job_cancel_api") or {}
    assert str(row.get("status") or "").lower() == "cancelling"
    assert row.get("error") is None


def test_cancel_download_orphan_finalizes_cancelled(monkeypatch):
    """When no runtime owner exists, cancel should close immediately."""
    vm = VaultManager()
    vm.create_download_job("job_cancel_orphan", "DOC_CANCEL_ORPHAN", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("job_cancel_orphan", current=2, total=10, status="running")

    monkeypatch.setattr(discovery_handlers.job_manager, "request_cancel", lambda _job_id: False)
    result = discovery_handlers.cancel_download("job_cancel_orphan")
    assert "Annullamento completato" in repr(result)

    row = vm.get_download_job("job_cancel_orphan") or {}
    assert str(row.get("status") or "").lower() == "cancelled"
    assert row.get("error") is None


def test_pause_download_orphan_running_finalizes_paused(monkeypatch):
    """When no runtime owner exists, pause on running should close to paused."""
    vm = VaultManager()
    vm.create_download_job("job_pause_orphan", "DOC_PAUSE_ORPHAN", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("job_pause_orphan", current=3, total=10, status="running")

    monkeypatch.setattr(discovery_handlers.job_manager, "request_pause", lambda _job_id: False)
    result = discovery_handlers.pause_download("job_pause_orphan")
    assert "Pausa richiesta" in repr(result)

    row = vm.get_download_job("job_pause_orphan") or {}
    assert str(row.get("status") or "").lower() == "paused"
    assert row.get("error") is None


def test_download_manager_finalizes_orphan_stop_requests(monkeypatch):
    """Polling should auto-close stale pausing/cancelling rows without runtime owner."""
    vm = VaultManager()
    vm.create_download_job("job_pausing_orphan", "DOC_P_ORPHAN", "Gallica", "https://example.org/manifest.json")
    vm.create_download_job("job_cancelling_orphan", "DOC_C_ORPHAN", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("job_pausing_orphan", current=2, total=10, status="pausing", error=None)
    vm.update_download_job("job_cancelling_orphan", current=2, total=10, status="cancelling", error=None)

    monkeypatch.setattr(discovery_handlers.job_manager, "list_jobs", lambda active_only=False: {})
    _ = discovery_handlers.download_manager()

    pausing_row = vm.get_download_job("job_pausing_orphan") or {}
    cancelling_row = vm.get_download_job("job_cancelling_orphan") or {}
    assert str(pausing_row.get("status") or "").lower() == "paused"
    assert str(cancelling_row.get("status") or "").lower() == "cancelled"


def test_resume_download_reuses_same_job(monkeypatch):
    """Resume endpoint should reuse the same download id from manager row."""
    vm = VaultManager()
    vm.upsert_manuscript("DOC_RESUME_API", title="Doc Resume API", library="Gallica", status="saved")
    vm.create_download_job("job_resume_api", "DOC_RESUME_API", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("job_resume_api", current=2, total=10, status="paused", error="Paused by user")

    called = {}

    def _fake_start(manifest_url, doc_id, library, target_pages=None, existing_job_id=None):
        called["manifest_url"] = manifest_url
        called["doc_id"] = doc_id
        called["library"] = library
        called["existing_job_id"] = existing_job_id
        return existing_job_id or "new_resume_job"

    monkeypatch.setattr(discovery_handlers, "start_downloader_thread", _fake_start)
    result = discovery_handlers.resume_download("job_resume_api")
    assert "Resume avviato" in repr(result)
    assert (vm.get_download_job("job_resume_api") or {}).get("status") == "paused"
    assert called["doc_id"] == "DOC_RESUME_API"
    assert called["existing_job_id"] == "job_resume_api"


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


def test_start_downloader_thread_uses_requested_existing_job_id(monkeypatch):
    """Download manager resume/retry should keep the same persisted job id."""
    captured = {}

    def _fake_submit(task_func, kwargs=None, job_type="generic"):
        captured["task_func"] = task_func
        captured["kwargs"] = dict(kwargs or {})
        captured["job_type"] = job_type
        return "internal_job"

    monkeypatch.setattr(discovery_helpers.job_manager, "submit_job", _fake_submit)

    jid = discovery_helpers.start_downloader_thread(
        "https://example.org/manifest.json",
        "DOC_KEEP_ID",
        "Gallica",
        existing_job_id="job_keep_1",
    )

    assert jid == "job_keep_1"
    assert captured["job_type"] == "download"
    assert captured["kwargs"]["db_job_id"] == "job_keep_1"
