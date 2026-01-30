import shutil
import time
from pathlib import Path
from typing import Any

from ...config_manager import get_config_manager
from ...logger import get_logger
from ...utils import ensure_dir, load_json, save_json
from ..storage.vault_manager import VaultManager

logger = get_logger(__name__)


class OCRStorage:
    """Handles storage paths, metadata, and OCR persistence for documents."""

    STORAGE_VERSION = 3  # Incremented for DB Integration

    def __init__(self, base_dir: str = "downloads"):
        """Initialize download directories and the vault."""
        # Always use config.json as single source of truth
        base_dir = str(get_config_manager().get_downloads_dir())

        p = Path(base_dir).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        self.base_dir = p
        ensure_dir(self.base_dir)

        self.vault = VaultManager()

    def list_documents(self) -> list[dict[str, str]]:
        """List all manuscripts from the centralized database."""
        docs = []
        try:
            db_rows = self.vault.get_all_manuscripts()
            for row in db_rows:
                # Only show valid entries with a path or explicitly downloaded
                if row.get("status") in ["complete", "downloading", "pending"]:
                    path = row.get("local_path")
                    # If path is missing in DB (legacy), try to construct it
                    if not path:
                        path = str(self.base_dir / (row.get("library") or "Unknown") / row["id"])

                    docs.append(
                        {
                            "id": row["id"],
                            "library": row.get("library", "Unknown"),
                            "path": path,
                            "label": row.get("label", row["id"]),
                            "status": row.get("status", "unknown"),
                        }
                    )
        except Exception as e:
            logger.error(f"Failed to list documents from DB: {e}")
            # Fallback to file system if DB fails
            return self._list_documents_fs()

        return docs

    def _list_documents_fs(self) -> list[dict[str, str]]:
        """Legacy file-system scan."""
        docs = []
        for library_dir in self.base_dir.iterdir():
            if not library_dir.is_dir():
                continue
            for doc_dir in library_dir.iterdir():
                if not doc_dir.is_dir():
                    continue
                metadata_path = doc_dir / "data" / "metadata.json"
                if metadata_path.exists():
                    docs.append(
                        {
                            "id": doc_dir.name,
                            "library": library_dir.name,
                            "path": str(doc_dir),
                        }
                    )
        return docs

    def get_document_paths(self, doc_id: str, library: str = "Unknown") -> dict[str, Path]:  # noqa: C901
        """Retrieve authoritative paths for a document from DB or FS fallback."""
        doc_path = None

        # 1. Try Database First
        try:
            m = self.vault.get_manuscript(doc_id)
            if m and m.get("local_path"):
                doc_path = Path(m["local_path"])
        except Exception as exc:
            logger.debug("Vault lookup failed for %s: %s", doc_id, exc)

        # 2. Fallback: Path Construction with Tolerance
        if (not doc_path or not doc_path.exists()) and library and library != "Unknown":
            # Try exact match
            candidate = self.base_dir / library / doc_id
            if candidate.exists():
                doc_path = candidate
            else:
                # Try alternatives for backward compatibility
                aliases = {"Vaticana": "Vaticana (BAV)", "Vaticana (BAV)": "Vaticana"}
                if library in aliases:
                    candidate_alias = self.base_dir / aliases[library] / doc_id
                    if candidate_alias.exists():
                        doc_path = candidate_alias

            # If still not found, default to the requested library (will be created if downloading)
            if not doc_path:
                doc_path = self.base_dir / library / doc_id

        # 3. Fallback: Search in downloads dir
        if not doc_path or not doc_path.exists():
            for lib in self.base_dir.iterdir():
                if lib.is_dir() and (lib / doc_id).exists():
                    doc_path = lib / doc_id
                    break

        # 4. Final Fallback
        if not doc_path:
            doc_path = self.base_dir / (library or "Unknown") / doc_id

        return {
            "root": doc_path,
            "scans": doc_path / "scans",
            "pdf_dir": doc_path / "pdf",
            "pdf": doc_path / "pdf" / f"{doc_id}.pdf",
            "data": doc_path / "data",
            "exports": doc_path / "data" / "exports",
            "thumbnails": doc_path / "data" / "thumbnails",
            "metadata": doc_path / "data" / "metadata.json",
            "stats": doc_path / "data" / "image_stats.json",
            "transcription": doc_path / "data" / "transcription.json",
            "manifest": doc_path / "data" / "manifest.json",
            "history": doc_path / "history",
        }

    def load_image_stats(self, doc_id: str, library: str = "Unknown") -> dict[str, Any] | None:
        """Load image statistics."""
        paths = self.get_document_paths(doc_id, library)
        return load_json(paths["stats"])

    def load_metadata(self, doc_id: str, library: str = "Unknown") -> dict[str, Any] | None:
        """Load metadata for a document."""
        paths = self.get_document_paths(doc_id, library)
        return load_json(paths["metadata"])

    def save_transcription(
        self,
        doc_id: str,
        page_idx: int,
        ocr_data: dict[str, Any],
        library: str = "Unknown",
    ):
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
            "rich_text": ocr_data.get("rich_text", ""),
            "lines": ocr_data.get("lines", []),
            "engine": "manual" if is_manual else ocr_data.get("engine", "unknown"),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "is_manual": is_manual,
            "status": ocr_data.get("status", "draft"),  # draft, verified
            "average_confidence": ocr_data.get("average_confidence", 1.0 if is_manual else 0.0),
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

    def save_history(
        self,
        doc_id: str,
        page_idx: int,
        entry: dict[str, Any],
        library: str = "Unknown",
    ):
        """Save a snapshot to the per-page history log."""
        paths = self.get_document_paths(doc_id, library)
        history_dir = paths["history"]
        ensure_dir(history_dir)

        history_file = history_dir / f"p{page_idx:04d}_history.json"
        history_data = load_json(history_file) or []

        # Deduplication: Don't save if the text is identical to the last version
        if history_data:
            last_entry = history_data[-1]
            if (
                last_entry.get("full_text") == entry.get("full_text")
                and last_entry.get("status") == entry.get("status")
                and last_entry.get("engine") == entry.get("engine")
            ):
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

    def load_history(self, doc_id: str, page_idx: int, library: str = "Unknown") -> list[dict[str, Any]]:
        """Load the history log for a specific page."""
        paths = self.get_document_paths(doc_id, library)
        history_file = paths["history"] / f"p{page_idx:04d}_history.json"
        return load_json(history_file) or []

    def clear_history(self, doc_id: str, page_idx: int, library: str = "Unknown"):
        """Delete the history log for a specific page."""
        paths = self.get_document_paths(doc_id, library)
        history_file = paths["history"] / f"p{page_idx:04d}_history.json"
        if history_file.exists():
            history_file.unlink()
            logger.info(
                "History cleared for doc=%s, page=%s",
                doc_id,
                page_idx,
            )
            return True
        return False

    def load_transcription(self, doc_id: str, page_idx: int | None = None, library: str = "Unknown") -> Any:
        """Load transcription for a document or specific page."""
        paths = self.get_document_paths(doc_id, library)
        data = load_json(paths["transcription"])
        if not data:
            return None

        if page_idx is not None:
            return next(
                (p for p in data.get("pages", []) if p.get("page_index") == page_idx),
                None,
            )
        return data

    def search_manuscript(self, query: str) -> list[dict[str, Any]]:
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
                results.append(
                    {
                        "doc_id": doc["id"],
                        "library": doc["library"],
                        "matches": doc_matches,
                    }
                )
        return results

    def delete_document(self, doc_id: str, library: str = "Unknown"):
        """Completely remove a document from database and disk."""
        logger.info("🗑️ Deleting document: %s (%s)", doc_id, library)

        # 1. Database Cleanup (Manuscripts + Snippets)
        self.vault.delete_manuscript(doc_id)

        # 2. Physical File Cleanup
        paths = self.get_document_paths(doc_id, library)
        root_dir = paths.get("root")

        if root_dir and root_dir.exists():
            try:
                shutil.rmtree(root_dir)
                logger.info("✅ Physical files removed: %s", root_dir)
                return True
            except Exception as e:
                logger.error("❌ Failed to remove physical files: %s", e)
                return False

        logger.warning("⚠️ Root directory not found or already deleted: %s", root_dir)
        return True
