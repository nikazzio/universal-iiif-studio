import json

from studio_ui.common.toasts import build_toast
from studio_ui.components.layout import base_layout
from studio_ui.components.settings import settings_content
from universal_iiif_core.config_manager import get_config_manager


def _parse_value(raw: str):
    """Try to coerce form string values into proper types.

    - Try JSON first (for arrays/objects)
    - Then booleans (1/0, true/false)
    - Then ints/floats
    - Then comma-separated lists
    - Otherwise return original string
    """
    if raw is None:
        return None
    raw = raw.strip()
    if raw == "":
        return ""
    # JSON
    try:
        return json.loads(raw)
    except Exception:
        pass
    low = raw.lower()
    if low in ("true", "false"):
        return low == "true"
    # numeric int
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except Exception:
        pass
    # comma separated
    if "," in raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        return parts
    return raw


def _deep_merge(dst: dict, src: dict) -> dict:
    for k, v in (src or {}).items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def settings_page(request):
    """Renderizza la pagina delle impostazioni."""
    # If request comes from HTMX (sidebar navigation), return only the fragment
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
        # Build a nested dict from dotted form keys
        payload: dict = {}
        for raw_key, raw_val in form.items():
            # Values from checkbox inputs may be '1' or absent; we keep them as is and parse
            parsed = _parse_value(raw_val)
            parts = [p for p in raw_key.split(".") if p]
            node = payload
            for part in parts[:-1]:
                if part not in node or not isinstance(node[part], dict):
                    node[part] = {}
                node = node[part]
            node[parts[-1]] = parsed

        # Merge payload into existing cm.data for top-level keys only
        for top_key, top_val in payload.items():
            if top_key in ("settings", "paths", "api_keys") and isinstance(top_val, dict):
                _deep_merge(cm.data.setdefault(top_key, {}), top_val)
            else:
                # Fallback: set at top-level
                cm.data[top_key] = top_val

        # Persist
        cm.save()

        return build_toast("Impostazioni salvate con successo!", "success")

    except Exception as e:
        return build_toast(f"Errore nel salvataggio: {e}", "danger")
        return build_toast(f"Errore nel salvataggio: {e}", "danger")
