import json
import re
from collections.abc import Iterable
from typing import Any

from fasthtml.common import Script

from studio_ui.common.toasts import build_toast
from studio_ui.components.layout import base_layout
from studio_ui.components.settings import settings_content
from studio_ui.theme import normalize_ui_theme_in_place
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.logger import get_logger, setup_logging

# Initialize logging
setup_logging()
logger = get_logger(__name__)

_UNPARSED = object()


def _safe_display(key: str | None, value: Any) -> str:
    """Return a log-safe representation for potentially sensitive values."""
    try:
        key_value = (key or "").lower()
        if any(secret_hint in key_value for secret_hint in ("key", "token", "secret", "password", "api")):
            return "<masked>"
    except Exception:
        logger.debug("Failed to evaluate key for masking: %s", key or "<unknown>", exc_info=True)

    if not isinstance(value, str):
        return repr(value)
    if len(value) > 120:
        return value[:117] + "..."
    return value


def _parse_json(raw: str) -> Any:
    """Try JSON parsing and return a sentinel on failure."""
    try:
        return json.loads(raw)
    except Exception:
        return _UNPARSED


def _parse_number(raw: str) -> Any:
    """Try numeric parsing and return a sentinel on failure."""
    try:
        return float(raw) if "." in raw else int(raw)
    except Exception:
        return _UNPARSED


