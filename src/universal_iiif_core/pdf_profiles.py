from __future__ import annotations

from copy import deepcopy
from typing import Any

from .config_manager import ConfigManager

DOC_OVERRIDE_KEY_TEMPLATE = "{library}::{doc_id}"

DEFAULT_PDF_PROFILES: dict[str, dict[str, Any]] = {
    "balanced": {
        "label": "Balanced",
        "compression": "Standard",
        "include_cover": True,
        "include_colophon": True,
        "image_source_mode": "local_balanced",
        "image_max_long_edge_px": 2600,
        "jpeg_quality": 82,
        "force_remote_refetch": False,
        "cleanup_temp_after_export": True,
        "max_parallel_page_fetch": 2,
    },
    "high_quality": {
        "label": "High Quality",
        "compression": "High-Res",
        "include_cover": True,
        "include_colophon": True,
        "image_source_mode": "local_highres",
        "image_max_long_edge_px": 3800,
        "jpeg_quality": 92,
        "force_remote_refetch": False,
        "cleanup_temp_after_export": True,
        "max_parallel_page_fetch": 2,
    },
    "archival_highres": {
        "label": "Archival High-Res",
        "compression": "High-Res",
        "include_cover": True,
        "include_colophon": True,
        "image_source_mode": "remote_highres_temp",
        "image_max_long_edge_px": 0,
        "jpeg_quality": 95,
        "force_remote_refetch": True,
        "cleanup_temp_after_export": True,
        "max_parallel_page_fetch": 1,
    },
    "lightweight": {
        "label": "Lightweight",
        "compression": "Light",
        "include_cover": False,
        "include_colophon": False,
        "image_source_mode": "local_balanced",
        "image_max_long_edge_px": 1500,
        "jpeg_quality": 65,
        "force_remote_refetch": False,
        "cleanup_temp_after_export": True,
        "max_parallel_page_fetch": 3,
    },
}


def _doc_override_key(doc_id: str, library: str) -> str:
    return DOC_OVERRIDE_KEY_TEMPLATE.format(library=str(library or "Unknown").strip(), doc_id=str(doc_id or "").strip())


def _normalize_profile(raw: dict[str, Any]) -> dict[str, Any]:
    base = deepcopy(DEFAULT_PDF_PROFILES["balanced"])
    for key, value in (raw or {}).items():
        base[key] = value

    compression = str(base.get("compression") or "Standard")
    if compression not in {"High-Res", "Standard", "Light"}:
        compression = "Standard"

    source_mode = str(base.get("image_source_mode") or "local_balanced")
    if source_mode not in {"local_balanced", "local_highres", "remote_highres_temp"}:
        source_mode = "local_balanced"

    try:
        max_edge = int(base.get("image_max_long_edge_px") or 0)
    except (TypeError, ValueError):
        max_edge = 0

    try:
        jpeg_quality = int(base.get("jpeg_quality") or 82)
    except (TypeError, ValueError):
        jpeg_quality = 82

    try:
        max_parallel = int(base.get("max_parallel_page_fetch") or 2)
    except (TypeError, ValueError):
        max_parallel = 2

    base["compression"] = compression
    base["image_source_mode"] = source_mode
    base["image_max_long_edge_px"] = max(0, max_edge)
    base["jpeg_quality"] = max(40, min(jpeg_quality, 100))
    base["max_parallel_page_fetch"] = max(1, min(max_parallel, 8))
    base["include_cover"] = bool(base.get("include_cover", True))
    base["include_colophon"] = bool(base.get("include_colophon", True))
    base["force_remote_refetch"] = bool(base.get("force_remote_refetch", False))
    base["cleanup_temp_after_export"] = bool(base.get("cleanup_temp_after_export", True))
    base["label"] = str(base.get("label") or "Custom")
    return base


def _profiles_root(cm: ConfigManager) -> dict[str, Any]:
    settings = cm.data.setdefault("settings", {})
    pdf = settings.setdefault("pdf", {})
    profiles = pdf.setdefault("profiles", {})

    if not isinstance(profiles.get("catalog"), dict):
        profiles["catalog"] = deepcopy(DEFAULT_PDF_PROFILES)
    if not isinstance(profiles.get("document_overrides"), dict):
        profiles["document_overrides"] = {}
    if str(profiles.get("default") or "").strip() == "":
        profiles["default"] = "balanced"
    return profiles


