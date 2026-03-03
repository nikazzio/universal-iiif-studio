from __future__ import annotations

import time
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any

from PIL import Image
from requests import RequestException
from tqdm import tqdm

from ..config_manager import get_config_manager
from ..export_studio import build_professional_pdf
from ..utils import get_json


def create_pdf(self, files=None):
    """Generates a professional PDF with cover and colophon."""
    if files is None:
        files = sorted(
            [str(p) for p in self.scans_dir.iterdir() if p.name.startswith("pag_") and p.suffix.lower() == ".jpg"]
        )
    if not files:
        return

    output_path = self._determine_pdf_output_path()
    cm = get_config_manager()
    cover_cfg = cm.get_setting("pdf.cover", {})
    logo_bytes = self._load_logo_bytes(cover_cfg.get("logo_path", ""))
    curator = cover_cfg.get("curator", "")
    desc = cover_cfg.get("description", "")
    transcription_json = None
    if self.ocr_path.exists():
        transcription_json = get_json(str(self.ocr_path))

    try:
        self.logger.info(f"Generating PDF for {len(files)} pages...")
        self.logger.info("Creating Professional PDF with Cover & Colophon...")

        with tqdm(total=len(files), desc="Generating PDF", unit="page") as pbar:

            def update_progress(current, total):
                pbar.update(1)

            build_professional_pdf(
                doc_dir=self.doc_dir,
                output_path=output_path,
                selected_pages=list(range(1, len(files) + 1)),
                cover_title=str(self.label),
                cover_curator=curator,
                cover_description=desc or str(self.manifest.get("description", "")),
                manifest_meta=self.manifest,
                transcription_json=transcription_json,
                mode="Solo immagini",
                compression="Standard",
                source_url=self.manifest_url,
                cover_logo_bytes=logo_bytes,
                progress_callback=update_progress,
            )

        self.logger.info(f"PDF Generated successfully: {output_path}")
        self.logger.info(f"✅ PDF Created: {output_path}")
    except Exception as e:
        self.logger.error(f"Failed to generate professional PDF: {e}", exc_info=True)


def _determine_pdf_output_path(self):
    output_path = self.output_path
    if output_path.exists() and self.get_pdf_url():
        return self.pdf_dir / f"{self.ms_id}_compiled.pdf"
    return output_path


def _load_logo_bytes(self, logo_path):
    if not logo_path:
        return None
    lp = Path(logo_path)
    if not lp.exists():
        return None
    try:
        return lp.read_bytes()
    except OSError:
        self.logger.warning(f"Could not read logo at {logo_path}")
        return None


def download_native_pdf(self, pdf_url: str) -> bool:
    """Download a PDF advertised in the IIIF manifest rendering section."""
    try:
        with self.session.get(pdf_url, stream=True, timeout=getattr(self, "_request_timeout", (10, 60))) as r:
            r.raise_for_status()
            with self.output_path.open("wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True
    except (RequestException, OSError):
        self.logger.debug("Native PDF download failed", exc_info=True)
        return False


def _should_prefer_native_pdf(self) -> bool:
    try:
        return bool(self.cm.get_setting("pdf.prefer_native_pdf", True))
    except (OSError, ValueError, TypeError):
        return True


def _should_create_pdf_from_images(self) -> bool:
    try:
        return bool(self.cm.get_setting("pdf.create_pdf_from_images", False))
    except (OSError, ValueError, TypeError):
        return False


def _extract_pages_from_pdf(
    self,
    pdf_path: Path,
    progress_callback: Callable[[int, int], None] | None = None,
) -> bool:
    # Keep lookup through the public downloader module so tests can monkeypatch it.
    import universal_iiif_core.logic.downloader as downloader_module

    self._clear_existing_scans()
    viewer_dpi = int(self.cm.get_setting("pdf.viewer_dpi", 150) or 150)
    viewer_quality = int(self.cm.get_setting("images.viewer_quality", 90) or 90)
    ok, message = downloader_module.convert_pdf_to_images(
        pdf_path=pdf_path,
        output_dir=self.scans_dir,
        progress_callback=progress_callback,
        dpi=viewer_dpi,
        jpeg_quality=viewer_quality,
    )
    if ok:
        self.logger.info("Native PDF extraction completed: %s", message)
        return True
    self.logger.warning("Native PDF extraction failed: %s", message)
    self._clear_existing_scans()
    return False


def _clear_existing_scans(self) -> None:
    for scan_file in self.scans_dir.glob("pag_*.jpg"):
        with suppress(OSError):
            scan_file.unlink()


def _collect_scan_stats(self, source_label: str) -> list[dict[str, Any]]:
    page_stats: list[dict[str, Any]] = []
    for index, image_path in enumerate(sorted(self.scans_dir.glob("pag_*.jpg"))):
        try:
            with Image.open(image_path) as img:
                width, height = img.size
            page_stats.append(
                {
                    "page_index": index,
                    "filename": image_path.name,
                    "original_url": source_label,
                    "thumbnail_url": None,
                    "size_bytes": image_path.stat().st_size,
                    "width": width,
                    "height": height,
                    "resolution_category": "High" if width > 2500 else "Medium",
                }
            )
        except Exception:
            self.logger.debug("Failed to collect scan stats for %s", image_path, exc_info=True)
    return page_stats


def _try_native_pdf_flow(self, native_pdf_url: str, progress_callback: Callable[[int, int], None] | None) -> bool:
    self.logger.info("Manifest advertises native PDF: %s", native_pdf_url)
    if not self.download_native_pdf(native_pdf_url):
        self.logger.warning("Native PDF download failed; falling back to canvas image download.")
        return False

    if not self._extract_pages_from_pdf(self.output_path, progress_callback=progress_callback):
        self.logger.warning("Native PDF extraction failed; falling back to canvas image download.")
        return False

    page_stats = self._collect_scan_stats(f"{native_pdf_url} (native-pdf)")
    self._store_page_stats(page_stats)
    final_files = [str(path) for path in sorted(self.scans_dir.glob("pag_*.jpg"))]
    self.vault.upsert_manuscript(
        self.ms_id,
        status="complete",
        asset_state="complete",
        downloaded_canvases=len(final_files),
        total_canvases=len(final_files),
        pdf_local_available=1 if self.output_path.exists() else 0,
        missing_pages_json="[]",
        last_sync_at=time.strftime("%Y-%m-%d %H:%M:%S"),
    )
    try:
        from ..utils import clean_dir

        clean_dir(self.temp_dir)
    except OSError:
        self.logger.debug("Failed to clean temp dir %s", self.temp_dir, exc_info=True)

    if final_files and self.ocr_model:
        self.run_batch_ocr(final_files, self.ocr_model)
    return bool(final_files)


def attach_pdf_methods(cls) -> None:
    """Attach extracted PDF-related methods to ``IIIFDownloader``."""
    cls.create_pdf = create_pdf
    cls._determine_pdf_output_path = _determine_pdf_output_path
    cls._load_logo_bytes = _load_logo_bytes
    cls.download_native_pdf = download_native_pdf
    cls._should_prefer_native_pdf = _should_prefer_native_pdf
    cls._should_create_pdf_from_images = _should_create_pdf_from_images
    cls._extract_pages_from_pdf = _extract_pages_from_pdf
    cls._clear_existing_scans = _clear_existing_scans
    cls._collect_scan_stats = _collect_scan_stats
    cls._try_native_pdf_flow = _try_native_pdf_flow
