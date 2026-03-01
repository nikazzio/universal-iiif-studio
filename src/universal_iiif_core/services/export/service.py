from __future__ import annotations

import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.export_studio import build_professional_pdf, clean_filename
from universal_iiif_core.logger import get_logger
from universal_iiif_core.services.ocr.storage import OCRStorage
from universal_iiif_core.utils import load_json

logger = get_logger(__name__)


class ExportFeatureNotAvailableError(ValueError):
    """Raised when a requested export capability is declared but disabled."""


class ExportCancelledError(RuntimeError):
    """Raised when an export job is cancelled by the user."""


@dataclass(frozen=True)
class ExportFormatCapability:
    """One export format capability exposed to UI/API."""

    key: str
    label: str
    available: bool
    output_kind: str


@dataclass(frozen=True)
class ExportDestinationCapability:
    """One export destination capability exposed to UI/API."""

    key: str
    label: str
    available: bool


EXPORT_FORMATS: tuple[ExportFormatCapability, ...] = (
    ExportFormatCapability("pdf_images", "PDF (solo immagini)", True, "binary"),
    ExportFormatCapability("pdf_searchable", "PDF ricercabile", True, "binary"),
    ExportFormatCapability("pdf_facing", "PDF testo a fronte", True, "binary"),
    ExportFormatCapability("zip_images", "ZIP immagini", True, "bundle"),
    ExportFormatCapability("txt_transcription", "TXT trascrizione (in arrivo)", False, "text"),
    ExportFormatCapability("md_transcription", "Markdown trascrizione (in arrivo)", False, "text"),
)

EXPORT_DESTINATIONS: tuple[ExportDestinationCapability, ...] = (
    ExportDestinationCapability("local_filesystem", "File locale", True),
    ExportDestinationCapability("google_drive", "Google Drive (in arrivo)", False),
)


def get_export_capabilities() -> dict[str, list[dict[str, Any]]]:
    """Return available and planned capabilities for export UI/API."""
    return {
        "formats": [
            {
                "key": item.key,
                "label": item.label,
                "available": item.available,
                "output_kind": item.output_kind,
            }
            for item in EXPORT_FORMATS
        ],
        "destinations": [
            {
                "key": item.key,
                "label": item.label,
                "available": item.available,
            }
            for item in EXPORT_DESTINATIONS
        ],
    }


def is_format_available(export_format: str) -> bool:
    """Return `True` when the requested export format is enabled."""
    target = (export_format or "").strip().lower()
    for item in EXPORT_FORMATS:
        if item.key == target:
            return bool(item.available)
    return False


def is_destination_available(destination: str) -> bool:
    """Return `True` when the requested destination is enabled."""
    target = (destination or "").strip().lower()
    for item in EXPORT_DESTINATIONS:
        if item.key == target:
            return bool(item.available)
    return False


def output_kind_for_format(export_format: str) -> str:
    """Resolve output kind (`binary|bundle|text`) for one export format."""
    target = (export_format or "").strip().lower()
    for item in EXPORT_FORMATS:
        if item.key == target:
            return item.output_kind
    return "binary"


def parse_items_csv(items_csv: str) -> list[dict[str, str]]:
    """Parse `library::doc_id|library::doc_id` into normalized item dictionaries."""
    seen: set[tuple[str, str]] = set()
    parsed: list[dict[str, str]] = []
    for token in (items_csv or "").split("|"):
        raw = token.strip()
        if not raw or "::" not in raw:
            continue
        library, doc_id = raw.split("::", 1)
        lib = library.strip()
        doc = doc_id.strip()
        if not lib or not doc:
            continue
        key = (lib, doc)
        if key in seen:
            continue
        seen.add(key)
        parsed.append({"library": lib, "doc_id": doc})
    return parsed


def parse_page_selection(raw: str) -> list[int]:
    """Parse `1,3-5,9` into sorted unique page indexes (1-based)."""
    text = (raw or "").strip()
    if not text:
        return []

    pages: set[int] = set()
    for token in text.split(","):
        part = token.strip()
        if not part:
            continue
        if "-" not in part:
            pages.add(_parse_positive_int(part))
            continue

        left, right = [p.strip() for p in part.split("-", 1)]
        start = _parse_positive_int(left)
        end = _parse_positive_int(right)
        if end < start:
            start, end = end, start
        pages.update(range(start, end + 1))

    return sorted(pages)


def _parse_positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Pagina non valida: {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"Numero pagina non valido: {value}")
    return value


