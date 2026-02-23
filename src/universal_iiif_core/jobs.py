import threading
import time
import uuid
from collections.abc import Callable
from typing import Any

from .logger import get_logger
from .services.storage.vault_manager import VaultManager

logger = get_logger(__name__)

# This module intentionally shields the UI from unexpected job exceptions.
# pylint: disable=broad-exception-caught


class JobManager:
    """Singleton manager for background jobs."""

    _instance = None
    _jobs: dict[str, dict[str, Any]] = {}
    _lock = threading.Lock()

    def __new__(cls):
        """Ensure only one JobManager instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def submit_job(self, task_func: Callable, args=(), kwargs=None, job_type="generic") -> str:
        """Submits a task to run in a background thread.

        Returns the job_id.
        """
        job_kwargs = dict(kwargs or {})
        job_id = str(uuid.uuid4())[:8]
        db_job_id = job_kwargs.get("db_job_id")

        self._register_pending_job(job_id, job_type, db_job_id)
        try:
            if job_type == "download":
                self._maybe_create_db_record(job_id, db_job_id, job_kwargs)
        except Exception:
            logger.exception("Failed to record download job %s in vault DB", db_job_id or job_id)

        thread = threading.Thread(
            target=self._worker_wrapper,
            args=(job_id, task_func, args, job_kwargs, job_type, db_job_id),
            daemon=True,
        )
        thread.start()

        return job_id

    def _register_pending_job(self, job_id: str, job_type: str, db_job_id: str | None) -> None:
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "type": job_type,
                "status": "pending",
                "progress": 0.0,
                "message": "Initializing...",
                "result": None,
                "error": None,
                "created_at": time.time(),
                "cancel_requested": False,
                "db_job_id": db_job_id,
            }

    def _worker_wrapper(
        self,
        job_id: str,
        task_func: Callable,
        args: tuple,
        job_kwargs: dict[str, Any],
        job_type: str,
        db_job_id: str | None,
    ) -> None:
        completed_successfully = False
        self._inject_worker_callbacks(job_id, job_kwargs, job_type, db_job_id)
        self._mark_running(job_id, job_type, db_job_id)

        try:
            result = task_func(*args, **job_kwargs)
            self._mark_success(job_id, result, job_type, db_job_id)
            completed_successfully = True
        except Exception as exc:
            self._mark_failure(job_id, exc, job_type, db_job_id)
        finally:
            self._finalize_incomplete_download(job_id, job_type, db_job_id, completed_successfully)

    def _inject_worker_callbacks(
        self,
        job_id: str,
        job_kwargs: dict[str, Any],
        job_type: str,
        db_job_id: str | None,
    ) -> None:
        if "progress_callback" not in job_kwargs:
            job_kwargs["progress_callback"] = self._build_progress_callback(job_id, job_type, db_job_id)
        if "should_cancel" not in job_kwargs:
            job_kwargs["should_cancel"] = lambda: self.is_cancel_requested(job_id)

    def _build_progress_callback(self, job_id: str, job_type: str, db_job_id: str | None) -> Callable:
        def update_progress(current, total, msg=None):
            try:
                self.update_job(
                    job_id,
                    progress=current / total,
                    message=msg or f"Processing {current}/{total}",
                )
            except Exception:
                logger.debug("Failed to update in-memory job progress for %s", job_id, exc_info=True)

            if job_type != "download":
                return
            try:
                self._update_db_safe(db_job_id or job_id, status="running", current=current, total=total)
            except Exception:
                logger.debug("Failed to update vault DB progress for %s", db_job_id or job_id, exc_info=True)

        return update_progress

    def _mark_running(self, job_id: str, job_type: str, db_job_id: str | None) -> None:
        with self._lock:
            self._jobs[job_id]["status"] = "running"

        if job_type != "download":
            return
        try:
            self._update_db_safe(db_job_id or job_id, status="running")
        except Exception:
            logger.debug("_update_db_safe failed to mark running for %s", db_job_id or job_id, exc_info=True)

    def _mark_success(self, job_id: str, result: Any, job_type: str, db_job_id: str | None) -> None:
        if job_type == "download":
            try:
                self._update_db_safe(db_job_id or job_id, status="completed")
            except Exception:
                logger.exception("Failed to mark job completed in vault DB: %s", db_job_id or job_id)

        with self._lock:
            self._jobs[job_id]["status"] = "completed"
            self._jobs[job_id]["progress"] = 1.0
            self._jobs[job_id]["message"] = "Done"
            self._jobs[job_id]["result"] = result

    def _mark_failure(self, job_id: str, exc: Exception, job_type: str, db_job_id: str | None) -> None:
        logger.exception("Job %s failed", job_id)
        error_text = str(exc)
        message_text = f"Error: {exc}"

        if job_type == "download":
            try:
                # Keep DB state synchronized before exposing final in-memory status.
                self._update_db_safe(db_job_id or job_id, status="error", error=error_text)
            except Exception:
                logger.exception("Failed to write failure to vault DB for %s", db_job_id or job_id)

        with self._lock:
            self._jobs[job_id]["status"] = "failed"
            self._jobs[job_id]["error"] = error_text
            self._jobs[job_id]["message"] = message_text

    def _finalize_incomplete_download(
        self,
        job_id: str,
        job_type: str,
        db_job_id: str | None,
        completed_successfully: bool,
    ) -> None:
        if job_type != "download" or completed_successfully:
            return

        try:
            snapshot = self.get_job(job_id) or {}
            final_error = "Cancelled by user" if snapshot.get("cancel_requested") else snapshot.get("message")
            self._update_db_safe(
                db_job_id or job_id,
                status="error",
                error=final_error,
                current=snapshot.get("progress", 0),
            )
        except Exception:
            logger.exception("Failed to write final state for %s", db_job_id or job_id)

    # --- DB helper methods to keep complexity low ---
    def _maybe_create_db_record(self, job_id: str, db_job_id: str | None, kwargs: dict | Any) -> None:
        try:
            vault = VaultManager()
            doc_id = str(kwargs.get("doc_id") or "-") if isinstance(kwargs, dict) else "-"
            library = str(kwargs.get("library") or "-") if isinstance(kwargs, dict) else "-"
            manifest_url = str(kwargs.get("manifest_url") or "") if isinstance(kwargs, dict) else ""
            target = db_job_id or job_id
            vault.create_download_job(target, doc_id, library, manifest_url)
        except Exception:
            logger.debug("_maybe_create_db_record failed for %s", db_job_id or job_id, exc_info=True)

    def _mark_db_running(self, db_job_id: str) -> None:
        try:
            VaultManager().update_download_job(db_job_id, 0, 0, status="running")
        except Exception:
            logger.debug("_mark_db_running failed for %s", db_job_id, exc_info=True)

    def _update_db_progress(self, db_job_id: str, current: int, total: int) -> None:
        try:
            VaultManager().update_download_job(db_job_id, current=current, total=total, status="running")
        except Exception:
            logger.debug("_update_db_progress failed for %s", db_job_id, exc_info=True)

    def _update_db_safe(
        self,
        db_job_id: str,
        status: str | None = None,
        current: int | None = None,
        total: int | None = None,
        error: str | None = None,
    ) -> None:
        """Safely update the Vault DB for a job, swallowing exceptions.

        - If status == 'completed' we attempt to preserve existing totals.
        - Otherwise we write the provided current/total/status/error.
        """
        try:
            vm = VaultManager()
            if status == "completed":
                existing = vm.get_download_job(db_job_id) or {}
                curr = int(existing.get("current", 0) or 0)
                total_val = int(existing.get("total", 0) or 0)
                vm.update_download_job(db_job_id, current=curr, total=total_val, status="completed", error=None)
            else:
                c = int(current or 0)
                t = int(total if total is not None else c)
                vm.update_download_job(db_job_id, current=c, total=t, status=(status or "running"), error=error)
        except Exception:
            logger.debug("_update_db_safe failed for %s", db_job_id, exc_info=True)

    def _mark_db_completed(self, db_job_id: str) -> None:
        try:
            vm = VaultManager()
            existing = vm.get_download_job(db_job_id) or {}
            curr = int(existing.get("current", 0) or 0)
            total = int(existing.get("total", 0) or 0)
            # If totals unknown, default to 0/0
            vm.update_download_job(db_job_id, current=curr, total=total, status="completed", error=None)
        except Exception:
            logger.debug("_mark_db_completed failed for %s", db_job_id, exc_info=True)

    def _mark_db_error(self, db_job_id: str, error: str | None = None, progress: int | None = None) -> None:
        try:
            curr = progress or 0
            VaultManager().update_download_job(db_job_id, current=curr, total=curr, status="error", error=error)
        except Exception:
            logger.debug("_mark_db_error failed for %s", db_job_id, exc_info=True)

    def request_cancel(self, id_or_db_id: str) -> bool:
        """Request cancellation for a job by either job_id or external db_job_id.

        Returns True if a matching job was found and cancel requested.
        """
        with self._lock:
            # Direct match
            if id_or_db_id in self._jobs:
                self._jobs[id_or_db_id]["cancel_requested"] = True
                return True
            # Search by db_job_id
            for _, info in self._jobs.items():
                if info.get("db_job_id") == id_or_db_id:
                    info["cancel_requested"] = True
                    return True
        return False

    def is_cancel_requested(self, job_id: str) -> bool:
        """Check if cancellation has been requested for a given job_id."""
        with self._lock:
            return bool(self._jobs.get(job_id, {}).get("cancel_requested"))

    def get_job(self, job_id: str) -> dict | None:
        """Return stored info for a given job_id."""
        with self._lock:
            return self._jobs.get(job_id)

    def update_job(self, job_id: str, status=None, progress=None, message=None):
        """Update one of the tracked job fields."""
        with self._lock:
            if job_id in self._jobs:
                if status:
                    self._jobs[job_id]["status"] = status
                if progress is not None:
                    self._jobs[job_id]["progress"] = progress
                if message:
                    self._jobs[job_id]["message"] = message

    def list_jobs(self, active_only=False):
        """List all tracked jobs, optionally filtering to active work."""
        with self._lock:
            if active_only:
                return {k: v for k, v in self._jobs.items() if v["status"] in ["pending", "running"]}
            return self._jobs.copy()


# Global Instance
job_manager = JobManager()
