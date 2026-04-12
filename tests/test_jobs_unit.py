"""Tests for JobManager state machine — pure in-memory operations."""

from __future__ import annotations

import time
from collections import deque
from pathlib import Path
from unittest.mock import MagicMock

from universal_iiif_core.jobs import JobManager


def _fresh_job_manager() -> JobManager:
    """Create an isolated JobManager with reset state (bypasses singleton).

    Uses object.__new__ to avoid triggering the singleton __new__.
    Restores the class _instance after test via a separate approach.
    """
    jm = object.__new__(JobManager)
    jm._jobs = {}
    jm._lock = __import__("threading").Lock()
    jm._download_queue = deque()
    jm._active_downloads = set()
    return jm


def _seed_job(jm: JobManager, job_id: str, **overrides) -> dict:
    """Insert a job dict directly into the manager."""
    job = {
        "id": job_id,
        "type": "download",
        "status": "running",
        "progress": 0.0,
        "message": "",
        "result": None,
        "error": None,
        "created_at": time.time(),
        "cancel_requested": False,
        "pause_requested": False,
        "db_job_id": overrides.get("db_job_id", job_id),
        "task_func": lambda: None,
        "args": (),
        "kwargs": {},
        "thread": None,
        "queue_position": 0,
        "priority": 0,
    }
    job.update(overrides)
    jm._jobs[job_id] = job
    return job


# --- update_job ---

class TestUpdateJob:
    def test_update_status(self):
        jm = _fresh_job_manager()
        _seed_job(jm, "j1", status="running")
        jm.update_job("j1", status="completed")
        assert jm._jobs["j1"]["status"] == "completed"

    def test_update_progress(self):
        jm = _fresh_job_manager()
        _seed_job(jm, "j1")
        jm.update_job("j1", progress=0.5)
        assert jm._jobs["j1"]["progress"] == 0.5

    def test_update_message(self):
        jm = _fresh_job_manager()
        _seed_job(jm, "j1")
        jm.update_job("j1", message="Downloading page 5/10")
        assert jm._jobs["j1"]["message"] == "Downloading page 5/10"

    def test_update_nonexistent_is_noop(self):
        jm = _fresh_job_manager()
        jm.update_job("nonexistent", status="running")  # Should not raise


# --- list_jobs ---

class TestListJobs:
    def test_list_all(self):
        jm = _fresh_job_manager()
        _seed_job(jm, "j1", status="completed")
        _seed_job(jm, "j2", status="running")
        result = jm.list_jobs()
        assert "j1" in result
        assert "j2" in result

    def test_list_active_only(self):
        jm = _fresh_job_manager()
        _seed_job(jm, "j1", status="completed")
        _seed_job(jm, "j2", status="running")
        _seed_job(jm, "j3", status="queued")
        result = jm.list_jobs(active_only=True)
        assert "j1" not in result
        assert "j2" in result
        assert "j3" in result


# --- is_cancel_requested / is_stop_requested ---

class TestCancelStopFlags:
    def test_cancel_not_requested(self):
        jm = _fresh_job_manager()
        _seed_job(jm, "j1")
        assert jm.is_cancel_requested("j1") is False

    def test_cancel_requested(self):
        jm = _fresh_job_manager()
        _seed_job(jm, "j1", cancel_requested=True)
        assert jm.is_cancel_requested("j1") is True

    def test_stop_requested_on_cancel(self):
        jm = _fresh_job_manager()
        _seed_job(jm, "j1", cancel_requested=True)
        assert jm.is_stop_requested("j1") is True

    def test_stop_requested_on_pause(self):
        jm = _fresh_job_manager()
        _seed_job(jm, "j1", pause_requested=True)
        assert jm.is_stop_requested("j1") is True

    def test_stop_not_requested(self):
        jm = _fresh_job_manager()
        _seed_job(jm, "j1")
        assert jm.is_stop_requested("j1") is False

    def test_nonexistent_job_is_false(self):
        jm = _fresh_job_manager()
        assert jm.is_cancel_requested("x") is False
        assert jm.is_stop_requested("x") is False


# --- request_cancel ---