def _scan_available_pages(scans_dir: Path) -> list[int]:
    if not scans_dir.exists():
        return []
    pages: set[int] = set()
    for image_path in scans_dir.glob("pag_*.jpg"):
        stem = image_path.stem
        try:
            idx0 = int(stem.split("_")[-1])
        except ValueError:
            continue
        pages.add(idx0 + 1)
    return sorted(pages)


def resolve_selected_pages(scans_dir: Path, selection_mode: str, selected_pages_raw: str) -> list[int]:
    """Resolve selected pages according to mode and local scan availability."""
    available_pages = _scan_available_pages(scans_dir)
    if not available_pages:
        raise FileNotFoundError(f"Nessuna immagine trovata in {scans_dir}")

    mode = (selection_mode or "all").strip().lower()
    if mode == "all":
        return available_pages
    if mode != "custom":
        raise ValueError(f"Modalita selezione non supportata: {selection_mode!r}")

    requested_pages = parse_page_selection(selected_pages_raw)
    if not requested_pages:
        raise ValueError("Selezione pagine vuota: specifica almeno una pagina o un intervallo.")

    available_set = set(available_pages)
    missing = [page for page in requested_pages if page not in available_set]
    if missing:
        raise ValueError(f"Pagine non disponibili in locale: {missing}")
    return requested_pages


def _ensure_supported_target(export_format: str, destination: str) -> None:
    if not is_format_available(export_format):
        raise ExportFeatureNotAvailableError(f"Formato non disponibile in questa versione: {export_format}")
    if not is_destination_available(destination):
        raise ExportFeatureNotAvailableError(f"Destinazione non disponibile in questa versione: {destination}")


def _mode_for_pdf(export_format: str) -> str:
    mapping = {
        "pdf_images": "Solo immagini",
        "pdf_searchable": "PDF Ricercabile",
        "pdf_facing": "Testo a fronte",
    }
    return mapping.get(export_format, "Solo immagini")


