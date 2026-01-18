from __future__ import annotations

from typing import Optional, Union

import streamlit as st

from iiif_downloader.config_manager import get_config_manager


def _normalize_toast_duration(value: Union[int, str, None]) -> Union[int, str]:
    """Normalize config values for Streamlit `st.toast(duration=...)`.

    Streamlit accepts either:
    - int (milliseconds)
    - 'short' | 'long' | 'infinite'

    We treat small ints (<= 60) as seconds for human-friendliness.
    """

    if value is None:
        return 3000

    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"short", "long", "infinite"}:
            return v
        try:
            value = int(v)
        except ValueError:
            return 3000

    try:
        ms = int(value)
    except (TypeError, ValueError):
        return 3000

    if ms <= 60:
        ms *= 1000

    return max(250, min(ms, 60_000))


def toast(message: str, *, icon: Optional[str] = None, duration: Union[int, str, None] = None) -> None:
    cm = get_config_manager()
    default_duration = _normalize_toast_duration(cm.get_setting("ui.toast_duration", 3000))
    dur = _normalize_toast_duration(duration) if duration is not None else default_duration

    st.toast(message, icon=icon, duration=dur)
