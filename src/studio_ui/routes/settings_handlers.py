import json
from collections.abc import Iterable
from typing import Any

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
        ui_settings = settings_node.get("ui")
        if not isinstance(ui_settings, dict):
            settings_node["ui"] = {}
            ui_settings = settings_node["ui"]
        normalize_ui_theme_in_place(ui_settings)
        cm.save()
        _reconfigure_logging_after_save()
        return build_toast("Impostazioni salvate con successo!", "success")
    except Exception as exc:
        return build_toast(f"Errore nel salvataggio: {exc}", "danger")
