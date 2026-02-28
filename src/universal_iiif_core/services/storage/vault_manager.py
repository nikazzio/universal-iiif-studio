import json
import shutil
import sqlite3
from contextlib import suppress
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

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
        except Exception as exc:
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

        self._migrate_manuscripts_table(cursor)
        self._migrate_download_jobs_table(cursor)

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
                        shelfmark,
                        date_label,
                        language_label,
                        source_detail_url,
                        reference_text,
                        user_notes,
                        metadata_json,
                        last_sync_at,
                        error_log
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        except Exception:
            temp_root = None

        for row in rows:
            manuscript_id = str(row.get("id") or "")
            library = str(row.get("library") or "")
            local_path_raw = str(row.get("local_path") or "").strip()
            local_path = Path(local_path_raw) if local_path_raw else None
            scans_dir = local_path / "scans" if local_path else None
            scans_pages = self._scan_page_numbers(scans_dir)
            temp_pages = self._scan_page_numbers((temp_root / manuscript_id) if temp_root and manuscript_id else None)
            known_pages = scans_pages or temp_pages
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
                            except Exception:
                                logger.debug("Failed to remove manuscript folder %s", candidate, exc_info=True)
                    else:
                        logger.debug(
                            "Refusing to remove manuscript folder outside downloads dir: %s (base=%s)",
                            candidate,
                            downloads_base,
                        )
                except Exception:
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

    def extract_image_snippet(self, image_path: str, coordinates: tuple) -> bytes | None:
        """Extracts a crop from an image using PyMuPDF (fitz).

        coordinates: (x0, y0, x1, y1) relative to the original image size.
        """
        try:
            # We assume image_path is a valid image file.
            # PyMuPDF can open images as simple documents.
            with fitz.open(image_path) as doc:
                page = doc.load_page(0)  # Images are 1-page documents
                rect = fitz.Rect(coordinates)

                # Pixmap of the cropped area
                pix = page.get_pixmap(clip=rect)

                # Convert to PNG bytes
                return pix.tobytes("png")
        except Exception as e:
            print(f"Error extracting snippet with fitz: {e}")
            return None

    def save_snippet(
        self,
        ms_name: str,
        page_num: int,
        image_path: str,
        category: str = "Uncategorized",
        transcription: str | None = None,
        notes: str | None = None,
        coords: list[Any] | None = None,
    ):
        """Saves the snippet to the database.

        Args:
            ms_name: Nome del manoscritto
            page_num: Numero pagina (1-indexed)
            image_path: Path del file immagine salvato
            category: Categoria (Capolettera, Glossa, etc)
            transcription: Trascrizione rapida
            notes: Note/commenti
            coords: Coordinate [x, y, width, height]
        """
        import json

        logger.debug(f"💾 SAVE_SNIPPET - ms_name='{ms_name}', page_num={page_num}, category='{category}'")

        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            coords_json = json.dumps(coords) if coords else None
            cursor.execute(
                """
                INSERT INTO snippets (ms_name, page_num, image_path, category, transcription, notes, coords_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (ms_name, page_num, image_path, category, transcription, notes, coords_json),
            )
            conn.commit()
            snippet_id = cursor.lastrowid
            logger.info(f"✅ Snippet ID {snippet_id} salvato: {category} - p.{page_num}")

            return snippet_id
        finally:
            conn.close()

    def get_snippets(self, ms_name: str, page_num: int | None = None):
        """Retrieve snippets for a manuscript, optionally filtered by page.

        Args:
            ms_name: Nome del manoscritto
            page_num: Numero pagina opzionale (1-indexed)

        Returns:
            List of snippet dictionaries
        """
        import json

        logger.debug(f"🔍 GET_SNIPPETS - ms_name='{ms_name}', page_num={page_num}")

        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            if page_num is not None:
                query = """
                    SELECT id, ms_name, page_num, image_path, category, transcription,
                           notes, coords_json, timestamp
                    FROM snippets
                    WHERE ms_name = ? AND page_num = ?
                    ORDER BY timestamp DESC
                """
                params = (ms_name, page_num)
                cursor.execute(query, params)
            else:
                query = """
                    SELECT id, ms_name, page_num, image_path, category, transcription,
                           notes, coords_json, timestamp
                    FROM snippets
                    WHERE ms_name = ?
                    ORDER BY page_num, timestamp DESC
                """
                params = (ms_name,)
                cursor.execute(query, params)

            rows = cursor.fetchall()
            logger.debug(f"Query eseguita: trovati {len(rows)} snippet")
            snippets = []
            for row in rows:
                snippets.append(
                    {
                        "id": row[0],
                        "ms_name": row[1],
                        "page_num": row[2],
                        "image_path": row[3],
                        "category": row[4],
                        "transcription": row[5],
                        "notes": row[6],
                        "coords_json": json.loads(row[7]) if row[7] else None,
                        "timestamp": row[8],
                    }
                )
            return snippets
        finally:
            conn.close()

    def delete_snippet(self, snippet_id: int):
        """Delete a snippet by ID and remove the physical file."""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            # Get image path before deleting
            cursor.execute("SELECT image_path FROM snippets WHERE id = ?", (snippet_id,))
            result = cursor.fetchone()

            if result and result[0]:
                image_path = Path(result[0])
                if image_path.exists():
                    with suppress(OSError):
                        image_path.unlink()

            # Delete from DB
            cursor.execute("DELETE FROM snippets WHERE id = ?", (snippet_id,))
            conn.commit()
        finally:
            conn.close()

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
                        except Exception:
                            title = None

                    log_message = "Download update: job=%s doc=%s title=%s %s/%s status=%s"
                    log_args = (job_id, doc_id or "-", title or "-", current, total, status)
                    if status in {"completed", "error", "cancelled", "cancelling", "paused"}:
                        logger.info(log_message, *log_args)
                    else:
                        logger.debug(log_message, *log_args)
                except Exception:
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
                        except Exception:
                            logger.debug("Failed to remove temp folder %s", p, exc_info=True)
            except Exception:
                logger.debug("Failed to cleanup temp dirs for stale jobs", exc_info=True)

            return len(job_ids)
        finally:
            conn.close()
