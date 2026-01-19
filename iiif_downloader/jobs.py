import logging
import threading
import time
import uuid
from typing import Any, Callable, Dict, Optional

from iiif_downloader.logger import get_logger

logger = get_logger(__name__)

# This module intentionally shields the UI from unexpected job exceptions.
# pylint: disable=broad-exception-caught


class JobManager:
    _instance = None
    _jobs: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JobManager, cls).__new__(cls)
        return cls._instance

    def submit_job(
        self, task_func: Callable, args=(), kwargs=None, job_type="generic"
    ) -> str:
        """
        Submits a task to run in a background thread.
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
            }

        def worker_wrapper():
            try:
                # Progress callback injector
                def update_progress(current, total, msg=None):
                    self.update_job(
                        job_id,
                        progress=current / total,
                        message=msg or f"Processing {current}/{total}",
                    )

                # Inject progress callback if the function accepts it
                # We assume task_func can accept 'progress_callback' kwarg
                if "progress_callback" not in kwargs:
                    kwargs["progress_callback"] = update_progress

                with self._lock:
                    self._jobs[job_id]["status"] = "running"

                result = task_func(*args, **kwargs)

                with self._lock:
                    self._jobs[job_id]["status"] = "completed"
                    self._jobs[job_id]["progress"] = 1.0
                    self._jobs[job_id]["message"] = "Done"
                    self._jobs[job_id]["result"] = result

            except Exception as e:
                logger.exception("Job %s failed", job_id)
                with self._lock:
                    self._jobs[job_id]["status"] = "failed"
                    self._jobs[job_id]["error"] = str(e)
                    self._jobs[job_id]["message"] = f"Error: {e}"

        thread = threading.Thread(target=worker_wrapper, daemon=True)
        thread.start()

        return job_id

    def get_job(self, job_id: str) -> Optional[Dict]:
        with self._lock:
            return self._jobs.get(job_id)

    def update_job(self, job_id: str, status=None, progress=None, message=None):
        with self._lock:
            if job_id in self._jobs:
                if status:
                    self._jobs[job_id]["status"] = status
                if progress is not None:
                    self._jobs[job_id]["progress"] = progress
                if message:
                    self._jobs[job_id]["message"] = message

    def list_jobs(self, active_only=False):
        with self._lock:
            if active_only:
                return {
                    k: v
                    for k, v in self._jobs.items()
                    if v["status"] in ["pending", "running"]
                }
            return self._jobs.copy()


# Global Instance
job_manager = JobManager()