class TestRequestCancel:
    def test_cancel_direct_match(self):
        jm = _fresh_job_manager()
        _seed_job(jm, "j1", status="running")
        assert jm.request_cancel("j1") is True
        assert jm._jobs["j1"]["cancel_requested"] is True

    def test_cancel_by_db_job_id(self):
        jm = _fresh_job_manager()
        _seed_job(jm, "j1", db_job_id="ext-123")
        assert jm.request_cancel("ext-123") is True
        assert jm._jobs["j1"]["cancel_requested"] is True

    def test_cancel_queued_job_marks_cancelled(self):
        jm = _fresh_job_manager()
        jm._update_db_safe = MagicMock()
        jm._refresh_queue_positions_locked = MagicMock()
        _seed_job(jm, "j1", status="queued")
        jm._download_queue.append("j1")

        jm.request_cancel("j1")
        assert jm._jobs["j1"]["status"] == "cancelled"
        assert "j1" not in jm._download_queue

    def test_cancel_nonexistent_returns_false(self):
        jm = _fresh_job_manager()
        assert jm.request_cancel("nonexistent") is False


# --- _mark_running / _mark_success / _mark_stopped / _mark_failure ---

class TestMarkMethods:
    def test_mark_running(self):
        jm = _fresh_job_manager()
        jm._update_db_safe = MagicMock()
        _seed_job(jm, "j1", status="queued")
        jm._mark_running("j1", "download", "db1")
        assert jm._jobs["j1"]["status"] == "running"
        assert jm._jobs["j1"]["queue_position"] == 0
        jm._update_db_safe.assert_called_once()

    def test_mark_running_generic_no_db_call(self):
        jm = _fresh_job_manager()
        jm._update_db_safe = MagicMock()
        _seed_job(jm, "j1", status="pending", type="generic")
        jm._mark_running("j1", "generic", None)
        assert jm._jobs["j1"]["status"] == "running"
        jm._update_db_safe.assert_not_called()

    def test_mark_success(self):
        jm = _fresh_job_manager()
        jm._update_db_safe = MagicMock()
        _seed_job(jm, "j1", status="running")
        jm._mark_success("j1", "result_data", "download", "db1")
        assert jm._jobs["j1"]["status"] == "completed"
        assert jm._jobs["j1"]["progress"] == 1.0
        assert jm._jobs["j1"]["result"] == "result_data"

    def test_mark_stopped_paused(self):
        jm = _fresh_job_manager()
        jm._update_db_safe = MagicMock()
        jm._promote_staged_pages_on_pause = MagicMock()
        _seed_job(jm, "j1", pause_requested=True, cancel_requested=False)
        jm._mark_stopped("j1", "download", "db1")
        assert jm._jobs["j1"]["status"] == "paused"
        assert jm._jobs["j1"]["error"] is None

    def test_mark_stopped_cancelled(self):
        jm = _fresh_job_manager()
        jm._update_db_safe = MagicMock()
        _seed_job(jm, "j1", cancel_requested=True, pause_requested=True)
        jm._mark_stopped("j1", "download", "db1")
        assert jm._jobs["j1"]["status"] == "cancelled"

    def test_mark_failure(self):
        jm = _fresh_job_manager()
        jm._update_db_safe = MagicMock()
        _seed_job(jm, "j1")
        jm._mark_failure("j1", RuntimeError("oops"), "download", "db1")
        assert jm._jobs["j1"]["status"] == "failed"
        assert "oops" in jm._jobs["j1"]["error"]


# --- _is_within ---

class TestIsWithin:
    def test_within(self, tmp_path):
        child = tmp_path / "sub" / "file.txt"
        child.parent.mkdir(parents=True)
        child.touch()
        assert JobManager._is_within(child, tmp_path) is True

    def test_not_within(self, tmp_path):
        outside = Path("/etc/passwd")
        assert JobManager._is_within(outside, tmp_path) is False


# --- prioritize_download ---

class TestPrioritizeDownload:
    def test_prioritize_moves_to_front(self):
        jm = _fresh_job_manager()
        jm._refresh_queue_positions_locked = MagicMock()
        jm._dispatch_queued_downloads_locked = MagicMock()
        _seed_job(jm, "j1", status="queued")
        _seed_job(jm, "j2", status="queued")
        jm._download_queue.extend(["j1", "j2"])

        assert jm.prioritize_download("j2") is True
        assert list(jm._download_queue) == ["j2", "j1"]
        assert jm._jobs["j2"]["priority"] == 1

    def test_prioritize_nonexistent_returns_false(self):
        jm = _fresh_job_manager()
        assert jm.prioritize_download("x") is False

    def test_prioritize_not_in_queue_returns_false(self):
        jm = _fresh_job_manager()
        _seed_job(jm, "j1", status="running")
        assert jm.prioritize_download("j1") is False
