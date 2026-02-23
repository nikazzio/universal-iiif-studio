"""Shared utilities for rendering toast notifications in the FastHTML UI."""

from __future__ import annotations

from fasthtml.common import Button, Div, Span

from studio_ui.config import get_setting

_TONE_STYLES = {
    "success": (
        "bg-emerald-100/95 border border-emerald-300 text-emerald-950 shadow-emerald-500/20 "
        "dark:bg-emerald-900/90 dark:border-emerald-500/70 dark:text-emerald-50 dark:shadow-emerald-500/40"
    ),
    "info": (
        "bg-sky-100/95 border border-sky-300 text-sky-950 shadow-sky-500/20 "
        "dark:bg-sky-900/85 dark:border-sky-500/60 dark:text-sky-50 dark:shadow-sky-500/30"
    ),
    "danger": (
        "bg-rose-100/95 border border-rose-300 text-rose-950 shadow-rose-500/20 "
        "dark:bg-rose-900/90 dark:border-rose-500/70 dark:text-rose-50 dark:shadow-rose-500/40"
    ),
}
_ICONS = {"success": "✅", "info": "ℹ️", "danger": "⚠️"}
_MIN_TIMEOUT_MS = 1000
_MAX_TIMEOUT_MS = 15000


def _coerce_timeout_ms(duration_ms: int | None) -> int:
    """Return a bounded timeout used by the global toast animation manager."""
    configured = duration_ms if duration_ms is not None else get_setting("ui.toast_duration", 3000)
    try:
        timeout = int(configured)
    except (TypeError, ValueError):
        timeout = 3000
    return max(_MIN_TIMEOUT_MS, min(timeout, _MAX_TIMEOUT_MS))


def build_toast(message: str, tone: str = "info", duration_ms: int | None = None) -> Div:
    """Return an out-of-band toast fragment appended to the global holder."""
    tone_classes = _TONE_STYLES.get(tone, _TONE_STYLES["info"])
    timeout_ms = _coerce_timeout_ms(duration_ms)
    icon = _ICONS.get(tone, "ℹ️")
    safe_message = (message or "").strip() or "Operazione completata."
    return Div(
        Span(icon, cls="text-lg leading-none mt-0.5"),
        Div(safe_message, cls="text-sm font-semibold leading-snug"),
        Button(
            "✕",
            type="button",
            data_toast_close="true",
            cls=(
                "ml-3 inline-flex h-6 w-6 items-center justify-center rounded-full "
                "text-current/80 transition hover:bg-black/10 hover:text-current "
                "dark:hover:bg-white/10"
            ),
            aria_label="Chiudi notifica",
        ),
        role="status",
        aria_live="polite",
        data_toast_timeout=str(timeout_ms),
        data_toast_ready="false",
        hx_swap_oob="beforeend:#studio-toast-holder",
        cls=(
            "pointer-events-auto studio-toast-entry flex items-start gap-3 rounded-xl px-4 py-3 "
            "opacity-0 translate-y-2 scale-95 shadow-xl backdrop-blur-sm transition-all duration-300 " + tone_classes
        ),
    )
