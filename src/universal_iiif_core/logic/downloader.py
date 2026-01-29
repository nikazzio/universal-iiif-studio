from __future__ import annotations

import shutil
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from secrets import SystemRandom
from typing import Any, Optional, Union

import requests
from PIL import Image
from requests import RequestException
from tqdm import tqdm

from ..config_manager import get_config_manager
from ..export_studio import build_professional_pdf
from ..iiif_tiles import stitch_iiif_tiles_to_jpeg
from ..logger import get_download_logger
from ..services.storage.vault_manager import VaultManager
from ..utils import DEFAULT_HEADERS, clean_dir, ensure_dir, get_json, save_json

# Constants
MAX_DOWNLOAD_RETRIES = 5
THROTTLE_BASE_WAIT = 15
VATICAN_MIN_DELAY = 1.5
VATICAN_MAX_DELAY = 4.0
NORMAL_MIN_DELAY = 0.4
NORMAL_MAX_DELAY = 1.2

SECURE_RANDOM = SystemRandom()


def _sanitize_filename(label: str) -> str:
    safe = "".join([c for c in str(label) if c.isalnum() or c in (" ", ".", "_", "-")])
    return safe.strip().replace(" ", "_")


class IIIFDownloader:
    """Class to handle IIIF manifest downloading and processing."""

    def __init__(
        self,
        manifest_url: str,
        output_dir: Union[str, Path, None] = None,
        output_name: str | None = None,
        workers: int = 4,
        clean_cache: bool = False,
        prefer_images: bool = False,
        ocr_model: str | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
        library: str = "Unknown",
    ):
        """Initialize the IIIFDownloader."""
        self.manifest_url = manifest_url
        self.workers = workers
        self.clean_cache = clean_cache
        self.prefer_images = prefer_images
        self.ocr_model: str | None = ocr_model
        self.progress_callback: Callable[[int, int], None] | None = progress_callback
        self.library = library

        self.manifest: dict[str, Any] = get_json(manifest_url) or {}
        self.label = self.manifest.get("label", "unknown_manuscript")
        if isinstance(self.label, list):
            self.label = self.label[0] if self.label else "unknown_manuscript"

        sanitized_label = _sanitize_filename(str(self.label))

        self.ms_id = (
            (output_name[:-4] if output_name.endswith(".pdf") else output_name) if output_name else sanitized_label
        )
        self.logger = get_download_logger(self.ms_id)

        # Resolve output base directory. Prefer explicit param; otherwise use config manager.
        cm = get_config_manager()
        if output_dir is None:
            out_base = cm.get_downloads_dir()
        else:
            out_base = Path(output_dir).expanduser()
            if not out_base.is_absolute():
                out_base = (Path.cwd() / out_base).resolve()
            # Ensure we have an absolute, resolved path
            out_base = out_base.resolve()

        lib_dir = out_base / self.library
        ensure_dir(lib_dir)
        self.doc_dir = lib_dir / self.ms_id
        ensure_dir(self.doc_dir)

        # New structure
        self.scans_dir = self.doc_dir / "scans"
        self.pdf_dir = self.doc_dir / "pdf"
        self.data_dir = self.doc_dir / "data"

        ensure_dir(self.scans_dir)
        ensure_dir(self.pdf_dir)
        ensure_dir(self.data_dir)

        self.output_path = self.pdf_dir / f"{self.ms_id}.pdf"
        self.meta_path = self.data_dir / "metadata.json"
        self.stats_path = self.data_dir / "image_stats.json"
        self.ocr_path = self.data_dir / "transcription.json"
        self.manifest_path = self.data_dir / "manifest.json"

        # Use true temp dir for atomic download
        cm = get_config_manager()
        base_temp = cm.get_temp_dir()
        self.temp_dir = base_temp / self.ms_id
        ensure_dir(self.temp_dir)

        # Database registration
        self.vault = VaultManager()
        try:
            # Just initial registration, details updated in run()
            self.vault.upsert_manuscript(
                self.ms_id,
                title=str(self.label),
                library=self.library,
                manifest_url=self.manifest_url,
                local_path=str(self.doc_dir),
                status="pending",
            )
        except Exception as e:
            self.logger.warning(f"Failed to register manuscript in DB: {e}")

        import threading

        self._lock = threading.Lock()
        self._tile_stitch_sem = threading.Semaphore(1)
        self._backoff_until = 0
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

        if "vatlib.it" in self.manifest_url.lower():
            viewer_url = self.manifest_url.replace("/iiif/", "/view/").replace("/manifest.json", "")
            try:
                self.session.get(viewer_url, timeout=20)
                self.session.headers.update(
                    {"Referer": viewer_url, "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"}
                )
            except Exception:
                self.logger.debug("Unable to pre-warm Vatican viewer session", exc_info=True)

    def get_pdf_url(self):
        """Check the manifest for a native PDF URL in the rendering section."""
        rendering = self.manifest.get("rendering", [])
        if isinstance(rendering, dict):
            rendering = [rendering]
        for item in rendering:
            if not isinstance(item, dict):
                continue
            fmt = item.get("format")
            url = (item.get("@id") or item.get("id") or "").lower()
            if fmt == "application/pdf" or url.endswith(".pdf"):
                return item.get("@id") or item.get("id")
        return None

    def extract_metadata(self):
        """Extract and save basic metadata from the manifest."""
        metadata = {
            "id": self.ms_id,
            "title": self.label,
            "attribution": self.manifest.get("attribution"),
            "description": self.manifest.get("description"),
            "manifest_url": self.manifest_url,
            "download_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_json(self.meta_path, metadata)
        save_json(self.manifest_path, self.manifest)

    def get_canvases(self):
        """Retrieve the list of canvases from the manifest."""
        sequences = self.manifest.get("sequences", [])
        if sequences:
            return sequences[0].get("canvases", [])
        items = self.manifest.get("items", [])
        if items:
            return items
        return []

    def download_page(self, canvas: dict[str, Any], index: int, folder: Path | str):
        """Download a single page image from a canvas."""
        try:
            base_url = self._resolve_canvas_base_url(canvas)
            if not base_url:
                return None

            cm = get_config_manager()
            iiif_q = cm.get_setting("images.iiif_quality", "default")
            strategy = cm.get_setting("images.download_strategy", ["max", "3000", "1740"])
            urls_to_try = [f"{base_url}/full/{s},/0/{iiif_q}.jpg" for s in strategy]

            folder_p = Path(folder)
            filename = folder_p / f"pag_{index:04d}.jpg"

            resumed = self._resume_existing_scan(filename, base_url, canvas, index)
            if resumed:
                return resumed

            downloaded = self._download_with_retries(urls_to_try, filename, canvas, index, base_url)
            if downloaded:
                return downloaded

            return self._stitch_tiles_from_service(cm, filename, base_url, canvas, index, iiif_q)
        except Exception:
            self.logger.debug("Failed to download page %s", index, exc_info=True)
            return None

    def _resolve_canvas_base_url(self, canvas: dict[str, Any]):
        images = canvas.get("images") or canvas.get("items") or []
        if not images:
            return None

        img_obj = images[0]
        annotation_type = img_obj.get("@type") or img_obj.get("type") or ""
        resource = img_obj.get("resource") or img_obj.get("body") if "Annotation" in annotation_type else img_obj
        if not resource:
            return None

        service = resource.get("service")
        if isinstance(service, list):
            service = service[0]
        base_url = (service or {}).get("@id") or (service or {}).get("id")
        if not base_url:
            val = resource.get("@id") or resource.get("id") or ""
            base_url = val.split("/full/")[0] if "/full/" in val else val
        return base_url

    def _resume_existing_scan(self, filename: Path, base_url: str, canvas: dict[str, Any], index: int):
        if not filename.exists() or filename.stat().st_size == 0:
            return None
        try:
            with Image.open(filename) as img:
                img.verify()

            with Image.open(filename) as img:
                width, height = img.size

            stats = {
                "page_index": index,
                "filename": filename.name,
                "original_url": f"{base_url} (cached)",
                "thumbnail_url": self._get_thumbnail_url(canvas),
                "size_bytes": filename.stat().st_size,
                "width": width,
                "height": height,
                "resolution_category": "High" if width > 2500 else "Medium",
            }
            self.logger.info(f"Resuming valid file: {filename}")
            return str(filename), stats
        except Exception as exc:
            self.logger.warning("Found corrupt file %s, re-downloading. Error: %s", filename, exc, exc_info=True)
            return None

    def _download_with_retries(
        self,
        urls_to_try: list[str],
        filename: Path,
        canvas: dict[str, Any],
        index: int,
        base_url: str,
    ):
        for attempt in range(MAX_DOWNLOAD_RETRIES):
            now = time.time()
            if now < self._backoff_until:
                jitter = SECURE_RANDOM.uniform(0.1, 0.5)
                time.sleep(self._backoff_until - now + jitter)
            delay = (
                SECURE_RANDOM.uniform(VATICAN_MIN_DELAY, VATICAN_MAX_DELAY)
                if "vatlib.it" in self.manifest_url.lower()
                else SECURE_RANDOM.uniform(NORMAL_MIN_DELAY, NORMAL_MAX_DELAY)
            )
            time.sleep(delay)

            for url in urls_to_try:
                try:
                    r = self.session.get(url, timeout=30)
                    if r.status_code == 200 and r.content:
                        with filename.open("wb") as f:
                            f.write(r.content)
                        with Image.open(str(filename)) as img:
                            width, height = img.size
                        stats = {
                            "page_index": index,
                            "filename": filename.name,
                            "original_url": url,
                            "thumbnail_url": self._get_thumbnail_url(canvas),
                            "size_bytes": len(r.content),
                            "width": width,
                            "height": height,
                            "resolution_category": "High" if width > 2500 else "Medium",
                        }
                        return str(filename), stats
                    if r.status_code == 429:
                        with self._lock:
                            wait = (2**attempt) * THROTTLE_BASE_WAIT
                            self._backoff_until = time.time() + wait
                        break
                except Exception as exc:
                    self.logger.debug("Download attempt failed for %s: %s", url, exc, exc_info=True)
                    continue
        return None

    def _stitch_tiles_from_service(
        self,
        cm,
        filename: Path,
        base_url: str,
        canvas: dict[str, Any],
        index: int,
        iiif_q: str,
    ):
        acquired = self._tile_stitch_sem.acquire(timeout=1)
        if not acquired:
            return None
        try:
            try:
                max_ram_gb = float(cm.get_setting("images.tile_stitch_max_ram_gb", 2) or 2)
            except (TypeError, ValueError):
                max_ram_gb = 2.0
            max_ram_gb = max(1.0, min(max_ram_gb, 64.0))
            max_ram_bytes = int(max_ram_gb * (1024**3))

            dims = stitch_iiif_tiles_to_jpeg(
                self.session,
                base_url,
                filename,
                iiif_quality=iiif_q,
                jpeg_quality=90,
                # Keep RAM usage under the configured cap.
                max_ram_bytes=max_ram_bytes,
                timeout_s=30,
            )
            if dims:
                width, height = dims
                stats = {
                    "page_index": index,
                    "filename": filename.name,
                    "original_url": f"{base_url} (tile-stitch)",
                    "thumbnail_url": self._get_thumbnail_url(canvas),
                    "size_bytes": filename.stat().st_size if filename.exists() else None,
                    "width": width,
                    "height": height,
                    "resolution_category": "High" if width > 2500 else "Medium",
                }
                return str(filename), stats
        finally:
            self._tile_stitch_sem.release()
        return None

    def _get_thumbnail_url(self, canvas: dict[str, Any]):
        thumbnail = canvas.get("thumbnail")
        if not thumbnail:
            return None
        if isinstance(thumbnail, list):
            thumbnail = thumbnail[0]
        if isinstance(thumbnail, dict):
            return thumbnail.get("@id") or thumbnail.get("id")
        return thumbnail

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
            print("Creating Professional PDF with Cover & Colophon...")

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
            print(f"✅ PDF Created: {output_path}")
        except Exception as e:
            self.logger.error(f"Failed to generate professional PDF: {e}", exc_info=True)
            # Fallback to simple image append if needed, but let's trust the new system

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
        except Exception:
            self.logger.warning(f"Could not read logo at {logo_path}")
            return None

    def download_native_pdf(self, pdf_url: str) -> bool:
        """Download a PDF advertised in the IIIF manifest rendering section."""
        try:
            with self.session.get(pdf_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with self.output_path.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            return True
        except (RequestException, OSError):
            self.logger.debug("Native PDF download failed", exc_info=True)
            return False

    def run(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ):
        """Execute the download workflow for the manifest.

        Args:
            progress_callback: Optional callable that receives (current, total)
                and will be invoked as pages are downloaded. If provided it
                overrides any instance-level `progress_callback` set at init.
        """
        self.extract_metadata()
        canvases = self.get_canvases()

        total_pages = len(canvases)
        # Register total pages upfront so the DB/UI can display a stable total
        self.vault.upsert_manuscript(self.ms_id, status="downloading", total_canvases=total_pages)

        if self.clean_cache:
            clean_dir(self.temp_dir)

        native_pdf_url = self.get_pdf_url()
        should_download_native_pdf = self._should_download_native_pdf()

        # Prefer runtime provided callback over instance attribute
        cb = progress_callback or self.progress_callback

        downloaded, page_stats = self._download_canvases(canvases, progress_callback=cb, should_cancel=should_cancel)
        self._store_page_stats(page_stats)

        valid = [f for f in downloaded if f]
        try:
            final_files = self._finalize_downloads(valid)
        except Exception as exc:
            self.vault.update_status(self.ms_id, "error", str(exc))
            raise

        if native_pdf_url and should_download_native_pdf:
            self.download_native_pdf(native_pdf_url)

        if should_download_native_pdf and final_files:
            self.create_pdf(files=final_files)

        if final_files and self.ocr_model:
            self.run_batch_ocr(final_files, self.ocr_model)

    def _should_download_native_pdf(self):
        try:
            cm = get_config_manager()
            return bool(cm.get_setting("defaults.auto_generate_pdf", True))
        except (OSError, ValueError, TypeError):
            return True

    def _download_canvases(
        self,
        canvases: list[dict[str, Any]],
        progress_callback: Optional[Callable[[int, int], None]] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ):
        downloaded: list[str | None] = [None] * len(canvases)
        page_stats = []
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_index = {
                executor.submit(self.download_page, canvas, i, self.temp_dir): i for i, canvas in enumerate(canvases)
            }
            for future in tqdm(as_completed(future_to_index), total=len(canvases)):
                idx = future_to_index[future]
                result = future.result()
                if result:
                    fname, stats = result
                    downloaded[idx] = fname
                    if stats:
                        page_stats.append(stats)
                if progress_callback:
                    completed = sum(1 for f in downloaded if f)
                    try:
                        progress_callback(completed, len(canvases))
                    except Exception:
                        # Never allow progress hooks to interrupt downloads
                        self.logger.debug("Progress callback raised an exception", exc_info=True)

                # Cooperative cancellation check
                if should_cancel and should_cancel():
                    completed = sum(1 for f in downloaded if f)
                    try:
                        self.vault.update_download_job(
                            self.ms_id,
                            current=completed,
                            total=len(canvases),
                            status="cancelled",
                            error="Cancelled by user",
                        )
                    except Exception:
                        self.logger.debug("Failed to mark job cancelled in DB", exc_info=True)
                    break
        return downloaded, page_stats

    def _store_page_stats(self, page_stats):
        if page_stats:
            page_stats.sort(key=lambda x: x.get("page_index", 0))
            save_json(self.stats_path, {"doc_id": self.ms_id, "pages": page_stats})

    def _finalize_downloads(self, valid):
        final_files = []
        for temp_file in valid:
            p = Path(temp_file)
            dest = self.scans_dir / p.name
            if not dest.exists():
                shutil.move(str(p), str(dest))
            else:
                # In case of partial resume or overwrite
                pass
            final_files.append(str(dest))
        self.vault.upsert_manuscript(self.ms_id, status="complete", downloaded_canvases=len(final_files))
        return final_files

    def run_batch_ocr(self, image_files: list[str], model_name: str):
        """Run OCR processing on the finalized image files."""
        from ..services.ocr.model_manager import ModelManager
        from ..services.ocr.processor import KRAKEN_AVAILABLE, OCRProcessor

        if not KRAKEN_AVAILABLE:
            return
        manager = ModelManager()
        model_path = manager.get_model_path(model_name)
        proc = OCRProcessor(model_path)
        aggregated = {
            "metadata": {
                "manuscript_id": self.ms_id,
                "model": self.ocr_model,
                "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "pages": [],
        }
        for i, img_path in enumerate(image_files):
            try:
                res = proc.process_image(img_path)
                if "error" not in res:
                    res["page_index"] = i + 1
                    aggregated["pages"].append(res)
            except Exception:
                self.logger.debug("OCR failed for %s", img_path, exc_info=True)
        save_json(self.ocr_path, aggregated)