def list_profiles(cm: ConfigManager) -> dict[str, dict[str, Any]]:
    """Return normalized global PDF profiles catalog."""
    root = _profiles_root(cm)
    catalog = root.get("catalog") or {}
    out: dict[str, dict[str, Any]] = {}
    for name, payload in catalog.items():
        if not isinstance(payload, dict):
            continue
        out[str(name)] = _normalize_profile(payload)
    return out


def set_global_profile(cm: ConfigManager, name: str, payload: dict[str, Any]) -> None:
    """Create or update one global PDF profile entry."""
    profile_name = str(name or "").strip().lower()
    if not profile_name:
        raise ValueError("Nome profilo non valido")
    root = _profiles_root(cm)
    catalog = root.setdefault("catalog", {})
    normalized = _normalize_profile(payload)
    normalized["label"] = str(payload.get("label") or profile_name)
    catalog[profile_name] = normalized


def delete_global_profile(cm: ConfigManager, name: str) -> bool:
    """Delete one global profile and clean dependent references."""
    profile_name = str(name or "").strip().lower()
    if profile_name in {"", "balanced"}:
        return False
    root = _profiles_root(cm)
    catalog = root.setdefault("catalog", {})
    if profile_name not in catalog:
        return False
    del catalog[profile_name]

    overrides = root.setdefault("document_overrides", {})
    for key in list(overrides.keys()):
        value = overrides.get(key)
        if (isinstance(value, str) and value == profile_name) or (
            isinstance(value, dict) and str(value.get("profile") or "") == profile_name
        ):
            del overrides[key]

    if root.get("default") == profile_name:
        root["default"] = "balanced"
    return True


def set_document_override(
    cm: ConfigManager,
    *,
    doc_id: str,
    library: str,
    profile_name: str | None = None,
    custom_payload: dict[str, Any] | None = None,
) -> None:
    """Assign one document-specific profile reference or inline custom profile payload."""
    key = _doc_override_key(doc_id, library)
    if not key.strip() or key.endswith("::"):
        raise ValueError("Override documento non valido")

    root = _profiles_root(cm)
    overrides = root.setdefault("document_overrides", {})

    if custom_payload:
        overrides[key] = {"custom": _normalize_profile(custom_payload)}
        return

    name = str(profile_name or "").strip().lower()
    if not name:
        raise ValueError("Profilo override non valido")
    overrides[key] = {"profile": name}


def clear_document_override(cm: ConfigManager, *, doc_id: str, library: str) -> bool:
    """Remove per-document profile override."""
    key = _doc_override_key(doc_id, library)
    root = _profiles_root(cm)
    overrides = root.setdefault("document_overrides", {})
    if key not in overrides:
        return False
    del overrides[key]
    return True


def set_default_profile(cm: ConfigManager, name: str) -> None:
    """Set global default profile name, falling back to `balanced` if invalid."""
    root = _profiles_root(cm)
    catalog = root.setdefault("catalog", {})
    target = str(name or "").strip().lower()
    if target and target in catalog:
        root["default"] = target
        return
    root["default"] = "balanced"


def resolve_effective_profile(
    cm: ConfigManager,
    *,
    doc_id: str | None = None,
    library: str | None = None,
    selected_profile: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Resolve active profile for one export request."""
    root = _profiles_root(cm)
    catalog = list_profiles(cm)
    default_name = str(root.get("default") or "balanced").strip().lower() or "balanced"

    selected = str(selected_profile or "").strip().lower()
    if selected and selected in catalog:
        return selected, deepcopy(catalog[selected])

    if doc_id and library:
        key = _doc_override_key(doc_id, library)
        override = (root.get("document_overrides") or {}).get(key)
        if isinstance(override, dict):
            custom = override.get("custom")
            if isinstance(custom, dict):
                return f"doc-custom:{key}", _normalize_profile(custom)
            ref = str(override.get("profile") or "").strip().lower()
            if ref in catalog:
                return ref, deepcopy(catalog[ref])
        elif isinstance(override, str):
            ref = override.strip().lower()
            if ref in catalog:
                return ref, deepcopy(catalog[ref])

    if default_name in catalog:
        return default_name, deepcopy(catalog[default_name])
    return "balanced", deepcopy(catalog.get("balanced") or _normalize_profile({}))
