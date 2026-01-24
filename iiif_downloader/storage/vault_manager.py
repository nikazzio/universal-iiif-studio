import sqlite3
from contextlib import suppress
from pathlib import Path

import fitz  # PyMuPDF

from iiif_downloader.logger import get_logger

logger = get_logger(__name__)


class VaultManager:
    """Manages the storage and retrieval of manuscripts and image snippets using SQLite."""

    def __init__(self, db_path: str = "data/vault.db"):
        """Initialize the VaultManager with the given database path."""
        self.db_path = Path(db_path)
        self._ensure_db_dir()
        self._init_db()

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
            required_cols = {"status", "local_path", "updated_at"}
            if columns and not required_cols.issubset(columns):
                logger.warning("Old DB schema detected. Recreating 'manuscripts' table (Beta reset).")
                force_recreate = True
        except Exception as exc:
            logger.debug("Schema check failed: %s", exc)

        if force_recreate:
            cursor.execute("DROP TABLE IF EXISTS manuscripts")

        # Table for manuscripts (simple reference)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manuscripts (
                id TEXT PRIMARY KEY,
                title TEXT,
                library TEXT,
                manifest_url TEXT,
                local_path TEXT,
                status TEXT,
                total_canvases INTEGER DEFAULT 0,
                downloaded_canvases INTEGER DEFAULT 0,
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

        conn.commit()
        conn.close()

    def upsert_manuscript(self, manuscript_id: str, **kwargs):
        """Insert or update a manuscript record."""
        valid_keys = (
            "title",
            "library",
            "manifest_url",
            "local_path",
            "status",
            "total_canvases",
            "downloaded_canvases",
            "error_log",
        )
        updates = {k: v for k, v in kwargs.items() if k in valid_keys}
        if not updates:
            self.register_manuscript(manuscript_id)
            return

        conn = self._get_conn()
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
                        title,
                        library,
                        manifest_url,
                        local_path,
                        status,
                        total_canvases,
                        downloaded_canvases,
                        error_log
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            else:
                values = [updates.get(k, existing[idx + 1]) for idx, k in enumerate(valid_keys)]
                cursor.execute(
                    """
                    UPDATE manuscripts
                    SET title = ?,
                        library = ?,
                        manifest_url = ?,
                        local_path = ?,
                        status = ?,
                        total_canvases = ?,
                        downloaded_canvases = ?,
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
        """Deletes a manuscript from the database."""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM manuscripts WHERE id = ?", (ms_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
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
                WHERE id LIKE ? OR label LIKE ? OR library LIKE ? OR attribution LIKE ?
                ORDER BY updated_at DESC
            """
            cursor.execute(sql, (q, q, q, q))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update_status(self, manuscript_id: str, status: str, error: str = None):
        """Update the status of a manuscript, optionally with an error log."""
        kwargs = {"status": status}
        if error:
            kwargs["error_log"] = error
        self.upsert_manuscript(manuscript_id, **kwargs)

    def register_manuscript(self, manuscript_id: str, title: str = None):
        """Ensures manuscript exists in DB."""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO manuscripts (id, title) VALUES (?, ?)", (manuscript_id, title))
            conn.commit()
        finally:
            conn.close()

    def extract_image_snippet(self, image_path: str, coordinates: tuple) -> bytes:
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
        category: str = None,
        transcription: str = None,
        notes: str = None,
        coords: list = None,
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

    def get_snippets(self, ms_name: str, page_num: int = None):
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
