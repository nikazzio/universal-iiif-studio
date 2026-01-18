import random
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests import RequestException
from PIL import Image
from tqdm import tqdm

from iiif_downloader.config_manager import get_config_manager
from iiif_downloader.logger import get_download_logger
from iiif_downloader.iiif_tiles import stitch_iiif_tiles_to_jpeg
from iiif_downloader.utils import (
    DEFAULT_HEADERS,
    clean_dir,
    ensure_dir,
    get_json,
    save_json,
)

# Constants
MAX_DOWNLOAD_RETRIES = 5
THROTTLE_BASE_WAIT = 15
VATICAN_MIN_DELAY = 1.5
VATICAN_MAX_DELAY = 4.0
NORMAL_MIN_DELAY = 0.4
NORMAL_MAX_DELAY = 1.2

try:
    import img2pdf
    HAS_IMG2PDF = True
except ImportError:
    HAS_IMG2PDF = False


def _sanitize_filename(label: str) -> str:
    safe = "".join([c for c in str(label) if c.isalnum() or c in (" ", ".", "_", "-")])
    return safe.strip().replace(" ", "_")


class IIIFDownloader:
    # This module handles many network/image/PDF edge cases.
    # pylint: disable=broad-exception-caught
    def __init__(
        self,
        manifest_url,
        output_dir="downloads",
        output_name=None,
        workers=4,
        clean_cache=False,
        prefer_images=False,
        ocr_model=None,
        progress_callback=None,
        library="Unknown",
    ):
        self.manifest_url = manifest_url
        self.workers = workers
        self.clean_cache = clean_cache
        self.prefer_images = prefer_images
        self.ocr_model = ocr_model
        self.progress_callback = progress_callback
        self.library = library

        self.manifest = get_json(manifest_url)
        self.label = self.manifest.get("label", "unknown_manuscript")
        if isinstance(self.label, list):
            self.label = self.label[0] if self.label else "unknown_manuscript"

        sanitized_label = _sanitize_filename(str(self.label))

        ms_id = None
        if output_name:
            ms_id = output_name[:-4] if output_name.endswith(".pdf") else output_name
        else:
            ms_id = sanitized_label
        self.ms_id = ms_id
        self.logger = get_download_logger(self.ms_id)

        out_base = Path(output_dir).expanduser()
        if not out_base.is_absolute():
            out_base = (Path.cwd() / out_base).resolve()

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

        self.temp_dir = self.scans_dir

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
                    {"Referer": viewer_url, "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"})
            except Exception:
                self.logger.debug("Unable to pre-warm Vatican viewer session", exc_info=True)

    def get_pdf_url(self):
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
        sequences = self.manifest.get('sequences', [])
        if sequences:
            return sequences[0].get('canvases', [])
        items = self.manifest.get('items', [])
        if items:
            return items
        return []

    def download_page(self, canvas, index, folder):
        try:
            images = canvas.get('images') or canvas.get('items') or []
            if not images:
                return None
            img_obj = images[0]
            annotation_type = img_obj.get('@type') or img_obj.get('type') or ''
            if 'Annotation' in annotation_type:
                resource = img_obj.get('resource') or img_obj.get('body')
            else:
                resource = img_obj
            if not resource:
                return None

            service = resource.get('service')
            if isinstance(service, list):
                service = service[0]
            base_url = (service or {}).get('@id') or (service or {}).get('id')
            if not base_url:
                val = resource.get('@id') or resource.get('id') or ''
                base_url = val.split('/full/')[0] if '/full/' in val else val

            cm = get_config_manager()
            iiif_q = cm.get_setting("images.iiif_quality", "default")
            strategy = cm.get_setting("images.download_strategy", ["max", "3000", "1740"])
            urls_to_try = [f"{base_url}/full/{s},/0/{iiif_q}.jpg" for s in strategy]

            folder_p = Path(folder)
            filename = folder_p / f"pag_{index:04d}.jpg"

            for attempt in range(MAX_DOWNLOAD_RETRIES):
                now = time.time()
                if now < self._backoff_until:
                    time.sleep(self._backoff_until - now + random.uniform(0.1, 0.5))
                delay = random.uniform(VATICAN_MIN_DELAY, VATICAN_MAX_DELAY) if "vatlib.it" in self.manifest_url.lower(
                ) else random.uniform(NORMAL_MIN_DELAY, NORMAL_MAX_DELAY)
                time.sleep(delay)

                for url in urls_to_try:
                    try:
                        r = self.session.get(url, timeout=30)
                        if r.status_code == 200 and r.content:
                            with filename.open('wb') as f:
                                f.write(r.content)
                            with Image.open(str(filename)) as img:
                                width, height = img.size
                            thumb_url = None
                            thumbnail = canvas.get("thumbnail")
                            if thumbnail:
                                if isinstance(thumbnail, list):
                                    thumbnail = thumbnail[0]
                                thumb_url = thumbnail.get(
                                    "@id") or thumbnail.get("id") if isinstance(thumbnail, dict) else thumbnail
                            stats = {"page_index": index, "filename": filename.name, "original_url": url, "thumbnail_url": thumb_url, "size_bytes": len(
                                r.content), "width": width, "height": height, "resolution_category": "High" if width > 2500 else "Medium"}
                            return str(filename), stats
                        if r.status_code == 429:
                            with self._lock:
                                wait = (2 ** attempt) * THROTTLE_BASE_WAIT
                                self._backoff_until = time.time() + wait
                            break
                    except Exception:
                        continue
            # Fallback: tile stitching for servers that deny /full at large sizes.
            acquired = self._tile_stitch_sem.acquire(timeout=1)
            try:
                if acquired:
                    try:
                        max_ram_gb = float(cm.get_setting("images.tile_stitch_max_ram_gb", 2) or 2)
                    except (TypeError, ValueError):
                        max_ram_gb = 2.0
                    max_ram_gb = max(1.0, min(max_ram_gb, 64.0))
                    max_ram_bytes = int(max_ram_gb * (1024 ** 3))

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
                            "thumbnail_url": None,
                            "size_bytes": filename.stat().st_size if filename.exists() else None,
                            "width": width,
                            "height": height,
                            "resolution_category": "High" if width > 2500 else "Medium",
                        }
                        return str(filename), stats
            finally:
                if acquired:
                    self._tile_stitch_sem.release()

            return None
        except Exception:
            return None

    def create_pdf(self, files=None):
        """Explicitly generate a PDF from downloaded page images.

        This is intentionally NOT called by run(); PDF generation should be an
        explicit user action.
        """
        if files is None:
            files = sorted(
                [
                    str(p)
                    for p in self.scans_dir.iterdir()
                    if p.name.startswith("pag_") and p.suffix.lower() == ".jpg"
                ]
            )
        if not files:
            return

        output_path = self.output_path
        # Avoid overwriting a native PDF we may have downloaded.
        if Path(output_path).exists():
            output_path = self.pdf_dir / f"{self.ms_id}_from_images.pdf"

        if HAS_IMG2PDF:
            try:
                with Path(output_path).open("wb") as f:
                    f.write(img2pdf.convert(files))
                return
            except Exception:
                self.logger.debug("img2pdf failed; falling back to PIL PDF", exc_info=True)
        images = [Image.open(f).convert('RGB') for f in files]
        images[0].save(str(output_path), save_all=True, append_images=images[1:])

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

    def run(self):
        self.extract_metadata()
        if self.clean_cache:
            clean_dir(self.temp_dir)

        native_pdf = self.get_pdf_url()
        try:
            cm = get_config_manager()
            download_native_pdf = bool(cm.get_setting("defaults.auto_generate_pdf", True))
        except (OSError, ValueError, TypeError):
            download_native_pdf = True

        canvases = self.get_canvases()
        downloaded = [None] * len(canvases)
        page_stats = []
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_index = {
                executor.submit(
                    self.download_page,
                    canvas,
                    i,
                    self.temp_dir,
                ): i
                for i, canvas in enumerate(canvases)
            }
            for future in tqdm(as_completed(future_to_index), total=len(canvases)):
                idx = future_to_index[future]
                result = future.result()
                if result:
                    fname, stats = result
                    downloaded[idx] = fname
                    if stats:
                        page_stats.append(stats)
                if self.progress_callback:
                    self.progress_callback(len([f for f in downloaded if f]), len(canvases))
        if page_stats:
            page_stats.sort(key=lambda x: x.get("page_index", 0))
            save_json(self.stats_path, {"doc_id": self.ms_id, "pages": page_stats})
        valid = [f for f in downloaded if f]

        # Download the native PDF as an additional artifact when available.
        # Controlled by config and never replaces the image pipeline.
        if native_pdf and download_native_pdf:
            self.download_native_pdf(native_pdf)

        if valid and self.ocr_model:
            self.run_batch_ocr(valid)

    def run_batch_ocr(self, image_files):
        from iiif_downloader.ocr.processor import KRAKEN_AVAILABLE, OCRProcessor
        from iiif_downloader.ui.state import get_model_manager
        if not KRAKEN_AVAILABLE:
            return
        manager = get_model_manager()
        model_path = manager.get_model_path(self.ocr_model)
        proc = OCRProcessor(model_path)
        aggregated = {"metadata": {"manuscript_id": self.ms_id, "model": self.ocr_model,
                                   "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")}, "pages": []}
        for i, img_path in enumerate(image_files):
            try:
                res = proc.process_image(img_path)
                if "error" not in res:
                    res["page_index"] = i + 1
                    aggregated["pages"].append(res)
            except Exception:
                self.logger.debug("OCR failed for %s", img_path, exc_info=True)
        save_json(self.ocr_path, aggregated)
