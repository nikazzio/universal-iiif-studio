"""Library statistics components — sidebar widget and full stats page."""

from __future__ import annotations

import json
from collections import Counter
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path

from fasthtml.common import H2, A, Div, Li, P, Span, Ul

from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.logger import get_logger

logger = get_logger(__name__)

_CARD_CLS = "rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 p-4"
_SECTION_LABEL_CLS = "text-xs uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-3"
_STATE_ICON = {"complete": "✅", "partial": "🔶", "saved": "🔵", "downloading": "⏳", "error": "❌"}


# ── helpers ──────────────────────────────────────────────────────────────────


def _format_bytes(n: int) -> str:
    """Format byte count as human-readable string."""
    value = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def _pct_str(part: int, total: int) -> str:
    """Format part/total as percentage string."""
    if not total:
        return "—"
    return f"{round(100 * part / total)}%"


def _fmt_count(n: int) -> str:
    """Format large numbers as compact strings (8400 → 8.4k)."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def _time_ago(ts_str: str | None) -> str:
    """Return human-readable relative time from an ISO timestamp."""
    if not ts_str:
        return "—"
    try:
        dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
        # SQLite stores timestamps without tzinfo; treat naive values as UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        days = delta.days
        if days == 0:
            hours = delta.seconds // 3600
            return "poco fa" if hours == 0 else f"{hours}h fa"
        if days == 1:
            return "ieri"
        if days < 7:
            return f"{days}g fa"
        if days < 30:
            return f"{days // 7}sett fa"
        if days < 365:
            return f"{days // 30}m fa"
        return f"{days // 365}a fa"
    except Exception:
        return "—"


# ── file-scan helpers (slow — use only in lazy endpoints) ─────────────────────


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
    for f in path.rglob("*"):
        with suppress(OSError):
            if f.is_file():
                total += f.stat().st_size
    return total


def _scan_disk_usage(manuscripts: list[dict]) -> int:
    """Return total bytes used across all local manuscript directories."""
    downloads_root = get_config_manager().get_downloads_dir().resolve()
    total = 0
    seen: set[str] = set()
    for m in manuscripts:
        lp = m.get("local_path")
        if not lp or lp in seen:
            continue
        seen.add(lp)
        p = Path(lp).resolve()
        if not p.is_relative_to(downloads_root):
            logger.warning("Skipping local_path outside downloads dir: %s", lp)
            continue
        if p.exists():
            total += _dir_size(p)
    return total


# ── sidebar widget ─────────────────────────────────────────────────────────────


def render_sidebar_stats_widget(manuscripts: list[dict]) -> Div:
    """Render the compact nerd-stats widget for the sidebar footer (DB-only, fast)."""
    total = len(manuscripts)
    total_canvases = sum(int(m.get("total_canvases") or 0) for m in manuscripts)
    downloaded = sum(int(m.get("downloaded_canvases") or 0) for m in manuscripts)
    pct = round(100 * downloaded / total_canvases) if total_canvases else 0

    line1 = f"{total} mss · {_fmt_count(total_canvases)} pp"
    line2 = f"{pct}% locale"

    return Div(
        A(
            Div(
                Div(line1, cls="font-mono text-xs text-gray-400 leading-snug"),
                Div(line2, cls="font-mono text-xs text-gray-500 leading-snug"),
                cls="sidebar-label",
            ),
            href="/stats",
            hx_get="/stats",
            hx_target="#app-main",
            hx_swap="innerHTML",
            hx_push_url="true",
            cls="block hover:opacity-80 transition-opacity",
            title="Statistiche collezione",
        ),
        id="sidebar-stats-widget",
        cls="mb-3",
    )


# ── full stats page ────────────────────────────────────────────────────────────


def _metric_card(label: str, value: str, sub: str = "") -> Div:
    children: list = [
        P(label, cls="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-1"),
        P(value, cls="text-2xl font-bold font-mono text-slate-800 dark:text-slate-100"),
    ]
    if sub:
        children.append(P(sub, cls="text-xs text-slate-400 dark:text-slate-500 mt-1"))
    return Div(*children, cls=_CARD_CLS)


def _provider_bar_row(name: str, count: int, total: int) -> Div:
    pct = round(100 * count / total) if total else 0
    return Div(
        Span(name, cls="text-sm text-slate-600 dark:text-slate-300 w-40 truncate shrink-0"),
        Div(
            Div(cls="h-full rounded bg-indigo-400 dark:bg-indigo-500", style=f"width:{pct}%"),
            cls="flex-1 h-2.5 rounded bg-slate-200 dark:bg-slate-700 overflow-hidden",
        ),
        Span(str(count), cls="text-xs font-mono tabular-nums text-slate-500 dark:text-slate-400 ml-3 shrink-0"),
        cls="flex items-center gap-3",
    )


def _recent_activity_row(m: dict) -> Li:
    title = str(m.get("display_title") or m.get("catalog_title") or m.get("id") or "—")
    library = str(m.get("library") or "—")
    state = str(m.get("asset_state") or m.get("status") or "saved")
    icon = _STATE_ICON.get(state, "⚪")
    when = _time_ago(m.get("updated_at"))
    return Li(
        Span(icon, cls="shrink-0 text-base"),
        Div(
            Div(title, cls="text-sm text-slate-700 dark:text-slate-200 truncate"),
            Div(f"{library} · {when}", cls="text-xs text-slate-500 dark:text-slate-400"),
            cls="min-w-0",
        ),
        cls="flex items-start gap-2 py-1.5 border-b border-slate-100 dark:border-slate-800 last:border-0",
    )


def render_stats_page_content(manuscripts: list[dict]) -> Div:
    """Render the fast (DB-only) part of the stats page — shown immediately."""
    total = len(manuscripts)
    total_canvases = sum(int(m.get("total_canvases") or 0) for m in manuscripts)
    downloaded = sum(int(m.get("downloaded_canvases") or 0) for m in manuscripts)
    provider_counts: Counter[str] = Counter(m.get("library") or "Unknown" for m in manuscripts)

    fast_metrics = Div(
        _metric_card("Manoscritti", str(total)),
        _metric_card("Pagine totali", _fmt_count(total_canvases)),
        _metric_card("Pagine scaricate", _fmt_count(downloaded), _pct_str(downloaded, total_canvases)),
        cls="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6",
    )

    top = sorted(provider_counts.items(), key=lambda x: -x[1])[:10]
    provider_panel = Div(
        P("Distribuzione per biblioteca", cls=_SECTION_LABEL_CLS),
        Div(*[_provider_bar_row(n, c, total) for n, c in top], cls="flex flex-col gap-2"),
        cls=_CARD_CLS + " mb-6",
    )

    recent = manuscripts[:6]
    recent_panel = Div(
        P("Ultimi aggiornati", cls="text-xs uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-2"),
        Ul(*[_recent_activity_row(m) for m in recent], cls="divide-y divide-slate-100 dark:divide-slate-800"),
        cls=_CARD_CLS + " mb-6",
    ) if recent else Div()

    detail_placeholder = Div(
        id="stats-detail-panel",
        hx_get="/api/stats/detail",
        hx_trigger="load",
        hx_swap="outerHTML",
    )

    return Div(
        Div(
            H2("Statistiche Collezione", cls="text-2xl font-bold text-slate-800 dark:text-slate-100"),
            cls="mb-6",
        ),
        fast_metrics,
        detail_placeholder,
        provider_panel,
        recent_panel,
        cls="p-6 max-w-4xl mx-auto",
        id="stats-page",
    )


def render_library_stats(manuscripts: list[dict]) -> Div:
    """Render the detail metrics panel (slow — disk + transcription scan)."""
    total_canvases = sum(int(m.get("total_canvases") or 0) for m in manuscripts)
    transcribed_pages, ocr_pages = _scan_transcriptions(manuscripts)
    disk_bytes = _scan_disk_usage(manuscripts)

    return Div(
        _metric_card("Spazio disco", _format_bytes(disk_bytes)),
        _metric_card(
            "Pagine trascritte",
            _fmt_count(transcribed_pages),
            _pct_str(transcribed_pages, total_canvases),
        ),
        _metric_card(
            "Pagine OCR",
            _fmt_count(ocr_pages),
            _pct_str(ocr_pages, total_canvases),
        ),
        cls="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6",
        id="stats-detail-panel",
    )
