"""Shared image settings helpers used by runtime and settings UI."""

from __future__ import annotations

from typing import Any

IMAGE_STRATEGY_PRESETS: dict[str, list[str]] = {
    "balanced": ["3000", "1740", "max"],
    "quality_first": ["max", "3000", "1740"],
    "fast": ["1740", "1200", "max"],
    "archival": ["max"],
}

IMAGE_STRATEGY_MODE_ALIASES: dict[str, str] = {
    "standard": "balanced",
    "balanced": "balanced",
    "massima_qualita": "quality_first",
    "quality_first": "quality_first",
    "fast": "fast",
    "veloce": "fast",
    "archival": "archival",
    "solo_max": "archival",
    "custom": "custom",
    "personalizzata": "custom",
}

STITCH_MODE_VALUES: set[str] = {"auto_fallback", "direct_only", "stitch_only"}
IIIF_QUALITY_VALUES: tuple[str, ...] = ("default", "color", "gray", "bitonal", "native")


def normalize_strategy_values(raw: Any) -> list[str]:
    """Normalize a raw strategy payload into unique IIIF size tokens."""
    if isinstance(raw, str):
        candidates = [token.strip() for token in raw.split(",") if token.strip()]
    elif isinstance(raw, list):
        candidates = [str(item).strip() for item in raw if str(item).strip()]
    else:
        candidates = []

    out: list[str] = []
    seen: set[str] = set()
    for token in candidates:
        norm = token.lower()
        if norm == "max":
            value = "max"
        elif token.isdigit() and int(token) > 0:
            value = token
        else:
            continue
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def normalize_strategy_mode(raw: Any, default: str = "balanced") -> str:
    """Normalize aliases and unknown values to a canonical strategy mode."""
    candidate = str(raw or default).strip().lower()
    return IMAGE_STRATEGY_MODE_ALIASES.get(candidate, default)


def normalize_stitch_mode(raw: Any, default: str = "auto_fallback") -> str:
    """Normalize stitch fallback mode to one of the supported runtime values."""
    candidate = str(raw or default).strip().lower()
    return candidate if candidate in STITCH_MODE_VALUES else default


def normalize_iiif_quality(raw: Any, default: str = "default") -> str:
    """Normalize the IIIF quality segment used in generated image URLs."""
    candidate = str(raw or default).strip().lower()
    return candidate if candidate in IIIF_QUALITY_VALUES else default


def resolve_download_strategy(
    images_node: dict[str, Any] | None,
    *,
    force_max_resolution: bool = False,
) -> list[str]:
    """Resolve the effective direct-download strategy from an images settings node."""
    if force_max_resolution:
        return ["max"]

    images = images_node if isinstance(images_node, dict) else {}
    mode = normalize_strategy_mode(images.get("download_strategy_mode"), default="balanced")
    custom_values = normalize_strategy_values(images.get("download_strategy_custom", []))
    if mode in IMAGE_STRATEGY_PRESETS:
        return list(IMAGE_STRATEGY_PRESETS[mode])
    if custom_values:
        return custom_values

    legacy_values = normalize_strategy_values(images.get("download_strategy", []))
    return legacy_values or list(IMAGE_STRATEGY_PRESETS["balanced"])
