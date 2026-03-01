"""Theme presets and color utilities shared across the UI."""

from __future__ import annotations

from typing import Any

DEFAULT_THEME_PRESET = "rosewater"

THEME_PRESETS: dict[str, dict[str, str]] = {
    "rosewater": {"label": "Rosewater", "primary": "#7B8CC7", "accent": "#E8A6B6"},
    "lavender-sky": {"label": "Lavender Sky", "primary": "#8C8FD8", "accent": "#F0B6C4"},
    "sage-sand": {"label": "Sage Sand", "primary": "#86A88D", "accent": "#D9BFA0"},
    "ocean-mist": {"label": "Ocean Mist", "primary": "#6F9FC7", "accent": "#E8B9A2"},
    "mint-blush": {"label": "Mint Blush", "primary": "#7FB4A8", "accent": "#F2B7BE"},
    "plum-cream": {"label": "Plum Cream", "primary": "#9A84B8", "accent": "#E9C9A7"},
    "ruby-haze": {"label": "Ruby Haze", "primary": "#B97A86", "accent": "#E9A0A8"},
    "azure-drift": {"label": "Azure Drift", "primary": "#6D90C8", "accent": "#9EC1EB"},
    "verdant-mist": {"label": "Verdant Mist", "primary": "#78A78D", "accent": "#A8D2BB"},
}


def normalize_hex(color: str | None, fallback: str) -> str:
    """Normalize a hex color to #RRGGBB with fallback."""
    raw = str(color or "").strip()
    if raw.startswith("#"):
        raw = raw[1:]
    if len(raw) == 3 and all(ch in "0123456789abcdefABCDEF" for ch in raw):
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6 or not all(ch in "0123456789abcdefABCDEF" for ch in raw):
        return fallback
    return f"#{raw.upper()}"


def parse_hex_rgb(color: str) -> tuple[int, int, int]:
    """Return (r, g, b) from a normalized #RRGGBB value."""
    normalized = normalize_hex(color, "#4F46E5").lstrip("#")
    return int(normalized[0:2], 16), int(normalized[2:4], 16), int(normalized[4:6], 16)


def mix_hex(color_a: str, color_b: str, ratio: float) -> str:
    """Mix two colors in hex space with ratio in [0, 1]."""
    ratio = max(0.0, min(1.0, ratio))
    a = parse_hex_rgb(color_a)
    b = parse_hex_rgb(color_b)
    mixed = (
        int(a[0] * (1.0 - ratio) + b[0] * ratio),
        int(a[1] * (1.0 - ratio) + b[1] * ratio),
        int(a[2] * (1.0 - ratio) + b[2] * ratio),
    )
    return f"#{mixed[0]:02X}{mixed[1]:02X}{mixed[2]:02X}"


def readable_ink(color: str) -> str:
    """Pick light/dark text color with good contrast over the given color."""
    r, g, b = parse_hex_rgb(color)
    luminance = (0.299 * r) + (0.587 * g) + (0.114 * b)
    return "#0F172A" if luminance >= 170 else "#F8FAFC"


def preset_options() -> list[tuple[str, str]]:
    """Return theme preset options for settings select controls."""
    return [(name, values["label"]) for name, values in THEME_PRESETS.items()]


def resolve_ui_theme(ui: dict[str, Any] | None) -> dict[str, str]:
    """Resolve effective UI theme from stored settings with safe fallbacks."""
    ui_data = ui if isinstance(ui, dict) else {}

    raw_preset = str(ui_data.get("theme_preset", DEFAULT_THEME_PRESET) or DEFAULT_THEME_PRESET)
    preset = raw_preset if raw_preset in THEME_PRESETS else DEFAULT_THEME_PRESET
    preset_def = THEME_PRESETS[preset]

    primary = normalize_hex(ui_data.get("theme_primary_color"), preset_def["primary"])
    accent = normalize_hex(ui_data.get("theme_accent_color") or ui_data.get("theme_color"), preset_def["accent"])
    return {"preset": preset, "primary": primary, "accent": accent}


def normalize_ui_theme_in_place(ui: dict[str, Any] | None) -> dict[str, str]:
    """Normalize and persist theme keys in-place, including legacy theme_color."""
    if not isinstance(ui, dict):
        return resolve_ui_theme({})
    resolved = resolve_ui_theme(ui)
    ui["theme_preset"] = resolved["preset"]
    ui["theme_primary_color"] = resolved["primary"]
    ui["theme_accent_color"] = resolved["accent"]
    ui["theme_color"] = resolved["accent"]  # legacy key used in older UI paths
    return resolved
