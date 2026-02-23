from __future__ import annotations

import shutil
import time
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress
from pathlib import Path
from secrets import SystemRandom
from typing import Any

import requests
from PIL import Image
from requests import RequestException
from tqdm import tqdm

from ..config_manager import get_config_manager
from ..export_studio import build_professional_pdf
from ..iiif_tiles import stitch_iiif_tiles_to_jpeg
from ..logger import get_download_logger
from ..pdf_utils import convert_pdf_to_images
from ..services.storage.vault_manager import VaultManager
from ..utils import DEFAULT_HEADERS, clean_dir, ensure_dir, get_json, save_json
from .download_helpers import derive_identifier

# Constants
MAX_DOWNLOAD_RETRIES = 5
THROTTLE_BASE_WAIT = 15
VATICAN_MIN_DELAY = 1.5
VATICAN_MAX_DELAY = 4.0
NORMAL_MIN_DELAY = 0.4
NORMAL_MAX_DELAY = 1.2

SECURE_RANDOM = SystemRandom()


class CanvasServiceLocator:
    """Helper that locates the IIIF service URL nested inside a canvas."""

    _SEARCH_KEYS = ("body", "resource", "resources", "items", "images", "annotations", "target")

    @staticmethod
    def locate(canvas: Any) -> str | None:
        """Traverse canvas nodes to find a usable service base URL."""
        if not isinstance(canvas, dict):
            return None
        queue = deque([canvas])
        seen: set[int] = set()

        while queue:
            node = queue.popleft()
            if not isinstance(node, dict):
                continue
            node_id = id(node)
            if node_id in seen:
                continue
            seen.add(node_id)

            if service_url := CanvasServiceLocator._service_from_node(node):
                return service_url

            CanvasServiceLocator._enqueue_children(queue, node)

            if normalized := CanvasServiceLocator._normalize_candidate(node):
                return normalized

        return None

    @staticmethod
    def _service_from_node(node: dict[str, Any]) -> str | None:
        service = node.get("service")
        if not service:
            return None
        candidate = service[0] if isinstance(service, list) else service
        return (candidate or {}).get("@id") or (candidate or {}).get("id")

    @staticmethod
    def _enqueue_children(queue: deque, node: dict[str, Any]) -> None:
        for key in CanvasServiceLocator._SEARCH_KEYS:
            child = node.get(key)
            if isinstance(child, (list, tuple)):
                queue.extend(child)
            elif child:
                queue.append(child)

    @staticmethod
    def _normalize_candidate(node: dict[str, Any]) -> str | None:
        base_url = node.get("@id") or node.get("id")
        if isinstance(base_url, str) and "/full/" in base_url:
            return base_url.split("/full/")[0]
        return None


