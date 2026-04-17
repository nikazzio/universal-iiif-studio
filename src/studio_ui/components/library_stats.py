"""Library statistics panel component."""

from __future__ import annotations

import json
from collections import Counter
from contextlib import suppress
from pathlib import Path

from fasthtml.common import Div, P, Span

from universal_iiif_core.logger import get_logger

logger = get_logger(__name__)

_CARD_CLS = "rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 p-3"


def _format_bytes(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def _pct_str(part: int, total: int) -> str:
    if not total:
        return "—"
    return f"{round(100 * part / total)}%"


def _metric_card(label: str, value: str, sub: str = "") -> Div:
    children: list = [
        P(label, cls="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-1"),
        P(value, cls="text-xl font-bold text-slate-800 dark:text-slate-100"),
    ]
    if sub:
        children.append(P(sub, cls="text-xs text-slate-500 dark:text-slate-400 mt-0.5"))
    return Div(*children, cls=_CARD_CLS)


def _provider_bar_row(name: str, count: int, total: int) -> Div:
    pct = round(100 * count / total) if total else 0
    return Div(
        Span(name, cls="text-xs text-slate-600 dark:text-slate-300 w-28 truncate shrink-0"),
        Div(
            Div(cls="h-full rounded bg-indigo-400 dark:bg-indigo-500", style=f"width:{pct}%"),
            cls="flex-1 h-2 rounded bg-slate-200 dark:bg-slate-600 overflow-hidden",
        ),
        Span(str(count), cls="text-xs tabular-nums text-slate-500 dark:text-slate-400 ml-2 shrink-0"),
        cls="flex items-center gap-2",
    )


def _provider_bars(counts: dict[str, int], total: int) -> Div:
    top = sorted(counts.items(), key=lambda x: -x[1])[:8]
    return Div(
        *[_provider_bar_row(name, count, total) for name, count in top],
        cls="flex flex-col gap-1.5",
    )


def _read_transcription_file(tx_file: Path) -> list[dict] | None:
    try:
        data = json.loads(tx_file.read_text(encoding="utf-8"))
        return data.get("pages", [])
    except Exception:
        logger.debug("Skipping unreadable transcription file: %s", tx_file)
        return None


def _scan_transcriptions(manuscripts: list[dict]) -> tuple[int, int]:
    """Return (transcribed_pages, ocr_pages) by reading per-manuscript JSON files."""
    transcribed = 0
    ocr = 0
    for m in manuscripts:
        lp = m.get("local_path")
        if not lp:
            continue
        tx_file = Path(lp) / "data" / "transcription.json"
        if not tx_file.exists():
            continue
        pages = _read_transcription_file(tx_file)
        if pages is None:
            continue
        for page in pages:
            if page.get("full_text"):
                transcribed += 1
                if not page.get("is_manual"):
                    ocr += 1
    return transcribed, ocr


def _dir_size(path: Path) -> int:
    total = 0
    with suppress(OSError):
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total


def _scan_disk_usage(manuscripts: list[dict]) -> int:
    """Return total bytes used across all local manuscript directories."""
    total = 0
    seen: set[str] = set()
    for m in manuscripts:
        lp = m.get("local_path")
        if not lp or lp in seen:
            continue
        seen.add(lp)
        p = Path(lp)
        if p.exists():
            total += _dir_size(p)
    return total


def render_library_stats(manuscripts: list[dict]) -> Div:
    """Render the statistics panel for the Library view (loaded lazily via HTMX)."""
    total = len(manuscripts)
    total_canvases = sum(int(m.get("total_canvases") or 0) for m in manuscripts)
    downloaded = sum(int(m.get("downloaded_canvases") or 0) for m in manuscripts)
    provider_counts: Counter[str] = Counter(m.get("library") or "Unknown" for m in manuscripts)
    transcribed_pages, ocr_pages = _scan_transcriptions(manuscripts)
    disk_bytes = _scan_disk_usage(manuscripts)

    metrics = Div(
        _metric_card(
            "Pagine scaricate",
            f"{downloaded:,} / {total_canvases:,}",
            _pct_str(downloaded, total_canvases),
        ),
        _metric_card(
            "Pagine trascritte",
            f"{transcribed_pages:,}",
            _pct_str(transcribed_pages, total_canvases),
        ),
        _metric_card(
            "Pagine OCR",
            f"{ocr_pages:,}",
            _pct_str(ocr_pages, total_canvases),
        ),
        _metric_card("Spazio disco", _format_bytes(disk_bytes)),
        cls="grid grid-cols-2 lg:grid-cols-4 gap-3",
    )

    provider_panel = Div(
        P(
            "Distribuzione per biblioteca",
            cls="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2",
        ),
        _provider_bars(dict(provider_counts), total),
        cls=_CARD_CLS,
    )

    return Div(
        metrics,
        provider_panel if total else Div(),
        cls="flex flex-col gap-3 mb-5",
        id="library-stats-panel",
    )
