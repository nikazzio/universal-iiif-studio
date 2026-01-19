from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
from PIL import Image

from iiif_downloader.export_studio import build_professional_pdf


def _write_scan(scans_dir: Path, idx0: int, size=(800, 1200), color=(240, 240, 240)) -> Path:
    scans_dir.mkdir(parents=True, exist_ok=True)
    p = scans_dir / f"pag_{idx0:04d}.jpg"
    img = Image.new("RGB", size, color)
    img.save(p, format="JPEG", quality=85)
    return p


def test_build_professional_pdf_respects_selected_pages(tmp_path: Path) -> None:
    doc_dir = tmp_path / "doc"
    scans_dir = doc_dir / "scans"
    for i in range(5):
        _write_scan(scans_dir, i)

    out_path = tmp_path / "out.pdf"
    build_professional_pdf(
        doc_dir=doc_dir,
        output_path=out_path,
        selected_pages=[1, 3],
        cover_title="T",
        cover_curator="",
        cover_description="",
        manifest_meta={},
        transcription_json=None,
        mode="Solo immagini",
        compression="Standard",
        source_url="",
    )

    pdf = fitz.open(out_path)
    try:
        # cover + 2 selected pages + colophon
        assert pdf.page_count == 4
    finally:
        pdf.close()


def test_testo_a_fronte_renders_some_text_even_if_long(tmp_path: Path) -> None:
    doc_dir = tmp_path / "doc"
    scans_dir = doc_dir / "scans"
    _write_scan(scans_dir, 0)

    long_text = ("Hello world\n" * 500).strip()
    transcription = {"pages": [{"page_index": 1, "full_text": long_text}]}

    out_path = tmp_path / "out.pdf"
    build_professional_pdf(
        doc_dir=doc_dir,
        output_path=out_path,
        selected_pages=[1],
        cover_title="T",
        cover_curator="",
        cover_description="",
        manifest_meta={},
        transcription_json=transcription,
        mode="Testo a fronte",
        compression="Standard",
        source_url="",
    )

    pdf = fitz.open(out_path)
    try:
        # page 0 = cover, page 1 = scan, page 2 = transcription
        assert pdf.page_count == 4
        text = pdf.load_page(2).get_text("text").strip()
        assert len(text) > 0
    finally:
        pdf.close()


def test_pdf_ricercabile_embeds_searchable_text(tmp_path: Path) -> None:
    doc_dir = tmp_path / "doc"
    scans_dir = doc_dir / "scans"
    _write_scan(scans_dir, 0)

    transcription = {"pages": [{"page_index": 1, "full_text": "SearchMe"}]}

    out_path = tmp_path / "out.pdf"
    build_professional_pdf(
        doc_dir=doc_dir,
        output_path=out_path,
        selected_pages=[1],
        cover_title="T",
        cover_curator="",
        cover_description="",
        manifest_meta={},
        transcription_json=transcription,
        mode="PDF Ricercabile",
        compression="Standard",
        source_url="",
    )

    pdf = fitz.open(out_path)
    try:
        text = pdf.load_page(1).get_text("text")
        assert "SearchMe" in text
    finally:
        pdf.close()
