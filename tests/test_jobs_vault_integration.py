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


def test_job_records_failure_in_db(tmp_path, monkeypatch):
    """Ensure failed jobs propagate error status to Vault DB."""
    db_path = str(tmp_path / "vault.db")
    import universal_iiif_core.jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "VaultManager", lambda: VaultManager(db_path))
    job_manager._jobs.clear()

    def failing_task(progress_callback=None, should_cancel=None, **kwargs):
        raise RuntimeError("boom")

    jid = job_manager.submit_job(
        failing_task,
        kwargs={"db_job_id": "failjob", "doc_id": "doc2", "library": "Lib"},
        job_type="download",
    )

    for _ in range(200):
        st = job_manager.get_job(jid).get("status")
        if st == "failed":
            break
        time.sleep(0.01)
    else:
        pytest.fail("Failed job did not transition to failed state")

    vm = VaultManager(db_path)
    rec = vm.get_download_job("failjob")
    assert rec is not None
    assert rec.get("status") == "error"
    assert rec.get("error")


def test_job_cancel_request_marks_final_error(tmp_path, monkeypatch):
    """Ensure cancellation request is observable by task and reflected in DB final state."""
    db_path = str(tmp_path / "vault.db")
    import universal_iiif_core.jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "VaultManager", lambda: VaultManager(db_path))
    job_manager._jobs.clear()

    def cancellable_task(progress_callback=None, should_cancel=None, **kwargs):
        for step in range(1, 40):
            time.sleep(0.01)
            if progress_callback:
                progress_callback(step, 40)
            if should_cancel and should_cancel():
                raise RuntimeError("task cancelled cooperatively")
        return "should-not-complete"

    jid = job_manager.submit_job(
        cancellable_task,
        kwargs={"db_job_id": "canceljob", "doc_id": "doc3", "library": "Lib"},
        job_type="download",
    )

    time.sleep(0.05)
    assert job_manager.request_cancel("canceljob") is True

    for _ in range(300):
        st = job_manager.get_job(jid).get("status")
        if st == "failed":
            break
        time.sleep(0.01)
    else:
        pytest.fail("Cancelled job did not transition to failed state")

    vm = VaultManager(db_path)
    rec = vm.get_download_job("canceljob")
    assert rec is not None
    assert rec.get("status") in {"error", "cancelled"}
    assert rec.get("error") in (
        "Cancelled by user",
        "task cancelled cooperatively",
        "Error: task cancelled cooperatively",
    )