class PageDownloader:
    """Encapsulate the per-canvas download workflow."""

    def __init__(self, downloader: IIIFDownloader, canvas: dict[str, Any], index: int, folder: Path | str):
        """Initialize the helper with downloader context and canvas metadata."""
        self.downloader = downloader
        self.canvas = canvas
        self.index = index
        self.folder = Path(folder)
        self.filename = Path(downloader.temp_dir) / f"pag_{index:04d}.jpg"
        self.cm = downloader.cm
        self.base_url = CanvasServiceLocator.locate(canvas)

    def fetch(self) -> tuple[str, dict[str, Any]] | None:
        """Download (or resume) the requested canvas."""
        if not self.base_url:
            return None
        base_url = self.base_url

        if resumed := self.resume_cached():
            return resumed

        iiif_q = self.cm.get_setting("images.iiif_quality", "default")
        strategy = self._get_strategy()
        urls_to_try = [f"{base_url}/full/{self._format_dimension(s)}/0/{iiif_q}.jpg" for s in strategy]

        downloaded = self.downloader._download_with_retries(
            urls_to_try, self.filename, self.canvas, self.index, base_url
        )
        if downloaded:
            return downloaded

        return self.downloader._stitch_tiles_from_service(
            self.cm, self.filename, base_url, self.canvas, self.index, iiif_q
        )

    def _get_strategy(self) -> list[str]:
        raw = self.cm.get_setting("images.download_strategy", ["max", "3000", "1740"])
        return [str(item) for item in raw if item]

    @staticmethod
    def _format_dimension(value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            return "max"
        if cleaned.lower() == "max":
            return "max"
        if cleaned.endswith(","):
            cleaned = cleaned[:-1]
        if cleaned.isdigit():
            return f"{cleaned},0"
        return cleaned

    def _resume_existing_scan(self, base_url: str) -> tuple[str, dict[str, Any]] | None:
        if not self.filename.exists() or self.filename.stat().st_size == 0 or not base_url:
            return None
        try:
            with Image.open(self.filename) as img:
                img.verify()

            with Image.open(self.filename) as img:
                width, height = img.size

            stats = {
                "page_index": self.index,
                "filename": self.filename.name,
                "original_url": f"{base_url} (cached)",
                "thumbnail_url": self.downloader._get_thumbnail_url(self.canvas),
                "size_bytes": self.filename.stat().st_size,
                "width": width,
                "height": height,
                "resolution_category": "High" if width > 2500 else "Medium",
            }
            self.downloader.logger.info(f"Resuming valid file: {self.filename}")
            return str(self.filename), stats
        except Exception as exc:
            self.downloader.logger.warning(
                "Found corrupt file %s, re-downloading. Error: %s", self.filename, exc, exc_info=True
            )
            return None

    def resume_cached(self) -> tuple[str, dict[str, Any]] | None:
        """Expose resume logic so callers can avoid a full download."""
        if not self.base_url:
            return None
        return self._resume_existing_scan(self.base_url)


class IIIFDownloader:
    """Class to handle IIIF manifest downloading and processing."""

    def __init__(
        self,
        manifest_url: str,
        output_dir: str | Path | None = None,
        output_name: str | None = None,
        workers: int = 4,
        clean_cache: bool = False,
        prefer_images: bool = False,
        ocr_model: str | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
        output_folder_name: str | None = None,
        library: str = "Unknown",
        job_id: str | None = None,
    ):
        """Initialize the IIIFDownloader."""
        # basic configuration
        self.manifest_url = manifest_url
        self.workers = workers
        self.clean_cache = clean_cache
        self.prefer_images = prefer_images
        self.ocr_model: str | None = ocr_model
        self.progress_callback: Callable[[int, int], None] | None = progress_callback
        self.library = library
        self.job_id: str | None = job_id

        # load manifest and derive human label (for display, NOT for storage)
        self.manifest: dict[str, Any] = get_json(manifest_url) or {}
        self.label = self.manifest.get("label", "unknown_manuscript")
        if isinstance(self.label, list):
            self.label = self.label[0] if self.label else "unknown_manuscript"

        # Resolve where downloads live
        cm = get_config_manager()
        self.cm = cm
        out_base = self._resolve_out_base(output_dir, cm)

        # UNIFIED IDENTIFIER: same value for folder name, DB id, and internal reference
        # Priority: output_folder_name (from UI) > extracted from URL > sanitized label
        identifier = derive_identifier(self.manifest_url, output_folder_name, self.library, self.label)

        # ms_id = identifier (ATOMIC: folder = DB key = internal ID)
        self.ms_id = identifier
        self.logger = get_download_logger(self.ms_id)

        # Setup directory structure
        self.doc_dir = out_base / self.library / identifier
        self._ensure_dir_structure()

        # temp dir uses the unified identifier
        base_temp = cm.get_temp_dir()
        self.temp_dir = base_temp / self.ms_id
        ensure_dir(self.temp_dir)

        # db and session setup
        self.vault = VaultManager()
        self._register_vault()
        self._init_session()

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

    def _resolve_out_base(self, output_dir: str | Path | None, cm):
        """Return an absolute download base directory.

        Keeps logic isolated for easier testing.
        """
        if output_dir is None:
            return cm.get_downloads_dir()
        out_base = Path(output_dir).expanduser()
        if not out_base.is_absolute():
            out_base = (Path.cwd() / out_base).resolve()
        return out_base.resolve()

    def _ensure_dir_structure(self):
        """Create scans/pdf/data folders under `self.doc_dir` and set path attributes."""
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

    def _register_vault(self):
        try:
            self.vault.upsert_manuscript(
                self.ms_id,
                display_title=str(self.label),  # Human-readable for UI
                title=str(self.label),  # Legacy compat
                library=self.library,
                manifest_url=self.manifest_url,
                local_path=str(self.doc_dir),
                status="pending",
            )
        except Exception as e:
            with suppress(Exception):
                self.logger.warning(f"Failed to register manuscript in DB: {e}")

    def _init_session(self):
        import threading

        self._lock = threading.Lock()
        self._tile_stitch_sem = threading.Semaphore(1)
        self._backoff_until = 0
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

        # Pre-warm certain viewers (Vatican specific)
        if "vatlib.it" in self.manifest_url.lower():
            viewer_url = self.manifest_url.replace("/iiif/", "/view/").replace("/manifest.json", "")
            try:
                self.session.get(viewer_url, timeout=20)
                self.session.headers.update(
                    {"Referer": viewer_url, "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"}
                )
            except Exception:
                self.logger.debug("Unable to pre-warm Vatican viewer session", exc_info=True)

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
            return PageDownloader(self, canvas, index, folder).fetch()
        except Exception:
            self.logger.debug("Failed to download page %s", index, exc_info=True)
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
                    if r.status_code != 200:
                        self.logger.debug(
                            "Canvas %s returned status %s for %s: %s",
                            index,
                            r.status_code,
                            url,
                            r.text[:200],
                        )
                    if r.status_code == 429:
                        with self._lock:
                            wait = (2**attempt) * THROTTLE_BASE_WAIT
                            self._backoff_until = time.time() + wait
                        break
                except Exception as exc:
                    self.logger.debug("Download attempt failed for %s: %s", url, exc, exc_info=True)
                    continue
        if attempt == MAX_DOWNLOAD_RETRIES - 1:
            message = (
                f"Failed to download canvas {index} after {MAX_DOWNLOAD_RETRIES} attempts; URLs tried: {urls_to_try}"
            )
            self.logger.warning(message)
            self._mark_job_error(index, message)
        return None

    def _mark_job_error(self, current_index: int, message: str) -> None:
        if not self.job_id:
            return
        try:
            self.vault.update_download_job(
                job_id=self.job_id,
                current=current_index,
                total=self.total_canvases,
                status="error",
                error=message,
            )
        except Exception:
            self.logger.debug("Failed to mark job %s as error: %s", self.job_id, message, exc_info=True)

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
            # Allow small RAM caps for testing/low-memory environments while
            # still preventing absurd values. Lower bound relaxed from 1.0GB
            # to 0.1GB so users can request e.g. 0.5GB and trigger disk-backed
            # stitching behavior instead of forcing a larger in-memory canvas.
            max_ram_gb = max(0.1, min(max_ram_gb, 64.0))
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

    def _extract_pages_from_pdf(self, pdf_path: Path, progress_callback: Callable[[int, int], None] | None = None) -> bool:
        self._clear_existing_scans()
        viewer_dpi = int(self.cm.get_setting("pdf.viewer_dpi", 150) or 150)
        viewer_quality = int(self.cm.get_setting("images.viewer_quality", 90) or 90)
        ok, message = convert_pdf_to_images(
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
        self.vault.upsert_manuscript(self.ms_id, status="complete", downloaded_canvases=len(final_files))
        try:
            clean_dir(self.temp_dir)
        except Exception:
            self.logger.debug("Failed to clean temp dir %s", self.temp_dir, exc_info=True)

        if final_files and self.ocr_model:
            self.run_batch_ocr(final_files, self.ocr_model)
        return bool(final_files)

    def run(
        self,
        progress_callback: Callable[[int, int], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ):
        """Execute the download workflow for the manifest.

        Args:
            progress_callback: Optional callable that receives (current, total)
                and will be invoked as pages are downloaded. If provided it
                overrides any instance-level `progress_callback` set at init.
            should_cancel: Optional callable returning True to request cancellation.
                It is polled during the run; when True, the method should abort
                further processing and perform any necessary cleanup.
        """
        self.extract_metadata()
        canvases = self.get_canvases()

        total_pages = len(canvases)
        # Register total pages upfront so the DB/UI can display a stable total
        self.vault.upsert_manuscript(self.ms_id, status="downloading", total_canvases=total_pages)

        if self.clean_cache:
            clean_dir(self.temp_dir)

        # Prefer runtime provided callback over instance attribute
        cb = progress_callback or self.progress_callback

        native_pdf_url = self.get_pdf_url()
        should_prefer_native_pdf = self._should_prefer_native_pdf()
        if native_pdf_url and should_prefer_native_pdf:
            if self._try_native_pdf_flow(native_pdf_url, progress_callback=cb):
                return
        elif native_pdf_url and not should_prefer_native_pdf:
            self.logger.info("Native PDF found but preference disabled; proceeding canvas-by-canvas download.")
        else:
            self.logger.info("No native PDF rendering found; proceeding canvas-by-canvas download.")

        downloaded, page_stats = self._download_canvases(canvases, progress_callback=cb, should_cancel=should_cancel)
        self._store_page_stats(page_stats)

        valid = [f for f in downloaded if f]
        try:
            final_files = self._finalize_downloads(valid)
        except Exception as exc:
            self.vault.update_status(self.ms_id, "error", str(exc))
            raise

        if self._should_create_pdf_from_images() and final_files:
            self.create_pdf(files=final_files)

        if final_files and self.ocr_model:
            self.run_batch_ocr(final_files, self.ocr_model)

    def _download_canvases(
        self,
        canvases: list[dict[str, Any]],
        progress_callback: Callable[[int, int], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ):
        downloaded, page_stats, to_download = self._prescan_canvases(canvases)

        # Initial progress reflecting pre-existing files
        if progress_callback:
            try:
                completed = sum(1 for f in downloaded if f)
                progress_callback(completed, len(canvases))
            except Exception:
                self.logger.debug("Initial progress callback failed", exc_info=True)

        self.total_canvases = len(canvases)
        downloaded, page_stats = self._download_missing_canvases(
            to_download, downloaded, page_stats, progress_callback, should_cancel, len(canvases)
        )
        return downloaded, page_stats

    def _prescan_canvases(self, canvases: list[dict[str, Any]]):
        """Check temp dir for existing valid images and build download list."""
        downloaded: list[str | None] = [None] * len(canvases)
        page_stats: list[dict[str, Any]] = []
        to_download: list[tuple[int, dict[str, Any]]] = []
        for i, canvas in enumerate(canvases):
            downloader = PageDownloader(self, canvas, i, self.temp_dir)
            resumed = downloader.resume_cached()
            if resumed:
                fname, stats = resumed
                downloaded[i] = fname
                if stats:
                    page_stats.append(stats)
            else:
                to_download.append((i, canvas))
        return downloaded, page_stats, to_download

    def _download_missing_canvases(
        self,
        to_download: list[tuple[int, dict[str, Any]]],
        downloaded: list[str | None],
        page_stats: list[dict[str, Any]],
        progress_callback: Callable[[int, int], None] | None,
        should_cancel: Callable[[], bool] | None,
        total_canvases: int,
    ):
        """Download missing pages using ThreadPoolExecutor and update progress and stats."""
        if not to_download:
            return downloaded, page_stats

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_index = {
                executor.submit(self.download_page, canvas, i, self.temp_dir): i for i, canvas in to_download
            }
            for future in tqdm(as_completed(future_to_index), total=len(to_download)):
                idx = future_to_index[future]
                try:
                    result = future.result()
                except Exception:
                    result = None
                if result:
                    fname, stats = result
                    downloaded[idx] = fname
                    if stats:
                        page_stats.append(stats)

                if progress_callback:
                    completed = sum(1 for f in downloaded if f)
                    try:
                        progress_callback(completed, total_canvases)
                    except Exception:
                        self.logger.debug("Progress callback raised an exception", exc_info=True)

                if should_cancel and should_cancel():
                    completed = sum(1 for f in downloaded if f)
                    try:
                        self.vault.update_download_job(
                            self.ms_id,
                            current=completed,
                            total=total_canvases,
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
        # Clean up the temporary directory that held the downloaded images.
        # This removes the folder that contained the images (and any remaining files).
        try:
            clean_dir(self.temp_dir)
        except Exception:
            # Avoid raising during cleanup; log and continue.
            with suppress(Exception):
                self.logger.debug("Failed to clean temp dir %s", self.temp_dir, exc_info=True)

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
