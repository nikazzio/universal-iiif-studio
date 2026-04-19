from __future__ import annotations

import json
import shutil
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress
from pathlib import Path

from tqdm import tqdm

from ..utils import clean_dir, load_json, save_json
from .downloader import PageDownloader


def _build_canvas_plan(canvases: list[dict], target_pages: set[int] | None) -> tuple[set[int], list]:
    selected_pages = set(target_pages or set())
    plan: list[tuple[int, dict[str, object]]] = []
    for idx, canvas in enumerate(canvases):
        if selected_pages and (idx + 1) not in selected_pages:
            continue
        plan.append((idx, canvas))
    return selected_pages, plan


def _mark_downloading_state(self, total_pages: int) -> None:
    self.vault.upsert_manuscript(
        self.ms_id,
        status="downloading",
        asset_state="downloading",
        total_canvases=total_pages,
    )


def _maybe_run_native_pdf(
    self,
    native_pdf_url: str | None,
    selected_pages: set[int],
    progress_callback: Callable[[int, int], None] | None,
) -> bool:
    should_prefer_native_pdf = self._should_prefer_native_pdf()
    if native_pdf_url and should_prefer_native_pdf and not selected_pages:
        return self._try_native_pdf_flow(native_pdf_url, progress_callback=progress_callback)
    if native_pdf_url and not should_prefer_native_pdf:
        self.logger.info("Native PDF found but preference disabled; proceeding canvas-by-canvas download.")
    else:
        self.logger.info("No native PDF rendering found; proceeding canvas-by-canvas download.")
    return False


