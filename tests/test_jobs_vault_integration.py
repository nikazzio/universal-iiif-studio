import time
from pathlib import Path

import pytest
from PIL import Image

from universal_iiif_core.jobs import job_manager
from universal_iiif_core.services.storage.vault_manager import VaultManager


class _PromotionCfg:
    data = {"settings": {"network": {"global": {"max_concurrent_download_jobs": 1}}}}

    def __init__(self, *, temp_root: Path, downloads_root: Path):
        self._temp_root = temp_root
        self._downloads_root = downloads_root

    def get_setting(self, key, default=None):
        if key == "network.global.max_concurrent_download_jobs":
            return 1
        if key == "storage.partial_promotion_mode":
            return "on_pause"
        return default

    def get_temp_dir(self):
        return self._temp_root

    def get_downloads_dir(self):
        return self._downloads_root


def _wait_until(predicate, *, timeout_s: float = 3.0, step_s: float = 0.01) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(step_s)
    return False


def _cooperative_pause_task(progress_callback=None, should_cancel=None, **kwargs):
    for step in range(1, 20):
        time.sleep(0.01)
        if progress_callback:
            progress_callback(step, 20)
        if should_cancel and should_cancel():
            raise RuntimeError("task paused cooperatively")
    return "should-not-complete"


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


def test_job_cancel_request_marks_final_cancelled_state(tmp_path, monkeypatch):
    """Ensure cancellation request is reflected as a cancelled (non-error) final DB state."""
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
        if st == "cancelled":
            break
        time.sleep(0.01)
    else:
        pytest.fail("Cancelled job did not transition to cancelled state")

    vm = VaultManager(db_path)
    for _ in range(300):
        rec = vm.get_download_job("canceljob")
        if rec and str(rec.get("status") or "").lower() == "cancelled":
            break
        time.sleep(0.01)
    else:
        pytest.fail("Cancelled job did not transition to cancelled state in DB")

    assert rec is not None
    assert rec.get("status") == "cancelled"
    assert rec.get("error") is None


def test_job_pause_request_marks_final_paused_state(tmp_path, monkeypatch):
    """Pause request on a running task should end in paused, not cancelled."""
    db_path = str(tmp_path / "vault.db")
    import universal_iiif_core.jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "VaultManager", lambda: VaultManager(db_path))
    job_manager._jobs.clear()
    job_manager._download_queue.clear()
    job_manager._active_downloads.clear()

    def pausable_task(progress_callback=None, should_cancel=None, **kwargs):
        for step in range(1, 40):
            time.sleep(0.01)
            if progress_callback:
                progress_callback(step, 40)
            if should_cancel and should_cancel():
                raise RuntimeError("task paused cooperatively")
        return "should-not-complete"

    job_manager.submit_job(
        pausable_task,
        kwargs={"db_job_id": "pausejob", "doc_id": "doc4", "library": "Lib"},
        job_type="download",
    )

    time.sleep(0.05)
    assert job_manager.request_pause("pausejob") is True

    vm = VaultManager(db_path)
    for _ in range(300):
        rec = vm.get_download_job("pausejob")
        if rec and str(rec.get("status") or "").lower() == "paused":
            break
        time.sleep(0.01)
    else:
        pytest.fail("Paused job did not transition to paused state in DB")

    assert rec is not None
    assert rec.get("status") == "paused"
    assert rec.get("error") is None


def test_pause_promotes_validated_temp_pages_when_mode_on_pause(tmp_path, monkeypatch):
    """When configured, pausing should promote validated staged pages into scans."""
    db_path = str(tmp_path / "vault.db")
    downloads_root = tmp_path / "downloads"
    temp_root = tmp_path / "temp_images"
    doc_id = "doc_promote"
    library = "Lib"
    temp_dir = temp_root / doc_id
    scans_dir = downloads_root / library / doc_id / "scans"
    temp_dir.mkdir(parents=True, exist_ok=True)
    scans_dir.mkdir(parents=True, exist_ok=True)

    staged = temp_dir / "pag_0000.jpg"
    Image.new("RGB", (20, 20), color="white").save(staged, format="JPEG")

    import universal_iiif_core.jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "VaultManager", lambda: VaultManager(db_path))
    monkeypatch.setattr(
        jobs_mod,
        "get_config_manager",
        lambda: _PromotionCfg(temp_root=Path(temp_root), downloads_root=Path(downloads_root)),
    )
    job_manager._jobs.clear()
    job_manager._download_queue.clear()
    job_manager._active_downloads.clear()

    job_manager.submit_job(
        _cooperative_pause_task,
        kwargs={"db_job_id": "pausepromote", "doc_id": doc_id, "library": library},
        job_type="download",
    )

    time.sleep(0.05)
    assert job_manager.request_pause("pausepromote") is True

    vm = VaultManager(db_path)

    def _is_paused() -> bool:
        rec = vm.get_download_job("pausepromote")
        return bool(rec and str(rec.get("status") or "").lower() == "paused")

    if not _wait_until(_is_paused):
        pytest.fail("Paused job did not transition to paused state in DB")
    if not _wait_until(lambda: (scans_dir / "pag_0000.jpg").exists()):
        pytest.fail("Validated staged page was not promoted to scans on pause")

    assert not staged.exists()


def test_pause_promotion_overwrites_existing_scan_when_flag_enabled(tmp_path, monkeypatch):
    """Pause promotion must keep overwrite semantics for redownload flows."""
    db_path = str(tmp_path / "vault.db")
    downloads_root = tmp_path / "downloads"
    temp_root = tmp_path / "temp_images"
    doc_id = "doc_overwrite"
    library = "Lib"
    temp_dir = temp_root / doc_id
    scans_dir = downloads_root / library / doc_id / "scans"
    temp_dir.mkdir(parents=True, exist_ok=True)
    scans_dir.mkdir(parents=True, exist_ok=True)

    destination = scans_dir / "pag_0000.jpg"
    Image.new("RGB", (20, 20), color="black").save(destination, format="JPEG")
    before_bytes = destination.read_bytes()

    staged = temp_dir / "pag_0000.jpg"
    Image.new("RGB", (20, 20), color="white").save(staged, format="JPEG")

    import universal_iiif_core.jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "VaultManager", lambda: VaultManager(db_path))
    monkeypatch.setattr(
        jobs_mod,
        "get_config_manager",
        lambda: _PromotionCfg(temp_root=Path(temp_root), downloads_root=Path(downloads_root)),
    )
    job_manager._jobs.clear()
    job_manager._download_queue.clear()
    job_manager._active_downloads.clear()

    job_manager.submit_job(
        _cooperative_pause_task,
        kwargs={
            "db_job_id": "pauseoverwrite",
            "doc_id": doc_id,
            "library": library,
            "overwrite_existing_scans": True,
        },
        job_type="download",
    )

    time.sleep(0.05)
    assert job_manager.request_pause("pauseoverwrite") is True

    vm = VaultManager(db_path)

    if not _wait_until(lambda: bool((vm.get_download_job("pauseoverwrite") or {}).get("status") == "paused")):
        pytest.fail("Paused job did not transition to paused state in DB")
    if not _wait_until(lambda: destination.exists() and not staged.exists()):
        pytest.fail("Pause promotion did not consume staged overwrite file")

    after_bytes = destination.read_bytes()
    assert before_bytes != after_bytes
