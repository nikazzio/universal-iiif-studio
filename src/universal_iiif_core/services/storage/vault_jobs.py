"""Download/export job and cleanup methods for VaultManager."""

from __future__ import annotations

import sqlite3
from typing import Any

from ...exceptions import DatabaseError
from ...logger import get_logger

logger = get_logger(__name__)


def create_download_job(self, job_id: str, doc_id: str, library: str, manifest_url: str):
    """Crea traccia del download nel DB."""
    conn = self._get_conn()
    try:
        cursor = conn.cursor()
        # Creiamo la tabella al volo se non esiste (safety check)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS download_jobs (
                job_id TEXT PRIMARY KEY, doc_id TEXT, library TEXT,
                manifest_url TEXT, status TEXT, current_page INTEGER,
                total_pages INTEGER, queue_position INTEGER DEFAULT 0,
                priority INTEGER DEFAULT 0, error_message TEXT, started_at TIMESTAMP,
                finished_at TIMESTAMP, updated_at TIMESTAMP
            )
        """)
        cursor.execute(
            """
            INSERT OR REPLACE INTO download_jobs (
                job_id, doc_id, library, manifest_url, status,
                current_page, total_pages, queue_position, priority, started_at, finished_at, updated_at
            )
            VALUES (?, ?, ?, ?, 'queued', 0, 0, 0, 0, NULL, NULL, CURRENT_TIMESTAMP)
        """,
            (job_id, doc_id, library, manifest_url),
        )
        conn.commit()
    finally:
        conn.close()


def update_download_job(
    self,
    job_id: str,
    current: int,
    total: int,
    status: str = "running",
    error: str | None = None,
    queue_position: int | None = None,
    priority: int | None = None,
):
    """Aggiorna lo stato."""
    conn = self._get_conn()
    try:
        cursor = conn.cursor()
        updates = [
            "current_page = ?",
            "total_pages = ?",
            "status = ?",
            "error_message = ?",
            "updated_at = CURRENT_TIMESTAMP",
        ]
        params: list[Any] = [current, total, status, error]
        if queue_position is not None:
            updates.append("queue_position = ?")
            params.append(int(queue_position))
        if priority is not None:
            updates.append("priority = ?")
            params.append(int(priority))
        if status == "running":
            updates.append("started_at = COALESCE(started_at, CURRENT_TIMESTAMP)")
            updates.append("finished_at = NULL")
        if status in {"completed", "error", "cancelled", "paused"}:
            updates.append("finished_at = CURRENT_TIMESTAMP")
        sql = f"UPDATE download_jobs SET {', '.join(updates)} WHERE job_id = ?"  # noqa: S608
        params.append(job_id)
        cursor.execute(sql, tuple(params))
        progress_key = (current, total, status)
        cached = self._download_progress_cache.get(job_id)
        if cached != progress_key:
            try:
                cursor.execute("SELECT doc_id FROM download_jobs WHERE job_id = ?", (job_id,))
                row = cursor.fetchone()
                doc_id = row[0] if row else None
                title = None
                if doc_id:
                    try:
                        ms = self.get_manuscript(doc_id)
                        title = ms.get("title") if ms else None
                    except DatabaseError:
                        title = None

                log_message = "Download update: job=%s doc=%s title=%s %s/%s status=%s"
                log_args = (job_id, doc_id or "-", title or "-", current, total, status)
                if status in {"completed", "error", "cancelled", "cancelling", "paused"}:
                    logger.info(log_message, *log_args)
                else:
                    logger.debug(log_message, *log_args)
            except DatabaseError:
                logger.debug("Failed to log download update for job %s", job_id, exc_info=True)
            finally:
                self._download_progress_cache[job_id] = progress_key
        conn.commit()
    finally:
        conn.close()


def get_active_download(self):
    """Trova un download attivo."""
    conn = self._get_conn()
    cursor = conn.cursor()
    # Controlla se la tabella esiste prima di fare select
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='download_jobs'")
    if not cursor.fetchone():
        return None

    cursor.execute("""
        SELECT job_id, doc_id, library, status, current_page, total_pages, error_message
        FROM download_jobs
        WHERE status IN ('running', 'queued')
        ORDER BY priority DESC, queue_position ASC, updated_at DESC LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        return {
            "job_id": row[0],
            "doc_id": row[1],
            "library": row[2],
            "status": row[3],
            "current": row[4],
            "total": row[5],
            "error": row[6],
        }
    return None


