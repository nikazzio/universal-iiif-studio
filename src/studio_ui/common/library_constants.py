"""Shared constants for library card and filter components."""

from __future__ import annotations

STATE_STYLE = {
    "saved": ("Da scaricare", "app-chip app-chip-neutral"),
    "queued": ("In coda", "app-chip app-chip-accent"),
    "downloading": ("Download", "app-chip app-chip-primary"),
    "running": ("Download", "app-chip app-chip-primary"),
    "partial": ("Parziale", "app-chip app-chip-warning"),
    "complete": ("Completo", "app-chip app-chip-success"),
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
    "manoscritto": (
        "bg-indigo-50 border-indigo-300 text-indigo-700 dark:bg-indigo-500/20 "
        "dark:border-indigo-500/45 dark:text-indigo-200"
    ),
    "libro a stampa": (
        "bg-emerald-50 border-emerald-300 text-emerald-700 dark:bg-emerald-500/20 "
        "dark:border-emerald-500/45 dark:text-emerald-200"
    ),
    "incunabolo": (
        "bg-amber-50 border-amber-300 text-amber-700 dark:bg-amber-500/20 dark:border-amber-500/45 dark:text-amber-200"
    ),
    "periodico": ("bg-sky-50 border-sky-300 text-sky-700 dark:bg-sky-500/20 dark:border-sky-500/45 dark:text-sky-200"),
    "musica/spartito": (
        "bg-fuchsia-50 border-fuchsia-300 text-fuchsia-700 dark:bg-fuchsia-500/20 "
        "dark:border-fuchsia-500/45 dark:text-fuchsia-200"
    ),
    "mappa/atlante": (
        "bg-teal-50 border-teal-300 text-teal-700 dark:bg-teal-500/20 dark:border-teal-500/45 dark:text-teal-200"
    ),
    "miscellanea": (
        "bg-violet-50 border-violet-300 text-violet-700 dark:bg-violet-500/20 "
        "dark:border-violet-500/45 dark:text-violet-200"
    ),
    "non classificato": (
        "bg-slate-100 border-slate-300 text-slate-700 dark:bg-slate-700/35 dark:border-slate-600 dark:text-slate-200"
    ),
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