def _parse_value(raw: str | None, key: str | None = None):
    """Try to coerce form string values into proper types.

    - Try JSON first (for arrays/objects)
    - Then booleans (1/0, true/false)
    - Then ints/floats
    - Then comma-separated lists
    - Otherwise return original string
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        return raw

    raw_value = raw.strip()
    if raw_value == "":
        return ""

    json_value = _parse_json(raw_value)
    if json_value is not _UNPARSED:
        return json_value

    lowered = raw_value.lower()
    if lowered in ("true", "false"):
        return lowered == "true"

    number_value = _parse_number(raw_value)
    if number_value is not _UNPARSED:
        return number_value

    if "," in raw_value:
        return [part.strip() for part in raw_value.split(",") if part.strip()]

    logger.debug(
        "Parsed value as string for key '%s'; original=%s",
        key or "<unknown>",
        _safe_display(key, raw_value),
    )
    return raw_value


def _deep_merge(dst: dict, src: dict) -> dict:
    for key, value in (src or {}).items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            _deep_merge(dst[key], value)
        else:
            dst[key] = value
    return dst


def _inflate_dotted_payload(form_items: Iterable[tuple[str, Any]]) -> dict:
    """Build nested payload from form entries using dotted keys."""
    payload: dict[str, Any] = {}
    for raw_key, raw_val in form_items:
        parsed = _parse_value(raw_val, raw_key)
        parts = [part for part in raw_key.split(".") if part]
        if not parts:
            continue
        node = payload
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = parsed
    return payload


def _payload_has(payload_dict: dict[str, Any], dotted_key: str) -> bool:
    """Check whether a nested dotted key exists in payload."""
    parts = [part for part in dotted_key.split(".") if part]
    node: Any = payload_dict
    for part in parts:
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


def _merge_payload_into_config(config_data: dict[str, Any], payload: dict[str, Any]) -> None:
    """Merge payload into config preserving nested structures."""
    for top_key, top_val in payload.items():
        if top_key in ("settings", "paths", "api_keys") and isinstance(top_val, dict):
            _deep_merge(config_data.setdefault(top_key, {}), top_val)
        else:
            config_data[top_key] = top_val


def _reconfigure_logging_after_save() -> None:
    """Safely reload logging settings after config persistence."""
    try:
        setup_logging()
        logger.info("Logging reconfigured after settings save")
    except Exception:
        logger.exception("Failed to reconfigure logging after settings save")


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "on"}


def _normalize_strategy_values(raw: Any) -> list[str]:
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


def _normalize_pdf_profile_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    compression = str(raw_payload.get("compression") or "Standard")
    if compression not in {"High-Res", "Standard", "Light"}:
        compression = "Standard"

    source_mode = str(raw_payload.get("image_source_mode") or "local_balanced")
    if source_mode not in {"local_balanced", "local_highres", "remote_highres_temp"}:
        source_mode = "local_balanced"

    try:
        max_edge = int(raw_payload.get("image_max_long_edge_px") or 0)
    except (TypeError, ValueError):
        max_edge = 0
    try:
        jpeg_quality = int(raw_payload.get("jpeg_quality") or 82)
    except (TypeError, ValueError):
        jpeg_quality = 82
    try:
        max_parallel = int(raw_payload.get("max_parallel_page_fetch") or 2)
    except (TypeError, ValueError):
        max_parallel = 2

    return {
        "label": str(raw_payload.get("label") or "Custom"),
        "compression": compression,
        "include_cover": bool(raw_payload.get("include_cover", True)),
        "include_colophon": bool(raw_payload.get("include_colophon", True)),
        "image_source_mode": source_mode,
        "image_max_long_edge_px": max(0, max_edge),
        "jpeg_quality": max(40, min(jpeg_quality, 100)),
        "force_remote_refetch": bool(raw_payload.get("force_remote_refetch", False)),
        "cleanup_temp_after_export": bool(raw_payload.get("cleanup_temp_after_export", True)),
        "max_parallel_page_fetch": max(1, min(max_parallel, 8)),
    }


def _postprocess_images_settings(settings_node: dict[str, Any]) -> None:
    images = settings_node.setdefault("images", {})
    if not isinstance(images, dict):
        settings_node["images"] = {}
        images = settings_node["images"]

    preset_map = {
        "balanced": ["3000", "1740", "max"],
        "quality_first": ["max", "3000", "1740"],
        "fast": ["1740", "1200", "max"],
        "archival": ["max"],
    }
    requested_mode = str(images.get("download_strategy_mode") or "balanced").strip().lower()
    mode = requested_mode if requested_mode in {*preset_map.keys(), "custom"} else "balanced"
    images["download_strategy_mode"] = mode

    custom_values = _normalize_strategy_values(images.get("download_strategy_custom", []))
    legacy_values = _normalize_strategy_values(images.get("download_strategy", []))
    if not custom_values:
        custom_values = legacy_values or preset_map["balanced"]
    images["download_strategy_custom"] = custom_values

    images["download_strategy"] = preset_map.get(mode, custom_values)

    if "probe_remote_max_resolution" not in images:
        images["probe_remote_max_resolution"] = True


def _sanitize_profile_key(raw: Any) -> str:
    text = str(raw or "").strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def _ensure_pdf_profiles_catalog(settings_node: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    pdf = settings_node.setdefault("pdf", {})
    if not isinstance(pdf, dict):
        settings_node["pdf"] = {}
        pdf = settings_node["pdf"]

    profiles = pdf.setdefault("profiles", {})
    if not isinstance(profiles, dict):
        pdf["profiles"] = {}
        profiles = pdf["profiles"]

    catalog = profiles.setdefault("catalog", {})
    if not isinstance(catalog, dict):
        profiles["catalog"] = {}
        catalog = profiles["catalog"]
    return profiles, catalog


def _normalize_pdf_catalog(catalog: dict[str, Any]) -> None:
    if "balanced" not in catalog or not isinstance(catalog.get("balanced"), dict):
        catalog["balanced"] = _normalize_pdf_profile_payload({"label": "Balanced"})

    for key in list(catalog.keys()):
        payload = catalog.get(key)
        if not isinstance(payload, dict):
            del catalog[key]
            continue
        catalog[key] = _normalize_pdf_profile_payload(payload)


def _apply_profile_deletions(*, profiles: dict[str, Any], catalog: dict[str, Any]) -> bool:
    delete_map = profiles.pop("delete", {})
    if not isinstance(delete_map, dict):
        return False
    changed = False
    for raw_key, raw_value in delete_map.items():
        target = _sanitize_profile_key(raw_key)
        if target in {"", "balanced"}:
            continue
        if _is_truthy(raw_value) and target in catalog:
            catalog.pop(target, None)
            changed = True
    return changed


def _apply_new_profile(*, profiles: dict[str, Any], catalog: dict[str, Any]) -> bool:
    new_profile = profiles.pop("new_profile", {})
    if not (isinstance(new_profile, dict) and _is_truthy(new_profile.get("create"))):
        return False

    target_key = _sanitize_profile_key(new_profile.get("key"))
    if not target_key:
        return False

    payload = _normalize_pdf_profile_payload(new_profile)
    payload["label"] = str(new_profile.get("label") or target_key)
    changed = catalog.get(target_key) != payload
    catalog[target_key] = payload
    if _is_truthy(new_profile.get("make_default")):
        profiles["default"] = target_key
        changed = True
    return changed


def _apply_profile_editor_action(*, profiles: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    editor = profiles.pop("editor", {})
    if not isinstance(editor, dict):
        return {"changed": False, "reload": False, "message": None}

    action = str(editor.get("action") or "none").strip().lower()
    if action not in {"save", "delete"}:
        return {"changed": False, "reload": False, "message": None}

    selected_raw = str(editor.get("selected") or "").strip().lower()
    selected_key = "" if selected_raw in {"", "__new__", "new"} else _sanitize_profile_key(selected_raw)

    if action == "delete":
        target = selected_key
        if target in {"", "balanced"} or target not in catalog:
            return {"changed": False, "reload": False, "message": None}
        catalog.pop(target, None)
        if str(profiles.get("default") or "").strip().lower() == target:
            profiles["default"] = "balanced"
        return {
            "changed": True,
            "reload": True,
            "message": f"Profilo '{target}' eliminato. Catalogo aggiornato.",
        }

    target = selected_key or _sanitize_profile_key(editor.get("key"))
    if not target:
        return {"changed": False, "reload": False, "message": None}

    payload = _normalize_pdf_profile_payload(editor)
    payload["label"] = str(editor.get("label") or target)
    existed = target in catalog
    payload_changed = catalog.get(target) != payload
    if payload_changed:
        catalog[target] = payload

    default_changed = False
    if _is_truthy(editor.get("make_default")) and str(profiles.get("default") or "").strip().lower() != target:
        profiles["default"] = target
        default_changed = True

    if not payload_changed and not default_changed:
        return {"changed": False, "reload": False, "message": None}

    message = f"Profilo '{target}' creato e aggiunto al catalogo." if not existed else f"Profilo '{target}' aggiornato."
    return {
        "changed": True,
        "reload": not existed,
        "message": message,
    }


def _ensure_valid_default_profile(*, profiles: dict[str, Any], catalog: dict[str, Any]) -> None:
    current_default = str(profiles.get("default") or "").strip().lower()
    if current_default not in catalog:
        profiles["default"] = "balanced"


def _postprocess_pdf_profiles(settings_node: dict[str, Any]) -> dict[str, Any]:
    profiles, catalog = _ensure_pdf_profiles_catalog(settings_node)
    _normalize_pdf_catalog(catalog)
    deleted = _apply_profile_deletions(profiles=profiles, catalog=catalog)
    created_or_updated = _apply_new_profile(profiles=profiles, catalog=catalog)
    editor_result = _apply_profile_editor_action(profiles=profiles, catalog=catalog)
    _ensure_valid_default_profile(profiles=profiles, catalog=catalog)
    return {
        "catalog_changed": bool(deleted or created_or_updated or editor_result.get("changed")),
        "reload": bool(deleted or created_or_updated or editor_result.get("reload")),
        "message": editor_result.get("message"),
    }


def settings_page(request):
    """Renderizza la pagina delle impostazioni."""
    is_hx = request.headers.get("HX-Request") == "true"
    if is_hx:
        return settings_content()
    return base_layout(title="Impostazioni - Universal IIIF", content=settings_content(), active_page="settings")


async def save_settings(request):
    """Salva le impostazioni inviate dal form.

    The form must send dotted keys (e.g. `settings.viewer.mirador.openSeadragonOptions.maxZoomLevel`).
    This handler inflates them into nested dicts and merges into the existing config.
    """
    form = await request.form()
    cm = get_config_manager()

    try:
        payload = _inflate_dotted_payload(form.items())
        has_desc = _payload_has(payload, "settings.pdf.cover.description")
        logger.debug("Payload contains settings.pdf.cover.description: %s", has_desc)

        _merge_payload_into_config(cm.data, payload)
        settings_node = cm.data.setdefault("settings", {})
        _postprocess_images_settings(settings_node)
        profile_changes = _postprocess_pdf_profiles(settings_node)
        ui_settings = settings_node.get("ui")
        if not isinstance(ui_settings, dict):
            settings_node["ui"] = {}
            ui_settings = settings_node["ui"]
        normalize_ui_theme_in_place(ui_settings)
        cm.save()
        _reconfigure_logging_after_save()
        if profile_changes.get("reload"):
            message = str(profile_changes.get("message") or "Catalogo profili PDF aggiornato.")
            return [
                build_toast(message, "success"),
                Script(
                    "setTimeout(() => { window.location.href = '/settings?tab=pdf'; }, 140);",
                    hx_swap_oob="true",
                ),
            ]
        return build_toast("Impostazioni salvate con successo!", "success")
    except Exception as exc:
        return build_toast(f"Errore nel salvataggio: {exc}", "danger")
