"""Shared utilities for rendering toast notifications in the FastHTML UI."""

from __future__ import annotations

import re

from fasthtml.common import Button, Div, Span

from studio_ui.config import get_setting
from studio_ui.theme import resolve_ui_theme

_ICONS = {"success": "✅", "info": "ℹ️", "danger": "⚠️"}
_MIN_TIMEOUT_MS = 1000
_MAX_TIMEOUT_MS = 15000
_HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")

_TONE_ANCHORS = {
    "success": "#10b981",
    "info": "#0ea5e9",
    "danger": "#ef4444",
}


def _coerce_timeout_ms(duration_ms: int | None) -> int:
    """Return a bounded timeout used by the global toast animation manager."""
    configured = duration_ms if duration_ms is not None else get_setting("ui.toast_duration", 3000)
    try:
        timeout = int(configured)
    except (TypeError, ValueError):
        timeout = 3000
    return max(_MIN_TIMEOUT_MS, min(timeout, _MAX_TIMEOUT_MS))


def _normalize_hex(color: str | None, fallback: str = "#6366f1") -> str:
    """Return a normalized #RRGGBB value for CSS usage."""
    raw = str(color or "").strip()
    if not _HEX_RE.match(raw):
        return fallback
    return raw if raw.startswith("#") else f"#{raw}"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    value = _normalize_hex(hex_color).lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _mix_hex(color_a: str, color_b: str, ratio: float) -> str:
    """Mix two hex colors with ratio in [0, 1]."""
    ratio = max(0.0, min(1.0, ratio))
    a = _hex_to_rgb(color_a)
    b = _hex_to_rgb(color_b)
    mixed = (
        int(a[0] * (1.0 - ratio) + b[0] * ratio),
        int(a[1] * (1.0 - ratio) + b[1] * ratio),
        int(a[2] * (1.0 - ratio) + b[2] * ratio),
    )
    return f"#{mixed[0]:02x}{mixed[1]:02x}{mixed[2]:02x}"


def _rgba(hex_color: str, alpha: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"


def _toast_style(tone: str) -> str:
    """Inline style for reliable gradient/background rendering."""
    resolved_theme = resolve_ui_theme(
        {
            "theme_preset": get_setting("ui.theme_preset", ""),
            "theme_primary_color": get_setting("ui.theme_primary_color", ""),
            "theme_accent_color": get_setting("ui.theme_accent_color", ""),
            "theme_color": get_setting("ui.theme_color", ""),
        }
    )
    site_theme = _normalize_hex(resolved_theme["accent"])
    anchor = _normalize_hex(_TONE_ANCHORS.get(tone, _TONE_ANCHORS["info"]))
    start = _mix_hex(site_theme, anchor, 0.28 if tone == "info" else 0.48)
    end = _mix_hex(site_theme, "#0f172a", 0.62)
    edge = _mix_hex(anchor, "#ffffff", 0.22)
    shadow = _mix_hex(anchor, "#000000", 0.35)
    return (
        f"background: linear-gradient(135deg, {_rgba(start, 0.95)} 0%, {_rgba(end, 0.92)} 100%); "
        f"border: 1px solid {_rgba(edge, 0.55)}; "
        f"border-radius: 0.8rem; "
        f"box-shadow: 0 10px 28px {_rgba(shadow, 0.35)}; "
        "text-align: left; "
        "color: #f8fafc;"
    )


def build_toast(message: str, tone: str = "info", duration_ms: int | None = None) -> Div:
    """Return an out-of-band toast fragment appended to the global holder."""
    normalized_tone = tone if tone in _TONE_ANCHORS else "info"
    timeout_ms = _coerce_timeout_ms(duration_ms)
    icon = _ICONS.get(normalized_tone, "ℹ️")
    safe_message = (message or "").strip() or "Operazione completata."
    toast_style = (
        _toast_style(normalized_tone)
        + "transform-origin: top right; "
        + "opacity: 1; "
        + "transform: translateY(0) scale(1); "
    )
    toast_card = Div(
        Span(icon, cls="text-lg leading-none mt-0.5"),
        Div(safe_message, cls="text-sm font-semibold leading-snug text-left"),
        Button(
            "✕",
            type="button",
            cls=(
                "ml-3 inline-flex h-6 w-6 items-center justify-center rounded-full "
                "text-current/80 transition hover:bg-white/20 hover:text-current"
            ),
            aria_label="Chiudi notifica",
            **{"data-toast-close": "true"},
        ),
        role="status",
        aria_live="polite",
        style=toast_style,
        cls=(
            "pointer-events-auto studio-toast-entry w-full flex items-start gap-3 px-4 py-3 text-left "
            "backdrop-blur-sm transition-all duration-200 ease-out"
        ),
        **{"data-toast-timeout": str(timeout_ms)},
    )
    return Div(
        toast_card,
        hx_swap_oob="beforeend:#studio-toast-holder",
    )