def run(
    self,
    progress_callback: Callable[[int, int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    target_pages: set[int] | None = None,
):
    """Execute the download workflow for the manifest."""
    self.extract_metadata()
    canvases = self.get_canvases()
    total_pages = len(canvases)
    self.expected_total_canvases = total_pages
    selected_pages, canvas_plan = self._build_canvas_plan(canvases, target_pages)
    operation_total = len(canvas_plan)
    if operation_total == 0:
        self._sync_asset_state(total_pages)
        return
    self._mark_downloading_state(total_pages)

    if self.clean_cache:
        clean_dir(self.temp_dir)

    cb = progress_callback or self.progress_callback

    if self._maybe_run_native_pdf(self.get_pdf_url(), selected_pages, cb):
        return

    downloaded, page_stats = self._download_canvases(
        canvas_plan,
        progress_callback=cb,
        should_cancel=should_cancel,
        total_for_progress=total_pages,
    )
    _raise_if_selected_direct_refresh_failed(
        self,
        selected_pages=selected_pages,
        page_stats=page_stats,
        should_cancel=should_cancel,
    )
    self._store_page_stats(page_stats)

    valid = [f for f in downloaded if f]
    try:
        final_files = self._finalize_downloads(valid)
    except Exception as exc:
        self.vault.update_status(self.ms_id, "error", str(exc))
        raise

    if self._should_create_pdf_from_images() and final_files and not selected_pages:
        self.create_pdf(files=final_files)

    if final_files and self.ocr_model:
        self.run_batch_ocr(final_files, self.ocr_model)
    self._sync_asset_state(total_pages)


def _raise_if_selected_direct_refresh_failed(
    self,
    *,
    selected_pages: set[int],
    page_stats: list[dict[str, object]],
    should_cancel: Callable[[], bool] | None,
) -> None:
    """Fail page-only direct refreshes when no selected page was actually replaced."""
    if not selected_pages:
        return
    if not bool(getattr(self, "force_redownload", False)):
        return
    if not bool(getattr(self, "overwrite_existing_scans", False)):
        return
    if str(getattr(self, "stitch_mode", "") or "").strip().lower() != "direct_only":
        return
    if should_cancel and should_cancel():
        return

    refreshed_pages: set[int] = set()
    for entry in page_stats:
        try:
            refreshed_pages.add(int(entry.get("page_index", -1)) + 1)
        except (AttributeError, TypeError, ValueError):
            continue

    missing = sorted(int(page) for page in selected_pages if int(page) not in refreshed_pages)
    if missing:
        raise RuntimeError(
            "Refresh diretto high-res fallito per le pagine selezionate: " + ", ".join(str(page) for page in missing)
        )


def _download_canvases(
    self,
    canvas_plan: list[tuple[int, dict[str, object]]],
    progress_callback: Callable[[int, int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    total_for_progress: int = 0,
):
    downloaded, page_stats, to_download = self._prescan_canvases(canvas_plan)

    # Calculate pages completed OUTSIDE the current canvas_plan to avoid double-counting
    # already_downloaded_count = all pages in scans/ + temp/
    # completed_in_current_plan = pages in canvas_plan that were resumed from cache
    # pages_outside_plan = pages not in current canvas_plan that are already done
    all_downloaded = self._count_all_downloaded_pages()
    completed_in_current_plan = sum(1 for f in downloaded if f)
    pages_outside_plan = max(0, all_downloaded - completed_in_current_plan)

    if progress_callback:
        try:
            initial_completed = pages_outside_plan + completed_in_current_plan
            progress_callback(initial_completed, total_for_progress or len(canvas_plan))
        except Exception:
            self.logger.debug("Initial progress callback failed", exc_info=True)

    self.total_canvases = total_for_progress or len(canvas_plan)
    downloaded, page_stats = self._download_missing_canvases(
        to_download,
        downloaded,
        page_stats,
        progress_callback,
        should_cancel,
        total_for_progress or len(canvas_plan),
        pages_outside_plan,  # Pass pages outside plan, not total
    )
    return downloaded, page_stats


def _count_all_downloaded_pages(self) -> int:
    """Count all downloaded pages (scans + temp) regardless of canvas_plan."""
    scans_pages = _page_numbers_in_dir(self.scans_dir)
    temp_pages = _page_numbers_in_dir(self.temp_dir)
    known_pages = scans_pages | temp_pages
    return len(known_pages)


def _prescan_canvases(self, canvas_plan: list[tuple[int, dict[str, object]]]):
    """Check temp dir for existing valid images and build download list."""
    downloaded: list[str | None] = [None] * len(canvas_plan)
    page_stats: list[dict[str, object]] = []
    to_download: list[tuple[int, int, dict[str, object]]] = []
    for local_idx, (canvas_idx, canvas) in enumerate(canvas_plan):
        downloader = PageDownloader(self, canvas, canvas_idx, self.temp_dir)
        resumed = downloader.resume_cached()
        if resumed:
            fname, stats = resumed
            downloaded[local_idx] = fname
            if stats:
                page_stats.append(stats)
        else:
            to_download.append((local_idx, canvas_idx, canvas))
    return downloaded, page_stats, to_download


def _download_missing_canvases(
    self,
    to_download: list[tuple[int, int, dict[str, object]]],
    downloaded: list[str | None],
    page_stats: list[dict[str, object]],
    progress_callback: Callable[[int, int], None] | None,
    should_cancel: Callable[[], bool] | None,
    total_canvases: int,
    pages_outside_plan: int = 0,
):
    """Download missing pages using ThreadPoolExecutor and update progress and stats.

    Args:
        self: Downloader instance
        to_download: List of (local_idx, canvas_idx, canvas) tuples to download
        downloaded: List tracking downloaded filenames (None if not yet downloaded)
        page_stats: List to accumulate page statistics
        progress_callback: Optional callback for progress updates (completed, total)
        should_cancel: Optional callable that returns True when download should stop
        total_canvases: Total number of canvases in the manuscript
        pages_outside_plan: Count of pages completed in previous runs that are NOT in current canvas_plan.
                           This is used to offset progress updates without double-counting resumed pages.
    """
    if not to_download:
        return downloaded, page_stats

    with ThreadPoolExecutor(max_workers=self.workers) as executor:
        future_to_index = {
            executor.submit(self.download_page, canvas, canvas_idx, self.temp_dir, should_cancel): local_idx
            for local_idx, canvas_idx, canvas in to_download
        }
        for future in self._iter_download_futures(future_to_index, len(to_download)):
            idx = future_to_index[future]
            _consume_download_future(future, idx, downloaded, page_stats)
            _emit_canvas_progress(self, downloaded, total_canvases, progress_callback, pages_outside_plan)

            if should_cancel and should_cancel():
                # Final state (paused vs cancelled) is determined by JobManager
                # based on pause/cancel flags, so avoid hardcoding "cancelled" here.
                _cancel_pending_futures(future_to_index, current=future)
                break

    return downloaded, page_stats


def _consume_download_future(
    future,
    idx: int,
    downloaded: list[str | None],
    page_stats: list[dict[str, object]],
) -> None:
    try:
        result = future.result()
    except Exception:
        result = None
    if not result:
        return
    fname, stats = result
    downloaded[idx] = fname
    if stats:
        page_stats.append(stats)


def _emit_canvas_progress(
    self,
    downloaded: list[str | None],
    total_canvases: int,
    progress_callback: Callable[[int, int], None] | None,
    pages_outside_plan: int = 0,
) -> None:
    """Emit progress update without double-counting.

    Args:
        self: Downloader instance
        downloaded: List of filenames for current canvas_plan (None if not yet downloaded)
        total_canvases: Total pages in the full manuscript
        progress_callback: Callback to report (completed, total)
        pages_outside_plan: Pages already completed that are NOT in current canvas_plan
    """
    if not progress_callback:
        return
    # Count completed in current canvas_plan
    completed_in_plan = sum(1 for f in downloaded if f)
    # Total = pages outside plan + pages completed in plan (no double-counting)
    total_completed = pages_outside_plan + completed_in_plan
    try:
        progress_callback(total_completed, total_canvases)
    except Exception:
        self.logger.debug("Progress callback raised an exception", exc_info=True)


def _cancel_pending_futures(future_to_index: dict, current) -> None:
    for pending in future_to_index:
        if pending is current:
            continue
        with suppress(Exception):
            pending.cancel()


def _iter_download_futures(self, future_to_index: dict, total_to_download: int):
    futures_iter = as_completed(future_to_index)
    if self.show_progress:
        return tqdm(futures_iter, total=total_to_download)
    return futures_iter


def _store_page_stats(self, page_stats):
    if page_stats:
        existing_pages = load_json(self.stats_path) or {}
        existing_by_page = {
            int(page.get("page_index")): dict(page)
            for page in (existing_pages.get("pages") or [])
            if isinstance(page, dict) and isinstance(page.get("page_index"), (int, float))
        }
        for page in page_stats:
            try:
                page_index = int(page.get("page_index", 0))
            except (TypeError, ValueError):
                continue
            existing_by_page[page_index] = dict(page)
        merged_pages = sorted(existing_by_page.values(), key=lambda x: x.get("page_index", 0))
        save_json(self.stats_path, {"doc_id": self.ms_id, "pages": merged_pages})


def _finalize_downloads(self, valid):
    validated_staged, validated_pages = _collect_validated_staged_files(self, valid)

    total_expected = int(getattr(self, "expected_total_canvases", 0) or getattr(self, "total_canvases", 0) or 0)
    known_pages = _page_numbers_in_dir(self.scans_dir) | validated_pages
    expected_pages = set(range(1, total_expected + 1)) if total_expected > 0 else set()
    allow_partial_overwrite = bool(getattr(self, "overwrite_existing_scans", False) and validated_pages)
    allow_partial_finalize = bool(getattr(self, "allow_partial_finalize", False) and validated_pages)

    # Keep staged files in temp until the full manuscript is available,
    # unless the provider is known to declare more pages than are served.
    if (
        total_expected > 0
        and not expected_pages.issubset(known_pages)
        and not allow_partial_overwrite
        and not allow_partial_finalize
    ):
        return []

    for staged_file in sorted(set(validated_staged)):
        dest = self.scans_dir / staged_file.name
        if not dest.exists():
            shutil.move(str(staged_file), str(dest))
            continue
        if self.overwrite_existing_scans:
            shutil.copy2(str(staged_file), str(dest))
        with suppress(OSError):
            staged_file.unlink()

    try:
        clean_dir(self.temp_dir)
    except OSError:
        with suppress(Exception):
            self.logger.debug("Failed to clean temp dir %s", self.temp_dir, exc_info=True)

    return _collect_finalized_scan_files(self, expected_pages=expected_pages, validated_pages=validated_pages)


def _collect_validated_staged_files(self, valid: list[str]) -> tuple[list[Path], set[int]]:
    validated_pages: set[int] = set()
    staged_by_name: dict[str, Path] = {}
    temp_root = self.temp_dir.resolve()

    for raw_path in valid:
        file_path = Path(raw_path)
        page_num = _page_number_from_filename(file_path.name)
        if page_num is None or not file_path.exists() or not _is_valid_image_file(file_path):
            continue
        validated_pages.add(page_num)
        with suppress(Exception):
            if file_path.resolve().is_relative_to(temp_root):
                staged_by_name[file_path.name] = file_path

    if self.temp_dir.exists():
        for staged_file in self.temp_dir.glob("pag_*.jpg"):
            page_num = _page_number_from_filename(staged_file.name)
            if page_num is None or not _is_valid_image_file(staged_file):
                continue
            validated_pages.add(page_num)
            staged_by_name.setdefault(staged_file.name, staged_file)

    return list(staged_by_name.values()), validated_pages


def _collect_finalized_scan_files(self, *, expected_pages: set[int], validated_pages: set[int]) -> list[str]:
    """Return only finalized files in scope for this manifest run.

    Scope priority:
    - expected manifest pages when known (`expected_pages`)
    - otherwise pages validated during this run (`validated_pages`)
    - finally fallback to all scan pages (legacy/defensive path)
    """
    scoped_pages = expected_pages or validated_pages or _page_numbers_in_dir(self.scans_dir)
    files: list[str] = []
    for page_num in sorted(scoped_pages):
        scan_path = self.scans_dir / f"pag_{page_num - 1:04d}.jpg"
        if scan_path.exists():
            files.append(str(scan_path))
    return files


def _is_valid_image_file(image_path: Path) -> bool:
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def _sync_asset_state(self, total_expected: int) -> None:
    scans_pages = _page_numbers_in_dir(self.scans_dir)
    temp_pages = _page_numbers_in_dir(self.temp_dir)
    scans_count = len(scans_pages)
    known_pages = scans_pages | temp_pages
    known_count = len(known_pages)
    pdf_available = 1 if any(self.pdf_dir.glob("*.pdf")) else 0
    if known_count <= 0 and total_expected > 0:
        state = "saved"
    elif total_expected <= 0 or known_count >= total_expected:
        state = "complete"
    else:
        state = "partial"
    missing = []
    if total_expected > 0 and known_count < total_expected:
        missing = [i for i in range(1, total_expected + 1) if i not in known_pages]
    manifest_path = getattr(self, "manifest_path", None)
    manifest_local_available = 0
    if isinstance(manifest_path, Path):
        manifest_local_available = 1 if manifest_path.exists() else 0
    elif manifest_path:
        try:
            manifest_local_available = 1 if Path(str(manifest_path)).exists() else 0
        except Exception:
            manifest_local_available = 0
    self.vault.upsert_manuscript(
        self.ms_id,
        status=state,
        asset_state=state,
        total_canvases=total_expected,
        downloaded_canvases=known_count,
        pdf_local_available=pdf_available,
        manifest_local_available=manifest_local_available,
        local_scans_available=1 if scans_count > 0 else 0,
        read_source_mode="local" if scans_count > 0 else "remote",
        missing_pages_json=json.dumps(missing),
        last_sync_at=time.strftime("%Y-%m-%d %H:%M:%S"),
    )


def _page_numbers_in_dir(directory: Path) -> set[int]:
    pages: set[int] = set()
    if not directory.exists():
        return pages
    for image in directory.glob("pag_*.jpg"):
        page_num = _page_number_from_filename(image.name)
        if page_num is not None:
            pages.add(page_num)
    return pages


def _page_number_from_filename(filename: str) -> int | None:
    stem = Path(filename).stem or ""
    try:
        return int(stem.split("_")[-1]) + 1
    except ValueError:
        return None


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


def attach_runtime_methods(cls) -> None:
    """Attach extracted runtime/pipeline methods to ``IIIFDownloader``."""
    cls._build_canvas_plan = staticmethod(_build_canvas_plan)
    cls._mark_downloading_state = _mark_downloading_state
    cls._maybe_run_native_pdf = _maybe_run_native_pdf
    cls.run = run
    cls._download_canvases = _download_canvases
    cls._count_all_downloaded_pages = _count_all_downloaded_pages
    cls._prescan_canvases = _prescan_canvases
    cls._download_missing_canvases = _download_missing_canvases
    cls._iter_download_futures = _iter_download_futures
    cls._store_page_stats = _store_page_stats
    cls._finalize_downloads = _finalize_downloads
    cls._sync_asset_state = _sync_asset_state
    cls.run_batch_ocr = run_batch_ocr
