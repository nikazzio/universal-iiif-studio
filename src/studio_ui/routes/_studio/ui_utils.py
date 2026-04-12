"""Small UI helpers: toast wrappers, flag / int coercion."""

from __future__ import annotations

from fasthtml.common import Div

from studio_ui.common.toasts import build_toast


def _with_toast(fragment, message: str, tone: str = "info"):
    """Append a global toast to a standard fragment response."""
    return [fragment, build_toast(message, tone=tone)]


def _toast_only(message: str, tone: str = "info"):
    """Return a noop target payload plus a global toast for HTMX requests."""
    return _with_toast(Div("", cls="hidden"), message, tone=tone)


def _is_truthy_flag(raw: str | None) -> bool:
    value = str(raw or "").strip().lower()
    return value in {"1", "true", "on", "yes"}


def _as_int(raw: int | str | None, default: int = 0) -> int:
    try:
        return int(raw or default)
    except (TypeError, ValueError):
        return int(default)
