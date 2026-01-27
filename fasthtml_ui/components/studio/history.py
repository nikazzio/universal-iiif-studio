"""Studio History Tab Component."""

from datetime import datetime

from fasthtml.common import H3, Div, P, Span

from iiif_downloader.logger import get_logger
from iiif_downloader.ocr.storage import OCRStorage

logger = get_logger(__name__)


def history_tab_content(doc_id, page, library):
    """Show transcription save history for this page (page is 1-based)."""
    storage = OCRStorage()

    # page is 1-based from the URL, and we use it as-is for transcription/history keys
    page_idx = int(page)

    # Get transcription history from OCRStorage
    try:
        history_items = storage.load_history(doc_id, page_idx, library)
        # Sort by timestamp descending (newest first)
        history_items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    except Exception as e:
        logger.error(f"Error loading history: {e}")
        history_items = []

    if not history_items:
        return [P("Nessuno storico di salvataggio per questa pagina.", cls="text-gray-400 italic py-10 text-center")]

    cards = []
    for item in history_items:
        timestamp = item.get("timestamp", "N/A")
        text = item.get("full_text", "")
        engine = item.get("engine", "Manual")

        try:
            # Entry timestamp is YYYY-MM-DD HH:MM:SS
            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            time_str = dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            time_str = timestamp

        cards.append(
            Div(
                Div(
                    Span(time_str, cls="text-xs font-bold text-gray-600"),
                    Span(f"• {engine}", cls="text-xs text-gray-500 ml-2"),
                    cls="mb-2",
                ),
                P(
                    text[:200] + ("..." if len(text) > 200 else ""),
                    cls="text-sm text-gray-700 dark:text-gray-300 font-mono bg-gray-50 "
                    "dark:bg-gray-900 p-3 rounded border",
                ),
                cls="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 mb-3",
            )
        )

    return [
        Div(
            H3("Storico Salvataggi", cls="text-xs font-bold text-gray-400 uppercase mb-3"),
            Div(*cards, cls="space-y-2"),
            cls="p-4",
        )
    ]
