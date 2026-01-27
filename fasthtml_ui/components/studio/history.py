"""Studio History Tab Component."""

from datetime import datetime

from fasthtml.common import H3, Button, Div, Form, Input, P, Span

from iiif_downloader.logger import get_logger
from iiif_downloader.ocr.storage import OCRStorage
from iiif_downloader.utils import compute_text_diff_stats

logger = get_logger(__name__)


def _format_timestamp(timestamp: str) -> str:
    """Present a timestamp in dd/mm/YYYY HH:MM."""
    try:
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return timestamp


def history_tab_content(doc_id, page, library, info_message: str | None = None):
    """Show transcription save history for this page (page is 1-based)."""
    storage = OCRStorage()
    page_idx = int(page)

    try:
        history_items = storage.load_history(doc_id, page_idx, library)
        history_items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    except Exception as e:
        logger.error("History load failed for %s p%s: %s", doc_id, page_idx, e)
        history_items = []

    if not history_items:
        return [
            P(
                "Nessuno storico di salvataggio per questa pagina.",
                cls="text-gray-400 italic py-10 text-center",
            )
        ]

    cards = []
    for idx, entry in enumerate(history_items):
        timestamp = entry.get("timestamp", "N/A")
        text = entry.get("full_text", "") or ""
        engine = entry.get("engine", "Manual").capitalize()
        status = entry.get("status", "draft")
        prev_text = history_items[idx + 1].get("full_text", "") if idx + 1 < len(history_items) else ""
        diff = compute_text_diff_stats(prev_text, text)
        added = diff["added"]
        deleted = diff["deleted"]

        snippet = " ".join(text.strip().splitlines())
        snippet = snippet[:220] + ("..." if len(snippet) > 220 else "")

        info_badges = Div(
            Span(
                f"{len(text)} caratteri",
                cls="text-[10px] uppercase tracking-widest text-slate-500 dark:text-slate-400 font-semibold"
            ),
            Span(
                f"+{added}",
                cls="text-[10px] px-2 py-0.5 rounded-full bg-emerald-900/30 text-emerald-200 font-semibold tracking-wider",
            ),
            Span(
                f"-{deleted}",
                cls="text-[10px] px-2 py-0.5 rounded-full bg-rose-900/30 text-rose-200 font-semibold tracking-wider",
            ),
            cls="flex flex-wrap items-center gap-2 text-xs"
        )

        subtle_status = Span(
            status.upper(),
            cls="text-[10px] font-semibold tracking-wider px-2 py-0.5 rounded-full "
            f"{'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200' if status == 'verified' else 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-100'}"
        )

        restore_meta = None
        if entry.get("restored_from"):
            restore_meta = Span(
                f"Ripristinato da {entry['restored_from']}",
                cls="text-[10px] text-slate-500 dark:text-slate-400 italic",
            )

        cards.append(
            Div(
                Div(
                    Span(_format_timestamp(timestamp), cls="text-xs font-semibold text-slate-600 dark:text-slate-300"),
                    Span(f"• {engine}", cls="text-xs text-slate-500 dark:text-slate-300"),
                    subtle_status,
                    cls="flex flex-wrap items-center gap-2 mb-2",
                ),
                info_badges,
                P(
                    snippet,
                    cls="text-sm font-mono text-slate-700 dark:text-slate-200 bg-slate-50 dark:bg-slate-900/60 p-3 rounded-xl border border-slate-100 dark:border-slate-800 shadow-inner"
                ),
                *( [restore_meta] if restore_meta else [] ),
                Div(
                    Form(
                        Input(type="hidden", name="doc_id", value=doc_id),
                        Input(type="hidden", name="library", value=library),
                        Input(type="hidden", name="page", value=str(page_idx)),
                        Input(type="hidden", name="timestamp", value=timestamp),
                        Button(
                            "↺ Ripristina versione",
                            type="submit",
                            cls="text-[11px] font-bold uppercase tracking-[0.25em] px-3 py-1 rounded-full bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition",
                        ),
                        hx_post="/api/restore_transcription",
                        hx_target="#studio-right-panel",
                        hx_swap="outerHTML",
                        hx_confirm=(
                            "Ripristinare questa versione sovrascriverà la trascrizione corrente. Vuoi continuare?"
                        ),
                        cls="text-right",
                    ),
                    cls="mt-3",
                ),
                cls="relative bg-white dark:bg-gray-900/60 p-4 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-lg space-y-3",
            )
        )

    info_banner = None
    if info_message:
        info_banner = Div(
            Span(info_message, cls="text-[11px] font-semibold text-slate-50"),
            cls="mb-4 rounded-2xl border border-indigo-500/40 bg-indigo-900/70 px-4 py-2 shadow-lg text-sm",
        )

    return [
        Div(
            H3("Storico Salvataggi", cls="text-xs font-bold text-gray-400 uppercase mb-3"),
            *([info_banner] if info_banner else []),
            Div(*cards, cls="space-y-4"),
            cls="p-4",
        )
    ]
