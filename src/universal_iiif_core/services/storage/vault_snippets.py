"""Snippet repository methods for VaultManager."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from ...logger import get_logger

logger = get_logger(__name__)


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
        logger.error(f"Error extracting snippet with fitz: {e}", exc_info=True)
        return None


def save_snippet(  # noqa: D417
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


def get_snippets(self, ms_name: str, page_num: int | None = None):  # noqa: D417
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


def attach_snippet_methods(cls) -> None:
    """Attach extracted snippet methods to ``VaultManager``."""
    cls.extract_image_snippet = extract_image_snippet
    cls.save_snippet = save_snippet
    cls.get_snippets = get_snippets
    cls.delete_snippet = delete_snippet
