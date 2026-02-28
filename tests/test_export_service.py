from __future__ import annotations

import json
import zipfile
from pathlib import Path

from PIL import Image

from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.services.export.service import (
    execute_export_job,
    get_export_capabilities,
    parse_page_selection,
)


def _seed_document(doc_id: str, library: str, pages: int = 3) -> Path:
    cm = get_config_manager()
    root = cm.get_downloads_dir() / library / doc_id
    scans = root / "scans"
    data_dir = root / "data"
    scans.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    for idx in range(pages):
        image_path = scans / f"pag_{idx:04d}.jpg"
        Image.new("RGB", (800, 1200), (250, 250, 250)).save(image_path, format="JPEG", quality=85)

    metadata = {
        "title": f"Document {doc_id}",
        "manifest_url": f"https://example.org/{doc_id}/manifest.json",
    }
    (data_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return root


def test_export_capabilities_include_placeholders():
    """Future text/drive capabilities must be visible but disabled."""
    caps = get_export_capabilities()
    formats = {item["key"]: item for item in caps["formats"]}
    destinations = {item["key"]: item for item in caps["destinations"]}

    assert formats["txt_transcription"]["available"] is False
    assert formats["md_transcription"]["available"] is False
    assert destinations["google_drive"]["available"] is False


def test_parse_page_selection_expands_ranges_and_deduplicates():
    """Page parser should expand ranges and return sorted unique values."""
    assert parse_page_selection("1,3-5,5,8-7") == [1, 3, 4, 5, 7, 8]


def test_execute_export_job_creates_pdf_from_selected_pages():
    """PDF export should produce one artifact for one selected item."""
    _seed_document("DOC_EXPORT_PDF", "Gallica", pages=4)
    output = execute_export_job(
        job_id="exp_pdf_test",
        items=[{"doc_id": "DOC_EXPORT_PDF", "library": "Gallica"}],
        export_format="pdf_images",
        selection_mode="custom",
        selected_pages_raw="1,4",
        destination="local_filesystem",
    )

    assert output.exists()
    assert output.suffix.lower() == ".pdf"


def test_execute_export_job_batches_zip_outputs_into_bundle():
    """Multi-item export should return one final bundle archive."""
    _seed_document("DOC_EXPORT_ZIP_A", "Gallica", pages=2)
    _seed_document("DOC_EXPORT_ZIP_B", "Gallica", pages=2)

    output = execute_export_job(
        job_id="exp_zip_batch",
        items=[
            {"doc_id": "DOC_EXPORT_ZIP_A", "library": "Gallica"},
            {"doc_id": "DOC_EXPORT_ZIP_B", "library": "Gallica"},
        ],
        export_format="zip_images",
        selection_mode="all",
        selected_pages_raw="",
        destination="local_filesystem",
    )

    assert output.exists()
    assert output.suffix.lower() == ".zip"
    with zipfile.ZipFile(output, "r") as archive:
        names = archive.namelist()
    assert len(names) >= 2

