from __future__ import annotations

import json
import shutil
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress
from pathlib import Path

from tqdm import tqdm

from ..utils import clean_dir, save_json
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
        total_for_progress=operation_total,
    )
    self._store_page_stats(page_stats)

    valid = [f for f in downloaded if f]
    try:
        final_files = [] if (should_cancel and should_cancel()) else self._finalize_downloads(valid)
    except Exception as exc:
        self.vault.update_status(self.ms_id, "error", str(exc))
        raise

    if self._should_create_pdf_from_images() and final_files and not selected_pages:
        self.create_pdf(files=final_files)

    if final_files and self.ocr_model:
        self.run_batch_ocr(final_files, self.ocr_model)
    self._sync_asset_state(total_pages)


def _download_canvases(
    self,
    canvas_plan: list[tuple[int, dict[str, object]]],
    progress_callback: Callable[[int, int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    total_for_progress: int = 0,
):
    downloaded, page_stats, to_download = self._prescan_canvases(canvas_plan)

    if progress_callback:
        try:
            completed = sum(1 for f in downloaded if f)
            progress_callback(completed, total_for_progress or len(canvas_plan))
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
    )
    return downloaded, page_stats


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
):
    """Download missing pages using ThreadPoolExecutor and update progress and stats."""
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
            _emit_canvas_progress(self, downloaded, total_canvases, progress_callback)

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
) -> None:
    if not progress_callback:
        return
    completed = sum(1 for f in downloaded if f)
    try:
        progress_callback(completed, total_canvases)
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
        page_stats.sort(key=lambda x: x.get("page_index", 0))
        save_json(self.stats_path, {"doc_id": self.ms_id, "pages": page_stats})


def _finalize_downloads(self, valid):
    _ = valid
    total_expected = int(getattr(self, "expected_total_canvases", 0) or getattr(self, "total_canvases", 0) or 0)
    known_pages = _known_page_numbers(self)
    expected_pages = set(range(1, total_expected + 1)) if total_expected > 0 else set()

    # Keep staged files in temp until the full manuscript is available.
    if total_expected > 0 and not expected_pages.issubset(known_pages):
        return []

    for staged_file in sorted(self.temp_dir.glob("pag_*.jpg")):
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

    return [str(path) for path in sorted(self.scans_dir.glob("pag_*.jpg"))]


def _sync_asset_state(self, total_expected: int) -> None:
    scans_pages = _page_numbers_in_dir(self.scans_dir)
    temp_pages = _page_numbers_in_dir(self.temp_dir)
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
    self.vault.upsert_manuscript(
        self.ms_id,
        status=state,
        asset_state=state,
        total_canvases=total_expected,
        downloaded_canvases=known_count,
        pdf_local_available=pdf_available,
        missing_pages_json=json.dumps(missing),
        last_sync_at=time.strftime("%Y-%m-%d %H:%M:%S"),
    )


def _page_numbers_in_dir(directory: Path) -> set[int]:
    pages: set[int] = set()
    if not directory.exists():
        return pages
    for image in directory.glob("pag_*.jpg"):
        stem = image.stem or ""
        try:
            pages.add(int(stem.split("_")[-1]) + 1)
        except ValueError:
            continue
    return pages


def _known_page_numbers(self) -> set[int]:
    return _page_numbers_in_dir(self.scans_dir) | _page_numbers_in_dir(self.temp_dir)


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
    cls._prescan_canvases = _prescan_canvases
    cls._download_missing_canvases = _download_missing_canvases
    cls._iter_download_futures = _iter_download_futures
    cls._store_page_stats = _store_page_stats
    cls._finalize_downloads = _finalize_downloads
    cls._sync_asset_state = _sync_asset_state
    cls.run_batch_ocr = run_batch_ocr
