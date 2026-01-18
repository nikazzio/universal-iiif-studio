import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from iiif_downloader.logger import get_logger
from iiif_downloader.utils import ensure_dir, load_json, save_json

logger = get_logger(__name__)


class OCRStorage:
    STORAGE_VERSION = 2  # Incremented to force refresh after directory reorganization

    def __init__(self, base_dir: str = "downloads"):
        self.base_dir = Path(base_dir)
        ensure_dir(self.base_dir)

    def list_documents(self) -> List[Dict[str, str]]:
        """List all manuscripts across all library subfolders."""
        docs = []
        for library_dir in self.base_dir.iterdir():
            if not library_dir.is_dir():
                continue
            for doc_dir in library_dir.iterdir():
                if doc_dir.is_dir():
                    # Clean look for metadata in new 'data' folder
                    if (doc_dir / "data" / "metadata.json").exists():
                        docs.append({
                            "id": doc_dir.name,
                            "library": library_dir.name,
                            "path": str(doc_dir)
                        })
        return docs

    def get_document_paths(self, doc_id: str, library: str = "Unknown") -> Dict[str, Path]:
        """Get paths for a specific document, searching if library unknown."""
        doc_path = None
        if library and library != "Unknown":
            doc_path = self.base_dir / library / doc_id

        # Search if not found or library unknown
        if not doc_path or not doc_path.exists():
            for lib in self.base_dir.iterdir():
                if lib.is_dir() and (lib / doc_id).exists():
                    doc_path = lib / doc_id
                    break

        if not doc_path:
            doc_path = self.base_dir / library / doc_id

        return {
            "root": doc_path,
            "scans": doc_path / "scans",
            "pdf_dir": doc_path / "pdf",
            "pdf": doc_path / "pdf" / f"{doc_id}.pdf",
            "data": doc_path / "data",
            "metadata": doc_path / "data" / "metadata.json",
            "stats": doc_path / "data" / "image_stats.json",
            "transcription": doc_path / "data" / "transcription.json",
            "manifest": doc_path / "data" / "manifest.json",
            "history": doc_path / "history"
        }

    def load_image_stats(self, doc_id: str, library: str = "Unknown") -> Optional[Dict[str, Any]]:
        """Load image statistics."""
        paths = self.get_document_paths(doc_id, library)
        return load_json(paths["stats"])

    def load_metadata(self, doc_id: str, library: str = "Unknown") -> Optional[Dict[str, Any]]:
        """Load metadata for a document."""
        paths = self.get_document_paths(doc_id, library)
        return load_json(paths["metadata"])

    def save_transcription(self, doc_id: str, page_idx: int, ocr_data: Dict[str, Any], library: str = "Unknown"):
        """Save OCR result for a specific page in a document."""
        logger.info(
            "Saving transcription to disk: doc=%s, page=%s, engine=%s",
            doc_id,
            page_idx,
            ocr_data.get("engine"),
        )
        paths = self.get_document_paths(doc_id, library)
        data = load_json(paths["transcription"]) or {"pages": [], "doc_id": doc_id}

        pages = data.get("pages", [])
        is_manual = ocr_data.get("is_manual", False)

        new_entry = {
            "page_index": page_idx,
            "full_text": ocr_data.get("full_text", ""),
            "lines": ocr_data.get("lines", []),
            "engine": "manual" if is_manual else ocr_data.get("engine", "unknown"),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "is_manual": is_manual,
            "status": ocr_data.get("status", "draft"),  # draft, verified
            "average_confidence": ocr_data.get("average_confidence", 1.0 if is_manual else 0.0)
        }

        # Update existing or add new
        updated = False
        for i, p in enumerate(pages):
            if p.get("page_index") == page_idx:
                # Merge existing status if not provided in new data
                if "status" not in ocr_data:
                    new_entry["status"] = p.get("status", "draft")
                pages[i] = new_entry
                updated = True
                break

        if not updated:
            pages.append(new_entry)
            pages.sort(key=lambda x: x["page_index"])

        data["pages"] = pages
        save_json(paths["transcription"], data)

        # Automatically log history
        self.save_history(doc_id, page_idx, new_entry, library)

        return True

    def save_history(self, doc_id: str, page_idx: int, entry: Dict[str, Any], library: str = "Unknown"):
        """Save a snapshot to the per-page history log."""
        paths = self.get_document_paths(doc_id, library)
        history_dir = paths["history"]
        ensure_dir(history_dir)

        history_file = history_dir / f"p{page_idx:04d}_history.json"
        history_data = load_json(history_file) or []

        # Deduplication: Don't save if the text is identical to the last version
        if history_data:
            last_entry = history_data[-1]
            if last_entry.get("full_text") == entry.get("full_text") and last_entry.get("status") == entry.get("status"):
                logger.debug(
                    "Skipping duplicate history snapshot for page %s",
                    page_idx,
                )
                return

        # Add entry with its own timestamp if not present
        if "timestamp" not in entry:
            entry["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        history_data.append(entry)

        # Keep only last 50 versions to avoid massive files (still very safe)
        if len(history_data) > 50:
            history_data = history_data[-50:]

        save_json(history_file, history_data)
        logger.debug("History snapshot saved for page %s", page_idx)

    def load_history(self, doc_id: str, page_idx: int, library: str = "Unknown") -> List[Dict[str, Any]]:
        """Load the history log for a specific page."""
        paths = self.get_document_paths(doc_id, library)
        history_file = paths["history"] / f"p{page_idx:04d}_history.json"
        return load_json(history_file) or []

    def clear_history(self, doc_id: str, page_idx: int, library: str = "Unknown"):
        """Delete the history log for a specific page."""
        paths = self.get_document_paths(doc_id, library)
        history_file = paths["history"] / f"p{page_idx:04d}_history.json"
        if history_file.exists():
            os.remove(history_file)
            logger.info(
                "History cleared for doc=%s, page=%s",
                doc_id,
                page_idx,
            )
            return True
        return False

    def load_transcription(self, doc_id: str, page_idx: Optional[int] = None, library: str = "Unknown") -> Any:
        """Load transcription for a document or specific page."""
        paths = self.get_document_paths(doc_id, library)
        data = load_json(paths["transcription"])
        if not data:
            return None

        if page_idx is not None:
            return next((p for p in data.get("pages", []) if p.get("page_index") == page_idx), None)
        return data

    def search_manuscript(self, query: str) -> List[Dict[str, Any]]:
        """Search query across all documents and their transcriptions."""
        results = []
        for doc in self.list_documents():
            data = self.load_transcription(doc["id"], library=doc["library"])
            if not data:
                continue

            doc_matches = []
            for page in data.get("pages", []):
                if query.lower() in page.get("full_text", "").lower():
                    doc_matches.append(page)

            if doc_matches:
                results.append({
                    "doc_id": doc["id"],
                    "library": doc["library"],
                    "matches": doc_matches
                })
        return results
