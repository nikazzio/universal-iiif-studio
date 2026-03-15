"""Shared library options for Discovery and Settings UI."""

from __future__ import annotations

from universal_iiif_core.providers import normalize_provider_value, provider_library_options


def library_options() -> list[tuple[str, str]]:
    """Return available libraries as (label, value) pairs."""
    return provider_library_options()


def normalize_library_value(value: str | None, fallback: str = "Vaticana") -> str:
    """Normalize legacy library values to one of the select values."""
    return normalize_provider_value(value, fallback=fallback)
