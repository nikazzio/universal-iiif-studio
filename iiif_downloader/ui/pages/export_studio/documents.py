from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from iiif_downloader.ocr.storage import OCRStorage


@dataclass(frozen=True)
class DocOption:
    label: str
    doc_id: str
    library: str
    doc_dir: Path
    meta: Dict[str, Any]


def safe_read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        import json

        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def load_document_option(storage: OCRStorage, doc: Dict[str, Any]) -> Optional[DocOption]:
    doc_dir = Path(doc.get("path") or "")
    if not doc_dir.exists():
        return None

    doc_id = str(doc.get("id") or "")
    library = str(doc.get("library") or "Unknown")
    if not doc_id:
        return None

    paths = storage.get_document_paths(doc_id, library)
    meta = safe_read_json(paths["metadata"])
    if not meta:
        meta = {"label": doc.get("title") or doc_dir.name}

    label = str(meta.get("label") or meta.get("title") or doc_dir.name)
    return DocOption(label=label, doc_id=doc_id, library=library, doc_dir=doc_dir, meta=meta)
