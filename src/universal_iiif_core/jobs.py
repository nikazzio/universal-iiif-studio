import threading
import time
import uuid
from collections import deque
from collections.abc import Callable
from typing import Any

from .config_manager import get_config_manager
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
    _download_queue: deque[str] = deque()
    _active_downloads: set[str] = set()

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

        self._register_pending_job(job_id, task_func, args, job_kwargs, job_type, db_job_id)
        try:
            if job_type == "download":
                self._maybe_create_db_record(job_id, db_job_id, job_kwargs)
        except Exception:
            logger.exception("Failed to record download job %s in vault DB", db_job_id or job_id)
        if job_type == "download":
            self._enqueue_download_job(job_id, db_job_id)
        else:
            self._start_job_thread(job_id)
        return job_id

    def _register_pending_job(
        self,
        job_id: str,
        task_func: Callable,
        args: tuple,
        kwargs: dict[str, Any],
        job_type: str,
        db_job_id: str | None,
    ) -> None:
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "type": job_type,
                "status": "queued" if job_type == "download" else "pending",
                "progress": 0.0,
                "message": "Queued..." if job_type == "download" else "Initializing...",
                "result": None,
                "error": None,
                "created_at": time.time(),
                "cancel_requested": False,
                "pause_requested": False,
                "db_job_id": db_job_id,
                "task_func": task_func,
                "args": args,
                "kwargs": kwargs,
                "thread": None,
            }

    def _start_job_thread(self, job_id: str, *, locked: bool = False) -> bool:
        if locked:
            info = self._jobs.get(job_id)
            if not info:
                return False
            if info.get("thread") is not None:
                return False
            thread = threading.Thread(
                target=self._worker_wrapper,
                args=(
                    job_id,
                    info.get("task_func"),
                    tuple(info.get("args") or ()),
                    dict(info.get("kwargs") or {}),
                    str(info.get("type") or "generic"),
                    info.get("db_job_id"),
                ),
                daemon=True,
            )
            info["thread"] = thread
        else:
            with self._lock:
                info = self._jobs.get(job_id)
                if not info:
                    return False
                if info.get("thread") is not None:
                    return False
                thread = threading.Thread(
                    target=self._worker_wrapper,
                    args=(
                        job_id,
                        info.get("task_func"),
                        tuple(info.get("args") or ()),
                        dict(info.get("kwargs") or {}),
                        str(info.get("type") or "generic"),
                        info.get("db_job_id"),
                    ),
                    daemon=True,
                )
                info["thread"] = thread
        thread.start()
        return True

    def _enqueue_download_job(self, job_id: str, db_job_id: str | None) -> None:
        try:
            self._update_db_safe(
                db_job_id or job_id,
                status="queued",
                current=0,
                total=0,
            )
        except Exception:
            logger.debug("Failed to mark queued for %s", db_job_id or job_id, exc_info=True)
        with self._lock:
            self._download_queue.append(job_id)
            self._refresh_queue_positions_locked()
            self._dispatch_queued_downloads_locked()

    def _max_concurrent_downloads(self) -> int:
        try:
            cm = get_config_manager()
            configured = int(cm.get_setting("system.max_concurrent_downloads", 2) or 2)
            return max(1, min(configured, 8))
        except Exception:
            return 2

    def _dispatch_queued_downloads_locked(self) -> None:
        max_jobs = self._max_concurrent_downloads()
        while len(self._active_downloads) < max_jobs and self._download_queue:
            next_job = self._download_queue.popleft()
            info = self._jobs.get(next_job)
            if not info:
                continue
            if info.get("cancel_requested"):
                if info.get("pause_requested"):
                    info["status"] = "paused"
                    info["message"] = "Paused by user"
                else:
                    info["status"] = "cancelled"
                    info["message"] = "Cancelled before start"
                continue
            self._active_downloads.add(next_job)
            info["message"] = "Starting..."
            self._start_job_thread(next_job, locked=True)
        self._refresh_queue_positions_locked()

    def _refresh_queue_positions_locked(self) -> None:
        queue_ids = list(self._download_queue)
        for idx, job_id in enumerate(queue_ids, start=1):
            info = self._jobs.get(job_id) or {}
            info["queue_position"] = idx
            db_job_id = info.get("db_job_id") or job_id
            try:
                VaultManager().update_download_job(
                    db_job_id,
                    current=0,
                    total=0,
                    status="queued",
                    queue_position=idx,
                    priority=int(info.get("priority") or 0),
                )
            except Exception:
                logger.debug("Failed queue position update for %s", db_job_id, exc_info=True)

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
            if self.is_cancel_requested(job_id):
                self._mark_cancelled(job_id, job_type, db_job_id)
            else:
                self._mark_success(job_id, result, job_type, db_job_id)
                completed_successfully = True
        except Exception as exc:
            self._mark_failure(job_id, exc, job_type, db_job_id)
        finally:
            self._finalize_incomplete_download(job_id, job_type, db_job_id, completed_successfully)
            self._on_worker_finished(job_id, job_type)

    def _on_worker_finished(self, job_id: str, job_type: str) -> None:
        if job_type != "download":
            return
        with self._lock:
            self._active_downloads.discard(job_id)
            self._dispatch_queued_downloads_locked()

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
            self._jobs[job_id]["queue_position"] = 0

        if job_type != "download":
            return
        try:
            self._update_db_safe(db_job_id or job_id, status="running")
            VaultManager().update_download_job(db_job_id or job_id, 0, 0, status="running", queue_position=0)
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

    def _mark_cancelled(self, job_id: str, job_type: str, db_job_id: str | None) -> None:
        with self._lock:
            paused = bool(self._jobs.get(job_id, {}).get("pause_requested"))

        target_status = "paused" if paused else "cancelled"
        target_message = "Paused by user" if paused else "Cancelled by user"
        if job_type == "download":
            try:
                self._update_db_safe(db_job_id or job_id, status=target_status, error=target_message)
            except Exception:
                logger.debug("Failed to mark %s in vault DB: %s", target_status, db_job_id or job_id, exc_info=True)
        with self._lock:
            self._jobs[job_id]["status"] = target_status
            self._jobs[job_id]["message"] = target_message
            self._jobs[job_id]["error"] = target_message

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
            existing = VaultManager().get_download_job(db_job_id or job_id) or {}
            curr = int(existing.get("current", 0) or 0)
            total = int(existing.get("total", 0) or 0)
            if bool(snapshot.get("pause_requested") or snapshot.get("status") == "paused"):
                self._update_db_safe(
                    db_job_id or job_id,
                    status="paused",
                    error="Paused by user",
                    current=curr,
                    total=total,
                )
                return

            cancelled = bool(snapshot.get("cancel_requested") or snapshot.get("status") == "cancelled")
            if cancelled:
                self._update_db_safe(
                    db_job_id or job_id,
                    status="cancelled",
                    error="Cancelled by user",
                    current=curr,
                    total=total,
                )
                return
            final_error = snapshot.get("message")
            self._update_db_safe(
                db_job_id or job_id,
                status="error",
                error=final_error,
                current=curr,
                total=total,
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
        - Otherwise we preserve existing progress when current/total are omitted.
        """
        try:
            vm = VaultManager()
            if status == "completed":
                existing = vm.get_download_job(db_job_id) or {}
                curr = int(existing.get("current", 0) or 0)
                total_val = int(existing.get("total", 0) or 0)
                vm.update_download_job(db_job_id, current=curr, total=total_val, status="completed", error=None)
            else:
                existing = vm.get_download_job(db_job_id) or {}
                existing_current = int(existing.get("current", 0) or 0)
                existing_total = int(existing.get("total", existing_current) or existing_current)
                c = existing_current if current is None else int(current)
                t = existing_total if total is None else int(total)
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
        to_mark_cancelled: list[str] = []
        found = False
        with self._lock:
            # Direct match
            if id_or_db_id in self._jobs:
                self._jobs[id_or_db_id]["cancel_requested"] = True
                found = True
                if id_or_db_id in self._download_queue:
                    self._download_queue.remove(id_or_db_id)
                    self._jobs[id_or_db_id]["status"] = "cancelled"
                    self._jobs[id_or_db_id]["message"] = "Cancelled before start"
                    self._refresh_queue_positions_locked()
                    to_mark_cancelled.append(self._jobs[id_or_db_id].get("db_job_id") or id_or_db_id)
            # Search by db_job_id
            if not found:
                for jid, info in self._jobs.items():
                    if info.get("db_job_id") != id_or_db_id:
                        continue
                    info["cancel_requested"] = True
                    found = True
                    if jid in self._download_queue:
                        self._download_queue.remove(jid)
                        info["status"] = "cancelled"
                        info["message"] = "Cancelled before start"
                        self._refresh_queue_positions_locked()
                        to_mark_cancelled.append(info.get("db_job_id") or jid)
        for db_id in to_mark_cancelled:
            try:
                self._update_db_safe(db_id, status="cancelled", error="Cancelled by user")
            except Exception:
                logger.debug("Failed to mark queued job cancelled: %s", db_id, exc_info=True)
        return found

    def _target_job_ids_locked(self, id_or_db_id: str) -> list[str]:
        if id_or_db_id in self._jobs:
            return [id_or_db_id]
        for jid, info in self._jobs.items():
            if info.get("db_job_id") == id_or_db_id:
                return [jid]
        return []

    def _pause_queued_job_locked(self, jid: str, info: dict[str, Any], db_id: str, to_mark_paused: list[str]) -> None:
        self._download_queue.remove(jid)
        info["status"] = "paused"
        info["message"] = "Paused by user"
        info["error"] = "Paused by user"
        to_mark_paused.append(db_id)
        self._refresh_queue_positions_locked()

    @staticmethod
    def _pause_snapshot_locked(
        info: dict[str, Any],
        db_id: str,
        to_mark_cancelling: list[str],
        to_mark_paused: list[str],
    ) -> None:
        if info.get("status") == "running":
            info["status"] = "cancelling"
            info["message"] = "Pausing..."
            to_mark_cancelling.append(db_id)
        elif info.get("status") == "queued":
            info["status"] = "paused"
            info["message"] = "Paused by user"
            info["error"] = "Paused by user"
            to_mark_paused.append(db_id)

    @staticmethod
    def _apply_pause_status_updates(
        to_mark_cancelling: list[str],
        to_mark_paused: list[str],
        update_db_safe: Callable[..., None],
    ) -> None:
        for db_id in to_mark_cancelling:
            try:
                update_db_safe(db_id, status="cancelling", error="Pausing")
            except Exception:
                logger.debug("Failed to mark job cancelling while pausing: %s", db_id, exc_info=True)
        for db_id in to_mark_paused:
            try:
                update_db_safe(db_id, status="paused", error="Paused by user")
            except Exception:
                logger.debug("Failed to mark job paused: %s", db_id, exc_info=True)

    def request_pause(self, id_or_db_id: str) -> bool:
        """Request pause for a job by either job_id or external db_job_id."""
        to_mark_paused: list[str] = []
        to_mark_cancelling: list[str] = []

        with self._lock:
            target_job_ids = self._target_job_ids_locked(id_or_db_id)
            for jid in target_job_ids:
                info = self._jobs.get(jid)
                if not info:
                    continue
                db_id = info.get("db_job_id") or jid
                info["pause_requested"] = True
                info["cancel_requested"] = True

                if jid in self._download_queue:
                    self._pause_queued_job_locked(jid, info, db_id, to_mark_paused)
                else:
                    self._pause_snapshot_locked(info, db_id, to_mark_cancelling, to_mark_paused)

        self._apply_pause_status_updates(to_mark_cancelling, to_mark_paused, self._update_db_safe)
        return bool(to_mark_cancelling or to_mark_paused)

    def prioritize_download(self, id_or_db_id: str) -> bool:
        """Move a queued download to the front of the queue."""
        with self._lock:
            target_job_id = None
            if id_or_db_id in self._jobs:
                target_job_id = id_or_db_id
            else:
                for jid, info in self._jobs.items():
                    if info.get("db_job_id") == id_or_db_id:
                        target_job_id = jid
                        break
            if not target_job_id or target_job_id not in self._download_queue:
                return False
            self._download_queue.remove(target_job_id)
            self._download_queue.appendleft(target_job_id)
            self._jobs[target_job_id]["priority"] = int(self._jobs[target_job_id].get("priority") or 0) + 1
            self._refresh_queue_positions_locked()
            self._dispatch_queued_downloads_locked()
            return True

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
                return {k: v for k, v in self._jobs.items() if v["status"] in ["pending", "queued", "running"]}
            return self._jobs.copy()


# Global Instance
job_manager = JobManager()
