"""Shared constants for library card and filter components."""

from __future__ import annotations

STATE_STYLE = {
    "saved": ("Remoto", "app-chip app-chip-neutral"),
    "queued": ("In coda", "app-chip app-chip-accent"),
    "downloading": ("Download attivo", "app-chip app-chip-primary"),
    "running": ("Download attivo", "app-chip app-chip-primary"),
    "partial": ("Locale parziale", "app-chip app-chip-warning"),
    "complete": ("Locale completo", "app-chip app-chip-success"),
    "error": ("Errore", "app-chip app-chip-danger"),
}

CATEGORY_LABELS = {
    "manoscritto": "Manoscritto",
    "libro a stampa": "Libro a stampa",
    "incunabolo": "Incunabolo",
    "periodico": "Periodico",
    "musica/spartito": "Musica/Spartito",
    "mappa/atlante": "Mappa/Atlante",
    "miscellanea": "Miscellanea",
    "non classificato": "Non classificato",
}

SORT_LABELS = {
    "priority": "Priorita operativa",
    "recent": "Aggiornati di recente",
    "title_az": "Titolo A-Z",
    "pages_desc": "Piu pagine",
}

ACTION_BUTTON_CLS = {
    "primary": "app-btn app-btn-primary",
    "success": "app-btn app-btn-primary",
    "accent": "app-btn app-btn-accent",
    "danger": "app-btn app-btn-danger app-btn-sm",
    "warning": "app-btn app-btn-accent app-btn-sm",
    "neutral": "app-btn app-btn-neutral",
    "info": "app-btn app-btn-info app-btn-sm",
    "auto": "app-btn app-btn-accent",
}

LINK_BUTTON_CLS = {
    "primary": "app-btn app-btn-primary",
    "neutral": "app-btn app-btn-neutral",
    "external": "app-btn app-btn-accent app-btn-sm",
    "muted": "app-btn app-btn-muted app-btn-sm",
}

LIBRARY_FILTER_KEYS = [
    "q",
    "state",
    "library_filter",
    "category",
    "mode",
    "view",
    "action_required",
    "sort_by",
]

CATEGORY_SELECT_TONE = {
    "manoscritto": ("bg-indigo-50 border-indigo-300 dark:bg-indigo-950/30 dark:border-indigo-800/70"),
    "libro a stampa": ("bg-emerald-50 border-emerald-300 dark:bg-emerald-950/30 dark:border-emerald-800/70"),
    "incunabolo": ("bg-amber-50 border-amber-300 dark:bg-amber-950/30 dark:border-amber-800/70"),
    "periodico": ("bg-sky-50 border-sky-300 dark:bg-sky-950/30 dark:border-sky-800/70"),
    "musica/spartito": ("bg-fuchsia-50 border-fuchsia-300 dark:bg-fuchsia-950/30 dark:border-fuchsia-800/70"),
    "mappa/atlante": ("bg-teal-50 border-teal-300 dark:bg-teal-950/30 dark:border-teal-800/70"),
    "miscellanea": ("bg-violet-50 border-violet-300 dark:bg-violet-950/30 dark:border-violet-800/70"),
    "non classificato": ("bg-slate-100 border-slate-300 dark:bg-slate-800/70 dark:border-slate-600"),
}


def to_optional_bool(value) -> bool | None:
    """Convert a value to an optional boolean."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n", ""}:
        return False
    return None
