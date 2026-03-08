"""Local scans optimization service used by Studio workflows."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.logger import get_logger
from universal_iiif_core.services.ocr.storage import OCRStorage
from universal_iiif_core.services.storage.vault_manager import VaultManager

logger = get_logger(__name__)


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _page_num_from_scan_name(name: str) -> int | None:
    if not name.startswith("pag_") or not name.endswith(".jpg"):
        return None
    raw = name[4:-4]
    try:
        return int(raw) + 1
    except (TypeError, ValueError):
        return None


def summarize_scan_folder(scans_dir: Path) -> dict[str, int]:
    """Return aggregate byte statistics for `scans/pag_*.jpg`."""
    sizes: list[int] = []
    for scan_path in sorted(scans_dir.glob("pag_*.jpg")):
        if not scan_path.is_file():
            continue
        try:
            sizes.append(int(scan_path.stat().st_size))
        except OSError:
            logger.debug("Unable to read file stats for %s", scan_path, exc_info=True)

    total = int(sum(sizes))
    files_count = int(len(sizes))
    return {
        "files_count": files_count,
        "bytes_total": total,
        "bytes_avg": int(total // files_count) if files_count > 0 else 0,
        "bytes_min": int(min(sizes)) if sizes else 0,
        "bytes_max": int(max(sizes)) if sizes else 0,
    }


def _optimize_scan_file(
    scan_path: Path,
    *,
    max_long_edge_px: int,
    jpeg_quality: int,
) -> tuple[int, int, tuple[int, int] | None, tuple[int, int] | None]:
    from PIL import Image

    before = int(scan_path.stat().st_size)
    before_dims: tuple[int, int] | None = None
    after_dims: tuple[int, int] | None = None
    tmp_out = scan_path.with_suffix(".tmp.jpg")
    with Image.open(scan_path) as img:
        rgb = img.convert("RGB")
        width, height = rgb.size
        before_dims = (int(width), int(height))
        long_edge = max(width, height)
        if long_edge > max_long_edge_px > 0:
            scale = max_long_edge_px / float(long_edge)
            target_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            rgb = rgb.resize(target_size, Image.Resampling.LANCZOS)
        after_dims = (int(rgb.size[0]), int(rgb.size[1]))
        rgb.save(tmp_out, format="JPEG", quality=jpeg_quality, optimize=True, progressive=True)
    tmp_out.replace(scan_path)
    after = int(scan_path.stat().st_size)
    return before, after, before_dims, after_dims


def optimize_local_scans(
    doc_id: str,
    library: str,
    *,
    target_pages: set[int] | None = None,
) -> dict[str, Any]:
    """Optimize local `scans/pag_*.jpg` for one document (optionally filtered by page ids)."""
    storage = OCRStorage()
    paths = storage.get_document_paths(doc_id, library)
    cm = get_config_manager()
    downloads_root = cm.get_downloads_dir().resolve()
    doc_root = Path(paths["root"]).resolve()
    try:
        doc_root.relative_to(downloads_root)
    except Exception:
        return {
            "ok": False,
            "tone": "danger",
            "message": "Percorso documento non valido.",
            "meta": {},
            "page_deltas": [],
            "scan_stats": {},
        }

    scans_dir = doc_root / "scans"
    if not scans_dir.exists():
        return {
            "ok": False,
            "tone": "info",
            "message": "Nessuna scansione locale disponibile da ottimizzare.",
            "meta": {},
            "page_deltas": [],
            "scan_stats": summarize_scan_folder(scans_dir),
        }

    max_long_edge_px = max(
        512,
        min(_safe_int(cm.get_setting("images.local_optimize.max_long_edge_px", 2600), 2600), 12000),
    )
    jpeg_quality = max(10, min(_safe_int(cm.get_setting("images.local_optimize.jpeg_quality", 82), 82), 100))

    requested_pages = {int(p) for p in (target_pages or set()) if int(p) > 0}

    optimized_pages = 0
    skipped_pages = 0
    errors = 0
    total_before = 0
    total_after = 0
    page_deltas: list[dict[str, Any]] = []

    for scan_path in sorted(scans_dir.glob("pag_*.jpg")):
        if not scan_path.is_file():
            continue
        page_num = _page_num_from_scan_name(scan_path.name)
        if requested_pages and (not page_num or int(page_num) not in requested_pages):
            skipped_pages += 1
            continue
        try:
            before, after, before_dims, after_dims = _optimize_scan_file(
                scan_path,
                max_long_edge_px=max_long_edge_px,
                jpeg_quality=jpeg_quality,
            )
            optimized_pages += 1
            total_before += before
            total_after += after
            page_deltas.append(
                {
                    "page": int(page_num or 0),
                    "status": "ok",
                    "before_bytes": int(before),
                    "after_bytes": int(after),
                    "bytes_saved": int(max(before - after, 0)),
                    "before_dims": list(before_dims) if before_dims else [],
                    "after_dims": list(after_dims) if after_dims else [],
                }
            )
        except Exception as exc:
            errors += 1
            page_deltas.append(
                {
                    "page": int(page_num or 0),
                    "status": "error",
                    "error": str(exc),
                }
            )
            logger.debug("Failed optimizing scan %s", scan_path, exc_info=True)

    thumb_dir = Path(paths["thumbnails"])
    if thumb_dir.exists():
        for thumb in thumb_dir.glob("*.jpg"):
            thumb.unlink(missing_ok=True)

    saved_bytes = max(total_before - total_after, 0)
    savings_percent = (float(saved_bytes) / float(total_before) * 100.0) if total_before > 0 else 0.0
    meta_payload = {
        "optimized_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "max_long_edge_px": int(max_long_edge_px),
        "jpeg_quality": int(jpeg_quality),
        "optimized_pages": int(optimized_pages),
        "skipped_pages": int(skipped_pages),
        "errors": int(errors),
        "bytes_before": int(total_before),
        "bytes_after": int(total_after),
        "bytes_saved": int(saved_bytes),
        "savings_percent": float(round(savings_percent, 2)),
        "page_deltas": page_deltas,
    }
    local_scan_files = [scan for scan in scans_dir.glob("pag_*.jpg") if scan.is_file()]
    has_local_scans = bool(local_scan_files)
    VaultManager().upsert_manuscript(
        doc_id,
        local_optimized=1 if optimized_pages > 0 else 0,
        local_optimization_meta_json=json.dumps(meta_payload, ensure_ascii=False),
        local_scans_available=1 if has_local_scans else 0,
        read_source_mode="local" if has_local_scans else "remote",
    )

    tone = "success" if optimized_pages > 0 and errors == 0 else "warning" if optimized_pages > 0 else "danger"
    scope_label = "selezionate" if requested_pages else "totali"
    message = (
        f"Ottimizzazione completata: {optimized_pages} pagine {scope_label}, risparmio {saved_bytes // 1024} KB."
        if optimized_pages > 0
        else "Ottimizzazione non completata: nessuna pagina valida aggiornata."
    )
    if errors > 0:
        message += f" Errori su {errors} file."

    return {
        "ok": optimized_pages > 0 and errors == 0,
        "tone": tone,
        "message": message,
        "meta": meta_payload,
        "page_deltas": page_deltas,
        "scan_stats": summarize_scan_folder(scans_dir),
    }
