import time

import pytest

import universal_iiif_core.jobs as jobs_mod
from universal_iiif_core.jobs import job_manager
from universal_iiif_core.services.storage.vault_manager import VaultManager

# Mark entire file as slow (has time.sleep and async job queue tests)
pytestmark = pytest.mark.slow


class _Cfg:
    data = {"settings": {"network": {"global": {"max_concurrent_download_jobs": 1}}}}

    def get_setting(self, key, default=None):
        if key == "network.global.max_concurrent_download_jobs":
            return 1
        return default


def test_download_jobs_are_queued_when_concurrency_is_limited(tmp_path, monkeypatch):
    """With concurrency=1, second download should stay queued while first is running."""
    db_path = str(tmp_path / "vault.db")
    monkeypatch.setattr(jobs_mod, "VaultManager", lambda: VaultManager(db_path))
    monkeypatch.setattr(jobs_mod, "get_config_manager", lambda: _Cfg())

    job_manager._jobs.clear()
    job_manager._download_queue.clear()
    job_manager._active_downloads.clear()

    def _slow_task(progress_callback=None, should_cancel=None, **kwargs):
        if progress_callback:
            progress_callback(0, 10)
        time.sleep(0.25)
        if progress_callback:
            progress_callback(10, 10)
        return "ok"

    job_manager.submit_job(
        _slow_task,
        kwargs={"db_job_id": "qjob_1", "doc_id": "DOC1", "library": "Lib", "manifest_url": "u1"},
        job_type="download",
    )
    job_manager.submit_job(
        _slow_task,
        kwargs={"db_job_id": "qjob_2", "doc_id": "DOC2", "library": "Lib", "manifest_url": "u2"},
        job_type="download",
    )

    time.sleep(0.05)
    vm = VaultManager(db_path)
    first = vm.get_download_job("qjob_1") or {}
    second = vm.get_download_job("qjob_2") or {}

    statuses = {first.get("status"), second.get("status")}
    assert "queued" in statuses
    assert "running" in statuses or "completed" in statuses

    for _ in range(40):
        first = vm.get_download_job("qjob_1") or {}
        second = vm.get_download_job("qjob_2") or {}
        if first.get("status") in {"completed", "error", "cancelled"} and second.get("status") in {
            "completed",
            "error",
            "cancelled",
        }:
            break
        time.sleep(0.05)


def test_request_pause_does_not_mark_cancel_requested(monkeypatch):
    """Pausing must keep cancellation semantics separate."""
    job_manager._jobs.clear()
    job_manager._download_queue.clear()
    job_manager._active_downloads.clear()

    job_manager._jobs["job_pause"] = {
        "id": "job_pause",
        "db_job_id": "db_pause",
        "status": "running",
        "message": "Running",
        "pause_requested": False,
        "cancel_requested": False,
    }
    monkeypatch.setattr(job_manager, "_update_db_safe", lambda *args, **kwargs: None)

    assert job_manager.request_pause("db_pause") is True
    snapshot = job_manager.get_job("job_pause") or {}
    assert snapshot.get("pause_requested") is True
    assert snapshot.get("cancel_requested") is False


def test_request_cancel_clears_pause_flag(monkeypatch):
    """Cancellation should override a prior pause request."""
    job_manager._jobs.clear()
    job_manager._download_queue.clear()
    job_manager._active_downloads.clear()

    job_manager._jobs["job_cancel"] = {
        "id": "job_cancel",
        "db_job_id": "db_cancel",
        "status": "running",
        "message": "Pausing...",
        "pause_requested": True,
        "cancel_requested": False,
    }
    monkeypatch.setattr(job_manager, "_update_db_safe", lambda *args, **kwargs: None)

    assert job_manager.request_cancel("db_cancel") is True
    snapshot = job_manager.get_job("job_cancel") or {}
    assert snapshot.get("cancel_requested") is True
    assert snapshot.get("pause_requested") is False


def test_request_pause_targets_active_attempt_with_same_db_id(monkeypatch):
    """Pause by db_job_id should hit the live running attempt, not stale history."""
    job_manager._jobs.clear()
    job_manager._download_queue.clear()
    job_manager._active_downloads.clear()

    job_manager._jobs["old_attempt"] = {
        "id": "old_attempt",
        "db_job_id": "db_same",
        "status": "paused",
        "message": "Paused by user",
        "pause_requested": False,
        "cancel_requested": False,
        "created_at": 1.0,
        "thread": None,
    }
    job_manager._jobs["new_attempt"] = {
        "id": "new_attempt",
        "db_job_id": "db_same",
        "status": "running",
        "message": "Running",
        "pause_requested": False,
        "cancel_requested": False,
        "created_at": 2.0,
        "thread": None,
    }
    monkeypatch.setattr(job_manager, "_update_db_safe", lambda *args, **kwargs: None)

    assert job_manager.request_pause("db_same") is True
    assert str((job_manager.get_job("new_attempt") or {}).get("status") or "").lower() == "pausing"


def test_list_jobs_active_includes_stop_transitional_states():
    """Active view should include pausing/cancelling states."""
    job_manager._jobs.clear()
    job_manager._jobs["job_pausing"] = {"status": "pausing"}
    job_manager._jobs["job_cancelling"] = {"status": "cancelling"}
    job_manager._jobs["job_done"] = {"status": "completed"}

    active = job_manager.list_jobs(active_only=True)
    assert "job_pausing" in active
    assert "job_cancelling" in active
    assert "job_done" not in active


def test_resume_submission_preserves_existing_progress(tmp_path, monkeypatch):
    """Requeued runs with same db_job_id must keep prior current/total counters."""
    db_path = str(tmp_path / "vault.db")
    monkeypatch.setattr(jobs_mod, "VaultManager", lambda: VaultManager(db_path))
    monkeypatch.setattr(jobs_mod, "get_config_manager", lambda: _Cfg())

    job_manager._jobs.clear()
    job_manager._download_queue.clear()
    job_manager._active_downloads.clear()

    vm = VaultManager(db_path)
    vm.create_download_job("job_resume_keep", "DOC_KEEP", "Gallica", "https://example.org/manifest.json")
    vm.update_download_job("job_resume_keep", current=4, total=12, status="paused", error=None)

    def _slow_task(progress_callback=None, should_cancel=None, **kwargs):
        time.sleep(0.12)
        return "ok"

    jid = job_manager.submit_job(
        _slow_task,
        kwargs={
            "db_job_id": "job_resume_keep",
            "doc_id": "DOC_KEEP",
            "library": "Gallica",
            "manifest_url": "https://example.org/manifest.json",
        },
        job_type="download",
    )

    time.sleep(0.03)
    row = vm.get_download_job("job_resume_keep") or {}
    assert int(row.get("current") or 0) == 4
    assert int(row.get("total") or 0) == 12

    for _ in range(100):
        snapshot = job_manager.get_job(jid) or {}
        if str(snapshot.get("status") or "").lower() in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.01)