def get_active_downloads(self):
    """Return a list of active (pending/running) download jobs ordered by recent update.

    This is used by the UI to render all concurrent downloads.
    """
    conn = self._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='download_jobs'")
    if not cursor.fetchone():
        return []

    cursor.execute(
        """
        SELECT job_id, doc_id, library, status, current_page, total_pages, error_message, queue_position, priority
        FROM download_jobs
        WHERE status IN ('running', 'queued', 'cancelling')
        ORDER BY CASE
            WHEN status = 'running' THEN 0
            WHEN status = 'cancelling' THEN 1
            ELSE 2
        END, priority DESC, queue_position ASC, updated_at DESC
    """
    )
    rows = cursor.fetchall()
    conn.close()
    results = []
    for row in rows:
        results.append(
            {
                "job_id": row[0],
                "doc_id": row[1],
                "library": row[2],
                "status": row[3],
                "current": row[4],
                "total": row[5],
                "error": row[6],
                "queue_position": row[7],
                "priority": row[8],
            }
        )
    return results


def get_download_job(self, job_id: str):
    """Return a specific download job by its job_id, or None if not found."""
    conn = self._get_conn()
    conn.row_factory = None
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='download_jobs'")
    if not cursor.fetchone():
        return None
    cursor.execute(
        """
        SELECT job_id, doc_id, library, manifest_url, status, current_page, total_pages,
               error_message, queue_position, priority
        FROM download_jobs
        WHERE job_id = ?
    """,
        (job_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "job_id": row[0],
        "doc_id": row[1],
        "library": row[2],
        "manifest_url": row[3],
        "status": row[4],
        "current": row[5],
        "total": row[6],
        "error": row[7],
        "queue_position": row[8],
        "priority": row[9],
    }


def list_download_jobs(self, limit: int = 50):
    """List recent download jobs with queue metadata."""
    conn = self._get_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT dj.job_id, dj.doc_id, dj.library, dj.manifest_url, dj.status,
                   current_page AS current, total_pages AS total,
                   dj.queue_position, dj.priority, dj.error_message AS error,
                   dj.updated_at, dj.created_at, dj.started_at, dj.finished_at,
                   m.display_title, m.catalog_title, m.shelfmark
            FROM download_jobs dj
            LEFT JOIN manuscripts m
                ON m.id = dj.doc_id AND COALESCE(m.library, '') = COALESCE(dj.library, '')
            WHERE NOT (
                dj.status IN ('completed', 'error', 'cancelled', 'paused')
                AND m.id IS NULL
            )
            ORDER BY
                CASE
                    WHEN dj.status = 'running' THEN 0
                    WHEN dj.status = 'queued' THEN 1
                    WHEN dj.status = 'cancelling' THEN 2
                    WHEN dj.status = 'paused' THEN 3
                    WHEN dj.status = 'error' THEN 4
                    ELSE 5
                END,
                dj.priority DESC,
                dj.queue_position ASC,
                dj.updated_at DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def delete_download_job(self, job_id: str) -> bool:
    """Delete one download job row by id."""
    conn = self._get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM download_jobs WHERE job_id = ?", (job_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()


def create_export_job(
    self,
    job_id: str,
    *,
    scope_type: str,
    doc_ids_json: str,
    library: str,
    export_format: str,
    output_kind: str,
    selection_mode: str,
    selected_pages_json: str,
    destination: str,
    destination_payload_json: str = "{}",
    capability_flags_json: str = "{}",
    total_steps: int = 0,
) -> None:
    """Create or replace one export job row."""
    conn = self._get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO export_jobs (
                job_id, scope_type, doc_ids_json, library, export_format, output_kind,
                selection_mode, selected_pages_json, destination, destination_payload_json,
                capability_flags_json, status, current_step, total_steps, output_path, error_message,
                started_at, finished_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', 0, ?, NULL, NULL, NULL, NULL,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                job_id,
                scope_type,
                doc_ids_json,
                library,
                export_format,
                output_kind,
                selection_mode,
                selected_pages_json,
                destination,
                destination_payload_json,
                capability_flags_json,
                int(total_steps),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_export_job(
    self,
    job_id: str,
    *,
    current_step: int | None = None,
    total_steps: int | None = None,
    status: str | None = None,
    output_path: str | None = None,
    error_message: str | None = None,
) -> None:
    """Update one export job row with optional fields."""
    updates: list[str] = ["updated_at = CURRENT_TIMESTAMP"]
    params: list[Any] = []

    if current_step is not None:
        updates.append("current_step = ?")
        params.append(int(current_step))
    if total_steps is not None:
        updates.append("total_steps = ?")
        params.append(int(total_steps))
    if status is not None:
        updates.append("status = ?")
        params.append(status)
        if status == "running":
            updates.append("started_at = COALESCE(started_at, CURRENT_TIMESTAMP)")
            updates.append("finished_at = NULL")
        if status in {"completed", "error", "cancelled"}:
            updates.append("finished_at = CURRENT_TIMESTAMP")
    if output_path is not None:
        updates.append("output_path = ?")
        params.append(output_path)
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)

    conn = self._get_conn()
    try:
        cursor = conn.cursor()
        sql = f"UPDATE export_jobs SET {', '.join(updates)} WHERE job_id = ?"  # noqa: S608
        params.append(job_id)
        cursor.execute(sql, tuple(params))
        conn.commit()
    finally:
        conn.close()


def get_export_job(self, job_id: str) -> dict[str, Any] | None:
    """Return one export job by id."""
    conn = self._get_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='export_jobs'")
        if not cursor.fetchone():
            return None
        cursor.execute("SELECT * FROM export_jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_export_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
    """List recent export jobs ordered by status and recency."""
    conn = self._get_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='export_jobs'")
        if not cursor.fetchone():
            return []
        cursor.execute(
            """
            SELECT *
            FROM export_jobs
            ORDER BY
                CASE
                    WHEN status = 'running' THEN 0
                    WHEN status = 'queued' THEN 1
                    WHEN status = 'completed' THEN 2
                    WHEN status = 'error' THEN 3
                    WHEN status = 'cancelled' THEN 4
                    ELSE 5
                END,
                updated_at DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def delete_export_job(self, job_id: str) -> bool:
    """Delete one export job row by id."""
    conn = self._get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM export_jobs WHERE job_id = ?", (job_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()


def reset_active_downloads(self, mark: str = "error", message: str = "Server restarted"):
    """Mark any downloads left in 'pending' or 'running' state as stopped.

    This is intended to be called at application startup so that stale
    download jobs don't cause the UI to continue polling indefinitely.
    """
    conn = self._get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='download_jobs'")
        if not cursor.fetchone():
            return 0

        cursor.execute(
            """
            UPDATE download_jobs
            SET status = ?,
                error_message = COALESCE(error_message, ?) || ' (server restart)',
                updated_at = CURRENT_TIMESTAMP
            WHERE status IN ('queued', 'pending', 'running')
        """,
            (mark, message),
        )
        count = cursor.rowcount
        conn.commit()
        return count
    finally:
        conn.close()


def reset_active_exports(self, mark: str = "error", message: str = "Server restarted") -> int:
    """Mark any exports left in queued/running state as stopped on startup."""
    conn = self._get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='export_jobs'")
        if not cursor.fetchone():
            return 0

        cursor.execute(
            """
            UPDATE export_jobs
            SET status = ?,
                error_message = COALESCE(error_message, ?) || ' (server restart)',
                finished_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE status IN ('queued', 'running')
            """,
            (mark, message),
        )
        count = cursor.rowcount
        conn.commit()
        return count
    finally:
        conn.close()


def cleanup_stale_data(self, retention_hours: int = 24) -> int:
    """Remove download job records older than `retention_hours` and prune their temp folders.

    Returns the number of jobs removed.
    """
    from ...config_manager import get_config_manager

    conn = self._get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='download_jobs'")
        if not cursor.fetchone():
            return 0

        cursor.execute(
            "SELECT job_id, doc_id FROM download_jobs WHERE created_at < datetime('now', ?)",
            (f"-{int(retention_hours)} hours",),
        )
        rows = cursor.fetchall()
        if not rows:
            return 0

        job_ids = [r[0] for r in rows]
        doc_ids = [r[1] for r in rows if r[1]]

        # Delete DB records
        placeholders = ",".join("?" for _ in job_ids)
        sql = f"DELETE FROM download_jobs WHERE job_id IN ({placeholders})"  # noqa: S608
        cursor.execute(sql, tuple(job_ids))
        conn.commit()

        # Prune temp dirs for associated doc_ids
        try:
            cm = get_config_manager()
            base_temp = cm.get_temp_dir()
            for did in set(doc_ids):
                if not did:
                    continue
                p = base_temp / str(did)
                if p.exists() and p.is_dir():
                    try:
                        # Use shutil.rmtree to remove contents
                        import shutil

                        shutil.rmtree(p)
                        logger.info("Pruned stale temp folder: %s", p)
                    except OSError:
                        logger.debug("Failed to remove temp folder %s", p, exc_info=True)
        except OSError:
            logger.debug("Failed to cleanup temp dirs for stale jobs", exc_info=True)

        return len(job_ids)
    finally:
        conn.close()


def attach_job_methods(cls) -> None:
    """Attach extracted download/export job methods to ``VaultManager``."""
    cls.create_download_job = create_download_job
    cls.update_download_job = update_download_job
    cls.get_active_download = get_active_download
    cls.get_active_downloads = get_active_downloads
    cls.get_download_job = get_download_job
    cls.list_download_jobs = list_download_jobs
    cls.delete_download_job = delete_download_job
    cls.create_export_job = create_export_job
    cls.update_export_job = update_export_job
    cls.get_export_job = get_export_job
    cls.list_export_jobs = list_export_jobs
    cls.delete_export_job = delete_export_job
    cls.reset_active_downloads = reset_active_downloads
    cls.reset_active_exports = reset_active_exports
    cls.cleanup_stale_data = cleanup_stale_data
