import time

import universal_iiif_core.jobs as jobs_mod
from universal_iiif_core.jobs import job_manager
from universal_iiif_core.services.storage.vault_manager import VaultManager


class _Cfg:
    def get_setting(self, key, default=None):
        if key == "system.max_concurrent_downloads":
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
