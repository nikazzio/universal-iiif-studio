from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from secrets import SystemRandom
from typing import Any

import requests
from PIL import Image

from ..config_manager import get_config_manager
from ..iiif_tiles import stitch_iiif_tiles_to_jpeg
from ..library_catalog import parse_manifest_catalog
from ..logger import get_download_logger
from ..pdf_utils import convert_pdf_to_images  # noqa: F401 - preserved for monkeypatch compatibility in tests
from ..services.storage.vault_manager import VaultManager
from ..utils import DEFAULT_HEADERS, ensure_dir, get_json, save_json
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
        scans_dir = getattr(downloader, "scans_dir", downloader.temp_dir)
        self.final_filename = Path(scans_dir) / f"pag_{index:04d}.jpg"
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
        if bool(getattr(self.downloader, "force_max_resolution", False)):
            return ["max"]
        mode = str(self.cm.get_setting("images.download_strategy_mode", "custom") or "custom").strip().lower()
        preset_map = {
            "balanced": ["3000", "1740", "max"],
            "fast": ["1740", "1200", "max"],
            "quality_first": ["max", "3000", "1740"],
            "archival": ["max"],
        }
        if mode in preset_map:
            return preset_map[mode]

        custom_raw = self.cm.get_setting("images.download_strategy_custom", [])
        custom_values = self._normalize_strategy_values(custom_raw)
        if custom_values:
            return custom_values

        legacy_raw = self.cm.get_setting("images.download_strategy", ["3000", "1740", "max"])
        legacy_values = self._normalize_strategy_values(legacy_raw)
        return legacy_values or ["3000", "1740", "max"]

    @staticmethod
    def _normalize_strategy_values(raw: Any) -> list[str]:
        if isinstance(raw, str):
            candidates = [token.strip() for token in raw.split(",") if token.strip()]
        elif isinstance(raw, list):
            candidates = [str(item).strip() for item in raw if str(item).strip()]
        else:
            candidates = []

        out: list[str] = []
        seen: set[str] = set()
        for token in candidates:
            norm = token.lower()
            if norm == "max":
                value = "max"
            elif token.isdigit() and int(token) > 0:
                value = token
            else:
                continue

            if value in seen:
                continue
            out.append(value)
            seen.add(value)
        return out

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
        if not base_url:
            return None
        candidates = [self.final_filename, self.filename]
        for candidate in candidates:
            if not candidate.exists() or candidate.stat().st_size == 0:
                continue
            try:
                with Image.open(candidate) as img:
                    img.verify()

                with Image.open(candidate) as img:
                    width, height = img.size

                stats = {
                    "page_index": self.index,
                    "filename": candidate.name,
                    "original_url": f"{base_url} (cached)",
                    "thumbnail_url": self.downloader._get_thumbnail_url(self.canvas),
                    "size_bytes": candidate.stat().st_size,
                    "width": width,
                    "height": height,
                    "resolution_category": "High" if width > 2500 else "Medium",
                }
                self.downloader.logger.info(f"Resuming valid file: {candidate}")
                return str(candidate), stats
            except Exception as exc:
                self.downloader.logger.warning(
                    "Found corrupt file %s, re-downloading. Error: %s", candidate, exc, exc_info=True
                )
        return None

    def resume_cached(self) -> tuple[str, dict[str, Any]] | None:
        """Expose resume logic so callers can avoid a full download."""
        if bool(getattr(self.downloader, "force_redownload", False)):
            return None
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
        show_progress: bool = True,
        force_max_resolution: bool = False,
        force_redownload: bool = False,
        overwrite_existing_scans: bool = False,
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
        self.show_progress = show_progress
        self.force_max_resolution = bool(force_max_resolution)
        self.force_redownload = bool(force_redownload)
        self.overwrite_existing_scans = bool(overwrite_existing_scans)

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
        native_pdf_url = self.get_pdf_url()
        catalog = parse_manifest_catalog(self.manifest, self.manifest_url, self.ms_id, enrich_external_reference=False)
        try:
            self.vault.upsert_manuscript(
                self.ms_id,
                display_title=str(catalog.get("catalog_title") or self.label),  # Human-readable for UI
                title=str(self.label),  # Legacy compat
                catalog_title=str(catalog.get("catalog_title") or self.label),
                library=self.library,
                manifest_url=self.manifest_url,
                local_path=str(self.doc_dir),
                status="queued",
                asset_state="queued",
                has_native_pdf=1 if native_pdf_url else 0,
                pdf_local_available=1 if self.output_path.exists() else 0,
                shelfmark=str(catalog.get("shelfmark") or ""),
                date_label=str(catalog.get("date_label") or ""),
                language_label=str(catalog.get("language_label") or ""),
                source_detail_url=str(catalog.get("source_detail_url") or ""),
                reference_text=str(catalog.get("reference_text") or ""),
                item_type=str(catalog.get("item_type") or "non classificato"),
                item_type_source="auto",
                item_type_confidence=float(catalog.get("item_type_confidence") or 0.0),
                item_type_reason=str(catalog.get("item_type_reason") or ""),
                metadata_json=str(catalog.get("metadata_json") or "{}"),
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
            except (requests.RequestException, requests.Timeout):
                self.logger.debug("Unable to pre-warm Vatican viewer session", exc_info=True)
        elif "gallica.bnf.fr" in self.manifest_url.lower():
            viewer_url = self.manifest_url.replace("/iiif/ark:/12148/", "/ark:/12148/").replace("/manifest.json", "")
            try:
                self.session.get(viewer_url, timeout=20)
                self.session.headers.update(
                    {
                        "Referer": viewer_url,
                        "Origin": "https://gallica.bnf.fr",
                        "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    }
                )
            except (requests.RequestException, requests.Timeout):
                self.logger.debug("Unable to pre-warm Gallica viewer session", exc_info=True)

    def extract_metadata(self):
        """Extract and save basic metadata from the manifest."""
        catalog = parse_manifest_catalog(self.manifest, self.manifest_url, self.ms_id, enrich_external_reference=True)
        display_title = str(catalog.get("catalog_title") or self.label)
        metadata = {
            "id": self.ms_id,
            "title": display_title,
            "attribution": self.manifest.get("attribution"),
            "description": self.manifest.get("description"),
            "manifest_url": self.manifest_url,
            "download_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "shelfmark": catalog.get("shelfmark"),
            "date_label": catalog.get("date_label"),
            "language_label": catalog.get("language_label"),
            "source_detail_url": catalog.get("source_detail_url"),
            "reference_text": catalog.get("reference_text"),
            "item_type": catalog.get("item_type"),
            "item_type_confidence": catalog.get("item_type_confidence"),
            "item_type_reason": catalog.get("item_type_reason"),
            "metadata_map": catalog.get("metadata_map", {}),
        }
        save_json(self.meta_path, metadata)
        save_json(self.manifest_path, self.manifest)
        self.vault.upsert_manuscript(
            self.ms_id,
            display_title=display_title,
            title=str(self.label),
            catalog_title=display_title,
            shelfmark=str(catalog.get("shelfmark") or ""),
            date_label=str(catalog.get("date_label") or ""),
            language_label=str(catalog.get("language_label") or ""),
            source_detail_url=str(catalog.get("source_detail_url") or ""),
            reference_text=str(catalog.get("reference_text") or ""),
            item_type=str(catalog.get("item_type") or "non classificato"),
            item_type_source="auto",
            item_type_confidence=float(catalog.get("item_type_confidence") or 0.0),
            item_type_reason=str(catalog.get("item_type_reason") or ""),
            metadata_json=str(catalog.get("metadata_json") or "{}"),
        )

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
                    if r.status_code in {403, 429}:
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
            self.vault.upsert_manuscript(
                self.ms_id,
                status="error",
                asset_state="error",
                error_log=message,
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


from .downloader_pdf import attach_pdf_methods  # noqa: E402
from .downloader_runtime import attach_runtime_methods  # noqa: E402

attach_pdf_methods(IIIFDownloader)
attach_runtime_methods(IIIFDownloader)

__all__ = ["CanvasServiceLocator", "PageDownloader", "IIIFDownloader"]
