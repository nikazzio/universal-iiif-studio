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
        if kwargs is None:
            kwargs = {}

        job_id = str(uuid.uuid4())[:8]

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
                # optional mapping to external DB job id
                "db_job_id": kwargs.get("db_job_id") if isinstance(kwargs, dict) else None,
            }

        # Persist DB record for downloads (stable id may be provided via kwargs)
        db_job_id = kwargs.get("db_job_id") if isinstance(kwargs, dict) else None
        try:
            if job_type == "download":
                # Delegate to helper to keep this function concise
                self._maybe_create_db_record(job_id, db_job_id, kwargs)
        except Exception:
            logger.exception("Failed to record download job %s in vault DB", db_job_id or job_id)

        def worker_wrapper():
            # Ensure we mark job state in DB and in-memory reliably even on crash
            completed_successfully = False

            # Progress callback injector
            def update_progress(current, total, msg=None):
                try:
                    self.update_job(
                        job_id,
                        progress=current / total,
                        message=msg or f"Processing {current}/{total}",
                    )
                except Exception:
                    logger.debug("Failed to update in-memory job progress for %s", job_id, exc_info=True)

                # Update DB progress if available
                try:
                    if job_type == "download":
                        self._update_db_safe(db_job_id or job_id, status="running", current=current, total=total)
                except Exception:
                    logger.debug("Failed to update vault DB progress for %s", db_job_id or job_id, exc_info=True)

            # Inject progress callback if the function accepts it
            # We assume task_func can accept 'progress_callback' kwarg
            if "progress_callback" not in kwargs:
                kwargs["progress_callback"] = update_progress

            # Inject a cancel-check callable so task can cooperatively stop
            def _cancel_check():
                with self._lock:
                    return bool(self._jobs.get(job_id, {}).get("cancel_requested"))

            if "should_cancel" not in kwargs:
                kwargs["should_cancel"] = _cancel_check

            # Mark running in-memory and in DB
            with self._lock:
                self._jobs[job_id]["status"] = "running"

            if job_type == "download":
                try:
                    self._update_db_safe(db_job_id or job_id, status="running")
                except Exception:
                    logger.debug("_update_db_safe failed to mark running for %s", db_job_id or job_id, exc_info=True)

            try:
                result = task_func(*args, **kwargs)

                # mark DB completed first so UI polling sees DB final state
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

                completed_successfully = True

            except Exception as e:
                logger.exception("Job %s failed", job_id)
                with self._lock:
                    self._jobs[job_id]["status"] = "failed"
                    self._jobs[job_id]["error"] = str(e)
                    self._jobs[job_id]["message"] = f"Error: {e}"

                try:
                    if job_type == "download":
                        self._update_db_safe(db_job_id or job_id, status="error", error=str(e))
                except Exception:
                    logger.exception("Failed to write failure to vault DB for %s", db_job_id or job_id)

            finally:
                # If the thread died without marking completed, ensure DB shows failure
                try:
                    if job_type == "download" and not completed_successfully:
                        # If cancellation was requested, mark cancelled, else error
                        with self._lock:
                            cancel = bool(self._jobs.get(job_id, {}).get("cancel_requested"))
                        final_error = self._jobs.get(job_id, {}).get("message")
                        if cancel:
                            final_error = "Cancelled by user"
                        try:
                            self._update_db_safe(
                                db_job_id or job_id,
                                status="error",
                                error=final_error,
                                current=self._jobs.get(job_id, {}).get("progress", 0),
                            )
                        except Exception:
                            logger.exception("Failed to write final state for %s", db_job_id or job_id)
                except Exception:
                    logger.exception("Failed to perform finally DB update for job %s", job_id)

        thread = threading.Thread(target=worker_wrapper, daemon=True)
        thread.start()

        return job_id

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
