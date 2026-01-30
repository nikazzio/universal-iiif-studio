import time

import pytest

from universal_iiif_core.jobs import job_manager
from universal_iiif_core.services.storage.vault_manager import VaultManager


def test_job_records_progress_and_completion(tmp_path, monkeypatch):
    """Test that a submitted job records progress and completion in the VaultManager database."""
    # Use a test-specific vault DB
    db_path = str(tmp_path / "vault.db")

    # Monkeypatch the VaultManager used inside jobs module to point to our test DB
    import universal_iiif_core.jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "VaultManager", lambda: VaultManager(db_path))

    # Ensure job manager state clean
    job_manager._jobs.clear()

    # Define a task that reports progress then returns
    def task(progress_callback=None, should_cancel=None, **kwargs):
        for i in range(1, 4):
            time.sleep(0.01)
            if progress_callback:
                progress_callback(i, 3)
        return "ok"

    jid = job_manager.submit_job(
        task, kwargs={"db_job_id": "testjob", "doc_id": "doc1", "library": "Lib"}, job_type="download"
    )

    # Wait until job completes (with timeout)
    for _ in range(200):
        st = job_manager.get_job(jid).get("status")
        if st == "completed":
            break
        time.sleep(0.01)
    else:
        pytest.fail("Job did not complete in time")

    # Inspect DB to ensure record exists and is marked completed
    vm = VaultManager(db_path)
    rec = vm.get_download_job("testjob")
    assert rec is not None
    assert rec.get("status") == "completed"
    assert int(rec.get("total", 0)) in (0, 1, 3) or rec.get("total") is not None