def _zip_selected_images(scans_dir: Path, selected_pages: list[int], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for page_idx in selected_pages:
            image_name = f"pag_{page_idx - 1:04d}.jpg"
            image_path = scans_dir / image_name
            if not image_path.exists():
                logger.debug("Skipping missing scan while creating ZIP: %s", image_path)
                continue
            archive.write(image_path, arcname=image_name)
    return output_path


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _build_output_prefix(doc_id: str) -> str:
    return f"{clean_filename(doc_id)}_export"


def _load_cover_settings() -> tuple[str, str]:
    cfg = get_config_manager().get_setting("pdf.cover", {})
    if not isinstance(cfg, dict):
        return "", ""
    return str(cfg.get("curator") or ""), str(cfg.get("description") or "")


def _load_logo_bytes(logo_path: str) -> bytes | None:
    text = (logo_path or "").strip()
    if not text:
        return None
    candidate = Path(text).expanduser()
    if not candidate.exists() or not candidate.is_file():
        return None
    try:
        return candidate.read_bytes()
    except OSError:
        return None


def _pdf_output_path(doc_id: str, pdf_dir: Path, selection_mode: str, selected_pages: list[int]) -> Path:
    prefix = _build_output_prefix(doc_id)
    stamp = _timestamp()
    if selection_mode == "all" or not selected_pages:
        name = f"{prefix}_full_{stamp}.pdf"
    else:
        first = selected_pages[0]
        last = selected_pages[-1]
        if len(selected_pages) == (last - first + 1):
            sel = f"p{first}-{last}"
        else:
            sel = f"p{first}-{last}_n{len(selected_pages)}"
        name = f"{prefix}_{sel}_{stamp}.pdf"
    return pdf_dir / name


def list_item_pdf_files(doc_id: str, library: str) -> list[dict[str, Any]]:
    """List PDF files for one item with simple semantic classification."""
    storage = OCRStorage()
    paths = storage.get_document_paths(doc_id, library)
    pdf_dir = Path(paths["pdf_dir"])
    if not pdf_dir.exists():
        return []

    native_name = f"{doc_id}.pdf"
    compiled_name = f"{doc_id}_compiled.pdf"
    rows: list[dict[str, Any]] = []
    for pdf in sorted(pdf_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True):
        kind = "other"
        if pdf.name == native_name:
            kind = "native"
        elif pdf.name == compiled_name:
            kind = "compiled"
        elif "_export_" in pdf.stem:
            kind = "studio-export"

        stat = pdf.stat()
        rows.append(
            {
                "name": pdf.name,
                "path": str(pdf),
                "kind": kind,
                "size_bytes": int(stat.st_size),
                "modified_ts": float(stat.st_mtime),
            }
        )
    return rows


def _export_single_item_to_output(
    *,
    item: dict[str, str],
    export_format: str,
    selection_mode: str,
    selected_pages_raw: str,
    output_path: Path,
    compression: str,
    include_cover: bool,
    include_colophon: bool,
    cover_curator: str | None,
    cover_description: str | None,
    cover_logo_path: str | None,
) -> Path:
    doc_id = str(item.get("doc_id") or "").strip()
    library = str(item.get("library") or "").strip()
    if not doc_id or not library:
        raise ValueError("Item export non valido: doc_id/library mancanti")

    storage = OCRStorage()
    paths = storage.get_document_paths(doc_id, library)
    scans_dir = Path(paths["scans"])
    selected_pages = resolve_selected_pages(scans_dir, selection_mode, selected_pages_raw)

    if export_format == "zip_images":
        return _zip_selected_images(scans_dir, selected_pages, output_path)

    if export_format in {"pdf_images", "pdf_searchable", "pdf_facing"}:
        metadata = load_json(paths["metadata"]) or {}
        transcription = load_json(paths["transcription"]) or None

        default_curator, default_description = _load_cover_settings()
        curator = default_curator if cover_curator is None else str(cover_curator or "")
        description = default_description if cover_description is None else str(cover_description or "")
        logo_bytes = _load_logo_bytes(cover_logo_path or "")

        cover_title = str(metadata.get("title") or metadata.get("label") or doc_id)
        source_url = str(metadata.get("manifest") or metadata.get("manifest_url") or "")
        return build_professional_pdf(
            doc_dir=Path(paths["root"]),
            output_path=output_path,
            selected_pages=selected_pages,
            cover_title=cover_title,
            cover_curator=curator,
            cover_description=description,
            manifest_meta=metadata if isinstance(metadata, dict) else {},
            transcription_json=transcription if isinstance(transcription, dict) else None,
            mode=_mode_for_pdf(export_format),
            compression=compression,
            source_url=source_url,
            cover_logo_bytes=logo_bytes,
            include_cover=include_cover,
            include_colophon=include_colophon,
        )

    raise ExportFeatureNotAvailableError(f"Formato non implementato: {export_format}")


def execute_single_item_export(
    *,
    job_id: str,
    item: dict[str, str],
    export_format: str,
    selection_mode: str,
    selected_pages_raw: str,
    destination: str,
    compression: str = "Standard",
    include_cover: bool = True,
    include_colophon: bool = True,
    cover_curator: str | None = None,
    cover_description: str | None = None,
    cover_logo_path: str | None = None,
) -> Path:
    """Execute one single-item export and save PDFs under item `pdf/`."""
    _ensure_supported_target(export_format, destination)
    doc_id = str(item.get("doc_id") or "").strip()
    library = str(item.get("library") or "").strip()
    if not doc_id or not library:
        raise ValueError("Item export non valido: doc_id/library mancanti")

    storage = OCRStorage()
    paths = storage.get_document_paths(doc_id, library)
    pdf_dir = Path(paths["pdf_dir"])
    exports_dir = Path(paths["exports"])
    pdf_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    selected_pages = resolve_selected_pages(Path(paths["scans"]), selection_mode, selected_pages_raw)
    if export_format == "zip_images":
        output_path = exports_dir / f"{_build_output_prefix(doc_id)}_images_{_timestamp()}.zip"
    else:
        output_path = _pdf_output_path(doc_id, pdf_dir, selection_mode, selected_pages)

    return _export_single_item_to_output(
        item=item,
        export_format=export_format,
        selection_mode=selection_mode,
        selected_pages_raw=selected_pages_raw,
        output_path=output_path,
        compression=compression,
        include_cover=include_cover,
        include_colophon=include_colophon,
        cover_curator=cover_curator,
        cover_description=cover_description,
        cover_logo_path=cover_logo_path,
    )


def _bundle_outputs(outputs: list[Path], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for artifact in outputs:
            archive.write(artifact, arcname=artifact.name)
    return output_path


def _is_cancelled(should_cancel: Any) -> bool:
    try:
        return bool(should_cancel and should_cancel())
    except Exception:
        logger.debug("Cancellation callback failed", exc_info=True)
        return False


def _execute_single_item_job(
    *,
    job_id: str,
    item: dict[str, str],
    export_format: str,
    selection_mode: str,
    selected_pages_raw: str,
    destination: str,
    progress_callback: Any,
    compression: str,
    include_cover: bool,
    include_colophon: bool,
    cover_curator: str | None,
    cover_description: str | None,
    cover_logo_path: str | None,
) -> Path:
    if progress_callback:
        progress_callback(0, 1, "Preparing export")
    output = execute_single_item_export(
        job_id=job_id,
        item=item,
        export_format=export_format,
        selection_mode=selection_mode,
        selected_pages_raw=selected_pages_raw,
        destination=destination,
        compression=compression,
        include_cover=include_cover,
        include_colophon=include_colophon,
        cover_curator=cover_curator,
        cover_description=cover_description,
        cover_logo_path=cover_logo_path,
    )
    if progress_callback:
        progress_callback(1, 1, "Item 1/1 completato")
    return output


def _execute_batch_job(
    *,
    job_id: str,
    items: list[dict[str, str]],
    export_format: str,
    selection_mode: str,
    selected_pages_raw: str,
    should_cancel: Any,
    progress_callback: Any,
    compression: str,
    include_cover: bool,
    include_colophon: bool,
    cover_curator: str | None,
    cover_description: str | None,
    cover_logo_path: str | None,
) -> Path:
    out_dir = get_config_manager().get_exports_dir() / clean_filename(job_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    total_items = len(items)
    artifacts: list[Path] = []
    for idx, item in enumerate(items, start=1):
        if _is_cancelled(should_cancel):
            raise ExportCancelledError("Export annullato dall'utente.")
        if progress_callback:
            progress_callback(idx - 1, total_items, f"Export item {idx}/{total_items}")

        doc_id = str(item.get("doc_id") or f"item_{idx}")
        if export_format == "zip_images":
            output_path = out_dir / f"{clean_filename(doc_id)}_images_{_timestamp()}.zip"
        else:
            output_path = out_dir / f"{clean_filename(doc_id)}_export_{_timestamp()}.pdf"

        artifact = _export_single_item_to_output(
            item=item,
            export_format=export_format,
            selection_mode=selection_mode,
            selected_pages_raw=selected_pages_raw,
            output_path=output_path,
            compression=compression,
            include_cover=include_cover,
            include_colophon=include_colophon,
            cover_curator=cover_curator,
            cover_description=cover_description,
            cover_logo_path=cover_logo_path,
        )
        artifacts.append(artifact)

        if progress_callback:
            progress_callback(idx, total_items, f"Item {idx}/{total_items} completato")

    if not artifacts:
        raise RuntimeError("Nessun file prodotto dall'export.")
    bundle_name = f"export_batch_{clean_filename(job_id)}_{_timestamp()}.zip"
    return _bundle_outputs(artifacts, out_dir / bundle_name)


def execute_export_job(
    *,
    job_id: str,
    items: list[dict[str, str]],
    export_format: str,
    selection_mode: str,
    selected_pages_raw: str,
    destination: str,
    progress_callback: Any = None,
    should_cancel: Any = None,
    compression: str = "Standard",
    include_cover: bool = True,
    include_colophon: bool = True,
    cover_curator: str | None = None,
    cover_description: str | None = None,
    cover_logo_path: str | None = None,
) -> Path:
    """Execute one export job for one or multiple items and return final output path."""
    if not items:
        raise ValueError("Nessun item selezionato per export.")

    _ensure_supported_target(export_format, destination)

    if len(items) == 1:
        return _execute_single_item_job(
            job_id=job_id,
            item=items[0],
            export_format=export_format,
            selection_mode=selection_mode,
            selected_pages_raw=selected_pages_raw,
            destination=destination,
            progress_callback=progress_callback,
            compression=compression,
            include_cover=include_cover,
            include_colophon=include_colophon,
            cover_curator=cover_curator,
            cover_description=cover_description,
            cover_logo_path=cover_logo_path,
        )
    return _execute_batch_job(
        job_id=job_id,
        items=items,
        export_format=export_format,
        selection_mode=selection_mode,
        selected_pages_raw=selected_pages_raw,
        should_cancel=should_cancel,
        progress_callback=progress_callback,
        compression=compression,
        include_cover=include_cover,
        include_colophon=include_colophon,
        cover_curator=cover_curator,
        cover_description=cover_description,
        cover_logo_path=cover_logo_path,
    )
