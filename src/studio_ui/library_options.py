"""Shared library options for Discovery and Settings UI."""

from __future__ import annotations

LIBRARY_OPTIONS: list[tuple[str, str]] = [
    ("Vaticana (BAV)", "Vaticana"),
    ("Gallica (BnF)", "Gallica"),
    ("Institut de France (Bibnum)", "Institut de France"),
    ("Bodleian (Oxford)", "Bodleian"),
    ("Altro / URL Diretto", "Unknown"),
]

_LIBRARY_ALIASES = {
    "vaticana (bav)": "Vaticana",
    "vaticana": "Vaticana",
    "gallica (bnf)": "Gallica",
    "gallica": "Gallica",
    "institut de france (bibnum)": "Institut de France",
    "institut de france": "Institut de France",
    "bodleian (oxford)": "Bodleian",
    "bodleian": "Bodleian",
    "unknown": "Unknown",
}


def library_options() -> list[tuple[str, str]]:
    """Return available libraries as (label, value) pairs."""
    return list(LIBRARY_OPTIONS)


def normalize_library_value(value: str | None, fallback: str = "Vaticana") -> str:
    """Normalize legacy library values to one of the select values."""
    text = str(value or "").strip()
    if text in {option_value for _, option_value in LIBRARY_OPTIONS}:
        return text
    return _LIBRARY_ALIASES.get(text.lower(), fallback)
