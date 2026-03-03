import json
import shutil
import sqlite3
from contextlib import suppress
from pathlib import Path
from typing import Any

from ...exceptions import DatabaseError
from ...library_catalog import normalize_item_type
from ...logger import get_logger

logger = get_logger(__name__)


class VaultManager:
    """Manages the storage and retrieval of manuscripts and image snippets using SQLite."""

    def __init__(self, db_path: str = "data/vault.db"):
        """Initialize the VaultManager with the given database path.

        By default the DB is placed under the app `data/local` area derived
        from `ConfigManager` so storage is colocated with downloads and
        other user-data directories.
        """
        self.db_path = Path(db_path)
        if db_path == "data/vault.db":
            # Ensure the DB is placed in the repository data area
            self.db_path = Path("data/vault.db")

        self._ensure_db_dir()
        self._init_db()
        self._download_progress_cache: dict[str, tuple[int, int, str]] = {}

    def _ensure_db_dir(self):
        if not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()

        # Check if table exists and has correct schema
        force_recreate = False
        try:
            cursor.execute("PRAGMA table_info(manuscripts)")
            columns = {row[1] for row in cursor.fetchall()}
            required_cols = {"status", "local_path", "updated_at", "display_title"}
            if columns and not required_cols.issubset(columns):
                logger.warning("Old DB schema detected. Recreating 'manuscripts' table (Beta reset).")
                force_recreate = True
        except DatabaseError as exc:
            logger.debug("Schema check failed: %s", exc)

        if force_recreate:
            cursor.execute("DROP TABLE IF EXISTS manuscripts")

        # Table for manuscripts (simple reference)
        # - id: technical storage identifier (folder name, DB key) e.g. "btv1b10033406t"
        # - display_title: human-readable title for UI e.g. "Dante, Il Convito"
        # - title: legacy field, kept for compatibility
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manuscripts (
                id TEXT PRIMARY KEY,
                display_title TEXT,
                title TEXT,
                catalog_title TEXT,
                library TEXT,
                manifest_url TEXT,
                local_path TEXT,
                status TEXT,
                total_canvases INTEGER DEFAULT 0,
                downloaded_canvases INTEGER DEFAULT 0,
                asset_state TEXT DEFAULT 'saved',
                has_native_pdf INTEGER,
                pdf_local_available INTEGER DEFAULT 0,
                item_type TEXT DEFAULT 'non classificato',
                item_type_source TEXT DEFAULT 'auto',
                item_type_confidence REAL,
                item_type_reason TEXT,
                missing_pages_json TEXT,
                author TEXT,
                description TEXT,
                publisher TEXT,
                attribution TEXT,
                thumbnail_url TEXT,
                shelfmark TEXT,
                date_label TEXT,
                language_label TEXT,
                source_detail_url TEXT,
                reference_text TEXT,
                user_notes TEXT,
                metadata_json TEXT,
                last_sync_at TIMESTAMP,
                error_log TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table for snippets (image crops)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ms_name TEXT NOT NULL,
                page_num INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                category TEXT,
                transcription TEXT,
                notes TEXT,
                coords_json TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabella per i Job di Download
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS download_jobs (
                job_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                library TEXT NOT NULL,
                manifest_url TEXT,
                status TEXT DEFAULT 'queued',  -- queued, running, completed, error, cancelled
                current_page INTEGER DEFAULT 0,
                total_pages INTEGER DEFAULT 0,
                queue_position INTEGER DEFAULT 0,
                priority INTEGER DEFAULT 0,
                error_message TEXT,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS export_jobs (
                job_id TEXT PRIMARY KEY,
                scope_type TEXT DEFAULT 'batch',
                doc_ids_json TEXT,
                library TEXT,
                export_format TEXT,
                output_kind TEXT DEFAULT 'binary',
                selection_mode TEXT DEFAULT 'all',
                selected_pages_json TEXT,
                destination TEXT DEFAULT 'local_filesystem',
                destination_payload_json TEXT,
                capability_flags_json TEXT,
                status TEXT DEFAULT 'queued',
                current_step INTEGER DEFAULT 0,
                total_steps INTEGER DEFAULT 0,
                output_path TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manuscript_ui_preferences (
                manuscript_id TEXT NOT NULL,
                pref_key TEXT NOT NULL,
                pref_value_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (manuscript_id, pref_key)
            )
        """)

        self._migrate_manuscripts_table(cursor)
        self._migrate_download_jobs_table(cursor)
        self._migrate_export_jobs_table(cursor)
        self._migrate_manuscript_ui_preferences_table(cursor)

        conn.commit()
        conn.close()

    @staticmethod
    def _ensure_column(cursor: sqlite3.Cursor, table_name: str, column_name: str, ddl_fragment: str) -> None:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1] for row in cursor.fetchall()}
        if column_name in columns:
            return
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_fragment}")

    def _migrate_manuscripts_table(self, cursor: sqlite3.Cursor) -> None:
        self._ensure_column(cursor, "manuscripts", "asset_state", "TEXT DEFAULT 'saved'")
        self._ensure_column(cursor, "manuscripts", "has_native_pdf", "INTEGER")
        self._ensure_column(cursor, "manuscripts", "pdf_local_available", "INTEGER DEFAULT 0")
        self._ensure_column(cursor, "manuscripts", "item_type", "TEXT DEFAULT 'non classificato'")
        self._ensure_column(cursor, "manuscripts", "item_type_source", "TEXT DEFAULT 'auto'")
        self._ensure_column(cursor, "manuscripts", "item_type_confidence", "REAL")
        self._ensure_column(cursor, "manuscripts", "item_type_reason", "TEXT")
        self._ensure_column(cursor, "manuscripts", "missing_pages_json", "TEXT")
        self._ensure_column(cursor, "manuscripts", "catalog_title", "TEXT")
        self._ensure_column(cursor, "manuscripts", "shelfmark", "TEXT")
        self._ensure_column(cursor, "manuscripts", "date_label", "TEXT")
        self._ensure_column(cursor, "manuscripts", "language_label", "TEXT")
        self._ensure_column(cursor, "manuscripts", "source_detail_url", "TEXT")
        self._ensure_column(cursor, "manuscripts", "reference_text", "TEXT")
        self._ensure_column(cursor, "manuscripts", "user_notes", "TEXT")
        self._ensure_column(cursor, "manuscripts", "metadata_json", "TEXT")
        self._ensure_column(cursor, "manuscripts", "last_sync_at", "TIMESTAMP")
        self._ensure_column(cursor, "manuscripts", "author", "TEXT")
        self._ensure_column(cursor, "manuscripts", "description", "TEXT")
        self._ensure_column(cursor, "manuscripts", "publisher", "TEXT")
        self._ensure_column(cursor, "manuscripts", "attribution", "TEXT")
        self._ensure_column(cursor, "manuscripts", "thumbnail_url", "TEXT")
        self._backfill_metadata_fields(cursor)
        cursor.execute(
            """
            UPDATE manuscripts
            SET item_type = 'non classificato'
            WHERE item_type IS NULL OR TRIM(item_type) = '' OR LOWER(TRIM(item_type)) = 'altro'
            """
        )

    def _migrate_download_jobs_table(self, cursor: sqlite3.Cursor) -> None:
        self._ensure_column(cursor, "download_jobs", "queue_position", "INTEGER DEFAULT 0")
        self._ensure_column(cursor, "download_jobs", "priority", "INTEGER DEFAULT 0")
        self._ensure_column(cursor, "download_jobs", "started_at", "TIMESTAMP")
        self._ensure_column(cursor, "download_jobs", "finished_at", "TIMESTAMP")

    def _migrate_export_jobs_table(self, cursor: sqlite3.Cursor) -> None:
        self._ensure_column(cursor, "export_jobs", "scope_type", "TEXT DEFAULT 'batch'")
        self._ensure_column(cursor, "export_jobs", "doc_ids_json", "TEXT")
        self._ensure_column(cursor, "export_jobs", "library", "TEXT")
        self._ensure_column(cursor, "export_jobs", "export_format", "TEXT")
        self._ensure_column(cursor, "export_jobs", "output_kind", "TEXT DEFAULT 'binary'")
        self._ensure_column(cursor, "export_jobs", "selection_mode", "TEXT DEFAULT 'all'")
        self._ensure_column(cursor, "export_jobs", "selected_pages_json", "TEXT")
        self._ensure_column(cursor, "export_jobs", "destination", "TEXT DEFAULT 'local_filesystem'")
        self._ensure_column(cursor, "export_jobs", "destination_payload_json", "TEXT")
        self._ensure_column(cursor, "export_jobs", "capability_flags_json", "TEXT")
        self._ensure_column(cursor, "export_jobs", "status", "TEXT DEFAULT 'queued'")
        self._ensure_column(cursor, "export_jobs", "current_step", "INTEGER DEFAULT 0")
        self._ensure_column(cursor, "export_jobs", "total_steps", "INTEGER DEFAULT 0")
        self._ensure_column(cursor, "export_jobs", "output_path", "TEXT")
        self._ensure_column(cursor, "export_jobs", "error_message", "TEXT")
        self._ensure_column(cursor, "export_jobs", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        self._ensure_column(cursor, "export_jobs", "started_at", "TIMESTAMP")
        self._ensure_column(cursor, "export_jobs", "finished_at", "TIMESTAMP")
        self._ensure_column(cursor, "export_jobs", "updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    def _migrate_manuscript_ui_preferences_table(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manuscript_ui_preferences (
                manuscript_id TEXT NOT NULL,
                pref_key TEXT NOT NULL,
                pref_value_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (manuscript_id, pref_key)
            )
        """)

    def _backfill_metadata_fields(self, cursor: sqlite3.Cursor) -> None:
        """Populate author/description/publisher from metadata_json for existing rows."""
        cursor.execute(
            """
            SELECT id, metadata_json FROM manuscripts
            WHERE metadata_json IS NOT NULL
              AND metadata_json != ''
              AND metadata_json != '{}'
              AND (author IS NULL OR author = '')
            """
        )
        author_keys = {"author", "creator", "autore", "dc:creator", "dc.creator", "créateur"}
        desc_keys = {"description", "descrizione", "dc:description", "dc.description"}
        publisher_keys = {"publisher", "editore", "source", "dc:publisher", "dc.publisher", "éditeur"}
        for row in cursor.fetchall():
            ms_id, raw_json = row[0], row[1]
            try:
                meta = json.loads(raw_json)
            except Exception:  # noqa: S112
                continue
            if not isinstance(meta, dict):
                continue
            meta_lower = {k.lower().strip(): v for k, v in meta.items()}
            author = next((str(meta_lower[k]) for k in author_keys if k in meta_lower and meta_lower[k]), None)
            desc = next((str(meta_lower[k]) for k in desc_keys if k in meta_lower and meta_lower[k]), None)
            publisher = next((str(meta_lower[k]) for k in publisher_keys if k in meta_lower and meta_lower[k]), None)
            if author or desc or publisher:
                parts = []
                values: list[Any] = []
                if author:
                    parts.append("author = ?")
                    values.append(author)
                if desc:
                    parts.append("description = ?")
                    values.append(desc)
                if publisher:
                    parts.append("publisher = ?")
                    values.append(publisher)
                values.append(ms_id)
                sql = "UPDATE manuscripts SET " + ", ".join(parts) + " WHERE id = ?"  # noqa: S608
                cursor.execute(sql, values)

    def upsert_manuscript(self, manuscript_id: str, **kwargs):
        """Insert or update a manuscript record."""
        valid_keys = (
            "display_title",
            "title",
            "catalog_title",
            "library",
            "manifest_url",
            "local_path",
            "status",
            "total_canvases",
            "downloaded_canvases",
            "asset_state",
            "has_native_pdf",
            "pdf_local_available",
            "item_type",
            "item_type_source",
            "item_type_confidence",
            "item_type_reason",
            "missing_pages_json",
            "author",
            "description",
            "publisher",
            "attribution",
            "thumbnail_url",
            "shelfmark",
            "date_label",
            "language_label",
            "source_detail_url",
            "reference_text",
            "user_notes",
            "metadata_json",
            "last_sync_at",
            "error_log",
        )
        updates = {k: v for k, v in kwargs.items() if k in valid_keys}

        # Enforce library name standardization
        if updates.get("library") == "Vaticana (BAV)":
            updates["library"] = "Vaticana"

        # If display_title not set but title is, use title as display_title
        if "title" in updates and "display_title" not in updates:
            updates["display_title"] = updates["title"]

        if "item_type" in updates:
            updates["item_type"] = normalize_item_type(str(updates.get("item_type") or ""))

        if not updates:
            self.register_manuscript(manuscript_id)
            return

        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM manuscripts WHERE id = ?", (manuscript_id,))
            existing = cursor.fetchone()
            if existing is None:
                values = [manuscript_id] + [updates.get(k) for k in valid_keys]
                cursor.execute(
                    """
                    INSERT INTO manuscripts (
                        id,
                        display_title,
                        title,
                        catalog_title,
                        library,
                        manifest_url,
                        local_path,
                        status,
                        total_canvases,
                        downloaded_canvases,
                        asset_state,
                        has_native_pdf,
                        pdf_local_available,
                        item_type,
                        item_type_source,
                        item_type_confidence,
                        item_type_reason,
                        missing_pages_json,
                        author,
                        description,
                        publisher,
                        attribution,
                        thumbnail_url,
                        shelfmark,
                        date_label,
                        language_label,
                        source_detail_url,
                        reference_text,
                        user_notes,
                        metadata_json,
                        last_sync_at,
                        error_log
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    values,
                )
            else:
                existing_columns = tuple(existing.keys())
                existing_map = {column: existing[column] for column in existing_columns}
                if (
                    existing_map.get("item_type_source") == "manual"
                    and updates.get("item_type_source") == "auto"
                    and "item_type" in updates
                ):
                    updates.pop("item_type", None)
                    updates.pop("item_type_confidence", None)
                    updates.pop("item_type_reason", None)
                    updates.pop("item_type_source", None)

                values = [updates.get(k, existing_map.get(k)) for k in valid_keys]
                cursor.execute(
                    """
                    UPDATE manuscripts
                    SET display_title = ?,
                        title = ?,
                        catalog_title = ?,
                        library = ?,
                        manifest_url = ?,
                        local_path = ?,
                        status = ?,
                        total_canvases = ?,
                        downloaded_canvases = ?,
                        asset_state = ?,
                        has_native_pdf = ?,
                        pdf_local_available = ?,
                        item_type = ?,
                        item_type_source = ?,
                        item_type_confidence = ?,
                        item_type_reason = ?,
                        missing_pages_json = ?,
                        author = ?,
                        description = ?,
                        publisher = ?,
                        attribution = ?,
                        thumbnail_url = ?,
                        shelfmark = ?,
                        date_label = ?,
                        language_label = ?,
                        source_detail_url = ?,
                        reference_text = ?,
                        user_notes = ?,
                        metadata_json = ?,
                        last_sync_at = ?,
                        error_log = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (*values, manuscript_id),
                )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"DB Error upserting manuscript {manuscript_id}: {e}")
        finally:
            conn.close()

    @staticmethod
    def _compute_state(total: int, downloaded: int, status: str) -> str:
        running_states = {"queued", "running", "downloading", "pending"}
        if status in running_states:
            return status
        if status == "error":
            return "error"
        if downloaded <= 0:
            return "saved"
        if total <= 0 or downloaded >= total:
            return "complete"
        return "partial"

    @staticmethod
    def _fallback_status_from_counts(total: int, downloaded: int) -> str:
        if downloaded <= 0:
            return "saved"
        if total <= 0 or downloaded >= total:
            return "complete"
        return "partial"

    @staticmethod
    def _scan_page_numbers(directory: Path | None) -> set[int]:
        if not directory or not directory.exists():
            return set()
        pages: set[int] = set()
        for image in directory.glob("pag_*.jpg"):
            stem = image.stem or ""
            try:
                pages.add(int(stem.split("_")[-1]) + 1)
            except ValueError:
                logger.debug("Skipping malformed page filename while scanning %s: %s", directory, image.name)
        return pages

    def normalize_asset_states(self, limit: int = 200) -> int:
        """Backfill and normalize asset_state/item_type for existing rows."""
        rows = self.get_all_manuscripts()[: max(1, limit)]
        updated = 0
        active_keys = {
            (
                str(job.get("doc_id") or ""),
                str(job.get("library") or ""),
            )
            for job in self.get_active_downloads()
        }
        temp_root: Path | None = None
        try:
            from ...config_manager import get_config_manager

            temp_root = Path(get_config_manager().get_temp_dir())
        except DatabaseError:
            temp_root = None

        for row in rows:
            manuscript_id = str(row.get("id") or "")
            library = str(row.get("library") or "")
            local_path_raw = str(row.get("local_path") or "").strip()
            local_path = Path(local_path_raw) if local_path_raw else None
            scans_dir = local_path / "scans" if local_path else None
            scans_pages = self._scan_page_numbers(scans_dir)
            temp_pages = self._scan_page_numbers((temp_root / manuscript_id) if temp_root and manuscript_id else None)
            known_pages = scans_pages | temp_pages
            scans_count = len(scans_pages)
            temp_count = len(temp_pages)
            total = int(row.get("total_canvases") or 0)
            downloaded = max(int(row.get("downloaded_canvases") or 0), scans_count, temp_count)
            if total <= 0 and downloaded > 0:
                total = downloaded
            status = str(row.get("status") or "").lower()
            asset_state = str(row.get("asset_state") or "").lower()
            if status == "cancelling":
                status = "running"
            is_stale_running = (
                status in {"queued", "running", "downloading", "pending"}
                and (
                    manuscript_id,
                    library,
                )
                not in active_keys
            )
            if is_stale_running:
                status = self._fallback_status_from_counts(total, downloaded)

            target_state = self._compute_state(total, downloaded, status)
            allowed_statuses = {"saved", "partial", "complete", "error", "downloading", "queued", "running"}
            status_to_store = status if status in allowed_statuses else str(row.get("status") or "")
            normalized_type = normalize_item_type(str(row.get("item_type") or ""))
            missing_pages: list[int] = []
            if total > 0 and known_pages:
                missing_pages = [i for i in range(1, total + 1) if i not in known_pages]
            elif total > 0 and downloaded < total:
                missing_pages = [i for i in range(downloaded + 1, total + 1)] if downloaded > 0 else []
            missing_pages_json = json.dumps(missing_pages)

            if (
                status_to_store == str(row.get("status") or "")
                and target_state == asset_state
                and total == int(row.get("total_canvases") or 0)
                and downloaded == int(row.get("downloaded_canvases") or 0)
                and normalized_type == str(row.get("item_type") or "")
                and missing_pages_json == str(row.get("missing_pages_json") or "[]")
            ):
                continue

            self.upsert_manuscript(
                manuscript_id,
                status=status_to_store,
                asset_state=target_state,
                total_canvases=total,
                downloaded_canvases=downloaded,
                item_type=normalized_type,
                missing_pages_json=missing_pages_json,
            )
            updated += 1
        return updated

    def get_all_manuscripts(self):
        """Returns all manuscripts from the database."""
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM manuscripts ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_manuscript(self, ms_id: str):
        """Returns a single manuscript by ID."""
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM manuscripts WHERE id = ?", (ms_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_manuscript_ui_pref(self, manuscript_id: str, pref_key: str, default: Any = None) -> Any:
        """Read one manuscript-scoped UI preference."""
        if not manuscript_id or not pref_key:
            return default
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT pref_value_json
                FROM manuscript_ui_preferences
                WHERE manuscript_id = ? AND pref_key = ?
                """,
                (manuscript_id, pref_key),
            )
            row = cursor.fetchone()
            if not row:
                return default
            raw = str(row[0] or "").strip()
            if not raw:
                return default
            try:
                return json.loads(raw)
            except DatabaseError:
                return default
        finally:
            conn.close()

    def set_manuscript_ui_pref(self, manuscript_id: str, pref_key: str, pref_value: Any) -> None:
        """Persist one manuscript-scoped UI preference."""
        if not manuscript_id or not pref_key:
            return
        payload = json.dumps(pref_value, ensure_ascii=False)
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO manuscripts (id, title)
                VALUES (?, ?)
                """,
                (manuscript_id, None),
            )
            cursor.execute(
                """
                INSERT INTO manuscript_ui_preferences (manuscript_id, pref_key, pref_value_json, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(manuscript_id, pref_key) DO UPDATE SET
                    pref_value_json = excluded.pref_value_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (manuscript_id, pref_key, payload),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_manuscript(self, ms_id: str):
        """Delete manuscript DB record, snippets, and the manuscript folder on disk.

        The method removes snippet files, snippet rows, the manuscript row and
        — if the recorded `local_path` points inside the configured downloads
        directory — the whole manuscript folder on disk. This prevents accidental
        removal outside the app data directories.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            # Read recorded local_path/library for safety deletion and related job cleanup
            cursor.execute("SELECT local_path, library FROM manuscripts WHERE id = ?", (ms_id,))
            row = cursor.fetchone()
            local_path = row[0] if row and row[0] else None
            library = row[1] if row and len(row) > 1 and row[1] else None

            # 1. Get snippet paths for this manuscript
            cursor.execute("SELECT id, image_path FROM snippets WHERE ms_name = ?", (ms_id,))
            snippets = cursor.fetchall()

            # 2. Delete snippets physical files and DB entries
            for s_id, path in snippets:
                if path:
                    p = Path(path)
                    if p.exists():
                        with suppress(OSError):
                            p.unlink()
                cursor.execute("DELETE FROM snippets WHERE id = ?", (s_id,))

            # 3. Delete the manuscript DB entry
            cursor.execute("DELETE FROM manuscripts WHERE id = ?", (ms_id,))
            deleted = cursor.rowcount > 0

            # 3a. Delete manuscript-scoped UI preferences.
            cursor.execute("DELETE FROM manuscript_ui_preferences WHERE manuscript_id = ?", (ms_id,))

            # 3b. Remove historical download jobs for this manuscript to avoid stale
            # cards in the Download Manager after deletion from Library.
            if library:
                cursor.execute("DELETE FROM download_jobs WHERE doc_id = ? AND library = ?", (ms_id, library))
            else:
                cursor.execute("DELETE FROM download_jobs WHERE doc_id = ?", (ms_id,))
            conn.commit()

            # 4. Remove manuscript folder from disk if it's under configured downloads dir
            if local_path:
                try:
                    from ...config_manager import get_config_manager

                    cm = get_config_manager()
                    downloads_base = Path(cm.get_downloads_dir()).resolve()
                    candidate = Path(local_path).resolve()

                    # Safety: only remove when candidate is inside downloads_base
                    if downloads_base in candidate.parents or candidate == downloads_base:
                        if candidate.exists() and candidate.is_dir():
                            try:
                                shutil.rmtree(candidate)
                                logger.info("Removed manuscript folder from disk: %s", candidate)
                            except OSError:
                                logger.debug("Failed to remove manuscript folder %s", candidate, exc_info=True)
                    else:
                        logger.debug(
                            "Refusing to remove manuscript folder outside downloads dir: %s (base=%s)",
                            candidate,
                            downloads_base,
                        )
                except OSError:
                    logger.debug("Error while attempting to remove manuscript folder", exc_info=True)

            return deleted
        finally:
            conn.close()

    def search_manuscripts(self, query: str):
        """Search for manuscripts by ID, label, or library (SQL LIKE)."""
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            q = f"%{query}%"
            sql = """
                SELECT * FROM manuscripts
                WHERE id LIKE ?
                   OR display_title LIKE ?
                   OR title LIKE ?
                   OR library LIKE ?
                ORDER BY updated_at DESC
            """
            cursor.execute(sql, (q, q, q, q))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update_status(self, manuscript_id: str, status: str, error: str | None = None):
        """Update the status of a manuscript, optionally with an error log."""
        kwargs = {"status": status}
        if error:
            kwargs["error_log"] = error
        self.upsert_manuscript(manuscript_id, **kwargs)

    def register_manuscript(self, manuscript_id: str, title: str | None = None):
        """Ensures manuscript exists in DB."""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO manuscripts (id, title) VALUES (?, ?)", (manuscript_id, title))
            conn.commit()
        finally:
            conn.close()


from .vault_jobs import attach_job_methods  # noqa: E402
from .vault_snippets import attach_snippet_methods  # noqa: E402

attach_snippet_methods(VaultManager)
attach_job_methods(VaultManager)

__all__ = ["VaultManager"]
