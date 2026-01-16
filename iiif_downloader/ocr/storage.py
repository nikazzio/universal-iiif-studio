import os
import shutil
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from iiif_downloader.utils import save_json, load_json, ensure_dir

class OCRStorage:
    def __init__(self, base_dir: str = "downloads"):
        self.base_dir = Path(base_dir)
        ensure_dir(self.base_dir)

    def list_documents(self) -> List[Dict[str, str]]:
        """List all manuscripts across all library subfolders."""
        docs = []
        for library_dir in self.base_dir.iterdir():
            if not library_dir.is_dir(): continue
            for doc_dir in library_dir.iterdir():
                if doc_dir.is_dir():
                    # Check for PDF or metadata (Image-first might not have PDF yet)
                    if (doc_dir / "metadata.json").exists():
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
             # Fallback to base (legacy) or Unknown
             doc_path = self.base_dir / library / doc_id

        return {
            "root": doc_path,
            "pdf": doc_path / f"{doc_id}.pdf",
            "pages": doc_path / "pages",
            "metadata": doc_path / "metadata.json",
            "transcription": doc_path / "transcription.json"
        }

    def load_metadata(self, doc_id: str, library: str = "Unknown") -> Optional[Dict[str, Any]]:
        """Load metadata for a document."""
        paths = self.get_document_paths(doc_id, library)
        return load_json(paths["metadata"])

    def save_transcription(self, doc_id: str, page_idx: int, ocr_data: Dict[str, Any], library: str = "Unknown"):
        """Save OCR result for a specific page in a document."""
        paths = self.get_document_paths(doc_id, library)
        data = load_json(paths["transcription"]) or {"pages": [], "doc_id": doc_id}
        
        pages = data.get("pages", [])
        new_entry = {
            "page_index": page_idx,
            "full_text": ocr_data.get("full_text", ""),
            "lines": ocr_data.get("lines", []),
            "engine": ocr_data.get("engine", "unknown"),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Update existing or add new
        updated = False
        for i, p in enumerate(pages):
            if p.get("page_index") == page_idx:
                pages[i] = new_entry
                updated = True
                break
        
        if not updated:
            pages.append(new_entry)
            pages.sort(key=lambda x: x["page_index"])
        
        data["pages"] = pages
        save_json(paths["transcription"], data)
        return True

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
            if not data: continue
            
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

    def migrate_legacy(self):
        """Migrate legacy structure to document-centric structure."""
        # Old files: Urb.lat.1779.pdf, Urb.lat.1779_metadata.json
        # Old folder: transcriptions/Urb.lat.1779_ocr.json
        
        migrated_count = 0
        
        # 1. Look for root PDFs or legacy doc folders
        for item in self.base_dir.iterdir():
            if not item.is_dir(): continue
            if item.name in ["Vaticana", "Gallica", "Bodleian", "Unknown"]: continue
            
            # This is a legacy doc folder like downloads/Urb.lat.1779
            doc_id = item.name
            
            # Guess library from metadata if exists
            library = "Unknown"
            meta_file = item / "metadata.json"
            if meta_file.exists():
                meta = load_json(meta_file)
                manifest_url = meta.get("manifest_url", "").lower()
                if "vatlib.it" in manifest_url: library = "Vaticana"
                elif "gallica.bnf.fr" in manifest_url: library = "Gallica"
                elif "bodleian.ox.ac.uk" in manifest_url: library = "Bodleian"
            
            target_lib_dir = self.base_dir / library
            ensure_dir(target_lib_dir)
            
            target_doc_dir = target_lib_dir / doc_id
            if not target_doc_dir.exists():
                shutil.move(str(item), str(target_doc_dir))
                migrated_count += 1
            else:
                # Merge or skip
                print(f"Skipping migration for {doc_id}, already exists in {library}")

        # Also migrate loose PDFs if any
        for pdf_file in self.base_dir.glob("*.pdf"):
            doc_id = pdf_file.stem
            library = "Unknown" # Hard to guess without meta
            
            target_doc_dir = self.base_dir / library / doc_id
            ensure_dir(target_doc_dir)
            shutil.move(str(pdf_file), str(target_doc_dir / f"{doc_id}.pdf"))
            migrated_count += 1
            
        # Clean up legacy folder if empty
        legacy_trans_folder = self.base_dir / "transcriptions"
        if legacy_trans_folder.exists() and not any(legacy_trans_folder.iterdir()):
            legacy_trans_folder.rmdir()
            
        return migrated_count
