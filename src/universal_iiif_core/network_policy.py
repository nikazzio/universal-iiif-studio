from __future__ import annotations

from copy import deepcopy
from typing import Any

LIBRARY_KEY_ALIASES: dict[str, str] = {
    "gallica": "gallica",
    "gallica (bnf)": "gallica",
    "vaticana": "vaticana",
    "vaticana (bav)": "vaticana",
    "bodleian": "bodleian",
    "bodleian (oxford)": "bodleian",
    "institut de france": "institut_de_france",
    "institut de france (bibnum)": "institut_de_france",
    "unknown": "unknown",
}

LIBRARY_KEYS: tuple[str, ...] = (
    "gallica",
    "vaticana",
    "bodleian",
    "institut_de_france",
    "unknown",
)

_OBSOLETE_LIBRARY_SETTING_SUFFIXES: tuple[str, ...] = (
    "size_strategy_mode",
    "size_strategy_custom",
    "allow_max_size",
    "iiif_quality",
    "connect_timeout_s",
    "read_timeout_s",
)

DEFAULT_NETWORK_SETTINGS: dict[str, Any] = {
    "global": {
        "max_concurrent_download_jobs": 2,
        "connect_timeout_s": 10,
        "read_timeout_s": 30,
        "transport_retries": 3,
        "per_host_concurrency": 4,
    },
    "download": {
        "default_workers_per_job": 2,
        "default_min_delay_s": 0.6,
        "default_max_delay_s": 1.6,
        "default_retry_max_attempts": 5,
        "default_backoff_base_s": 15.0,
        "default_backoff_cap_s": 300.0,
        "respect_retry_after": True,
    },
    "libraries": {
        "gallica": {
            "enabled": True,
            "use_custom_policy": True,
            "workers_per_job": 1,
            "per_host_concurrency": 2,
            "min_delay_s": 2.5,
            "max_delay_s": 6.0,
            "retry_max_attempts": 3,
            "backoff_base_s": 20.0,
            "backoff_cap_s": 300.0,
            "cooldown_on_403_s": 600,
            "cooldown_on_429_s": 300,
            "burst_window_s": 60,
            "burst_max_requests": 20,
            "respect_retry_after": True,
            "prewarm_viewer": False,
            "send_referer_header": True,
            "send_origin_header": False,
        },
        "vaticana": {
            "enabled": True,
            "use_custom_policy": False,
            "workers_per_job": 2,
            "min_delay_s": 0.6,
            "max_delay_s": 1.6,
            "retry_max_attempts": 5,
            "backoff_base_s": 15.0,
            "backoff_cap_s": 300.0,
            "cooldown_on_403_s": 120,
            "cooldown_on_429_s": 120,
            "burst_window_s": 60,
            "burst_max_requests": 100,
            "respect_retry_after": True,
            "prewarm_viewer": True,
            "send_referer_header": True,
            "send_origin_header": False,
        },
        "bodleian": {
            "enabled": True,
            "use_custom_policy": False,
            "workers_per_job": 2,
            "min_delay_s": 0.6,
            "max_delay_s": 1.6,
            "retry_max_attempts": 5,
            "backoff_base_s": 15.0,
            "backoff_cap_s": 300.0,
            "cooldown_on_403_s": 120,
            "cooldown_on_429_s": 120,
            "burst_window_s": 60,
            "burst_max_requests": 100,
            "respect_retry_after": True,
            "prewarm_viewer": False,
            "send_referer_header": True,
            "send_origin_header": False,
        },
        "institut_de_france": {
            "enabled": True,
            "use_custom_policy": False,
            "workers_per_job": 2,
            "min_delay_s": 0.6,
            "max_delay_s": 1.6,
            "retry_max_attempts": 5,
            "backoff_base_s": 15.0,
            "backoff_cap_s": 300.0,
            "cooldown_on_403_s": 120,
            "cooldown_on_429_s": 120,
            "burst_window_s": 60,
            "burst_max_requests": 100,
            "respect_retry_after": True,
            "prewarm_viewer": False,
            "send_referer_header": True,
            "send_origin_header": False,
        },
        "unknown": {
            "enabled": True,
            "use_custom_policy": False,
            "workers_per_job": 2,
            "min_delay_s": 0.6,
            "max_delay_s": 1.6,
            "retry_max_attempts": 5,
            "backoff_base_s": 15.0,
            "backoff_cap_s": 300.0,
            "cooldown_on_403_s": 120,
            "cooldown_on_429_s": 120,
            "burst_window_s": 60,
            "burst_max_requests": 100,
            "respect_retry_after": True,
            "prewarm_viewer": False,
            "send_referer_header": True,
            "send_origin_header": False,
        },
    },
}

OBSOLETE_SETTING_KEYS: tuple[str, ...] = (
    "settings.system.max_concurrent_downloads",
    "settings.system.download_workers",
    "settings.system.request_timeout",
    "settings.system.ocr_concurrency",
    "settings.defaults.auto_generate_pdf",
    "settings.images.ocr_quality",
    "settings.pdf.ocr_dpi",
    "settings.thumbnails.columns",
    "settings.thumbnails.paginate_enabled",
    "settings.thumbnails.default_select_all",
    "settings.thumbnails.actions_apply_to_all_default",
    "settings.thumbnails.hover_preview_enabled",
    "settings.thumbnails.hover_preview_max_long_edge_px",
    "settings.thumbnails.hover_preview_jpeg_quality",
    "settings.thumbnails.hover_preview_delay_ms",
    "settings.thumbnails.inline_base64_max_tiles",
    "settings.thumbnails.hover_preview_max_tiles",
    "settings.network.tuning_steps",
    *tuple(
        f"settings.network.libraries.{library_key}.{suffix}"
        for library_key in LIBRARY_KEYS
        for suffix in _OBSOLETE_LIBRARY_SETTING_SUFFIXES
    ),
)


def normalize_library_key(raw: str | None) -> str:
    """Map a display library name to a canonical policy key."""
    text = str(raw or "").strip().lower()
    return LIBRARY_KEY_ALIASES.get(text, "unknown")


def _deep_merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for key, value in (src or {}).items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            _deep_merge(dst[key], value)
        else:
            dst[key] = value
    return dst


def _dict_or_empty(node: Any) -> dict[str, Any]:
    return node if isinstance(node, dict) else {}


def _as_int(value: Any, default: int, *, min_value: int, max_value: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(min_value, min(number, max_value))


def _as_float(value: Any, default: float, *, min_value: float, max_value: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(min_value, min(number, max_value))


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _normalize_global_node(global_node: dict[str, Any]) -> dict[str, Any]:
    defaults = DEFAULT_NETWORK_SETTINGS["global"]
    return {
        "max_concurrent_download_jobs": _as_int(
            global_node.get("max_concurrent_download_jobs", defaults["max_concurrent_download_jobs"]),
            defaults["max_concurrent_download_jobs"],
            min_value=1,
            max_value=8,
        ),
        "connect_timeout_s": _as_int(
            global_node.get("connect_timeout_s", defaults["connect_timeout_s"]),
            defaults["connect_timeout_s"],
            min_value=2,
            max_value=120,
        ),
        "read_timeout_s": _as_int(
            global_node.get("read_timeout_s", defaults["read_timeout_s"]),
            defaults["read_timeout_s"],
            min_value=5,
            max_value=300,
        ),
        "transport_retries": _as_int(
            global_node.get("transport_retries", defaults["transport_retries"]),
            defaults["transport_retries"],
            min_value=0,
            max_value=10,
        ),
    }


def _normalize_download_node(download_node: dict[str, Any]) -> dict[str, Any]:
    defaults = DEFAULT_NETWORK_SETTINGS["download"]
    normalized = {
        "default_workers_per_job": _as_int(
            download_node.get("default_workers_per_job", defaults["default_workers_per_job"]),
            defaults["default_workers_per_job"],
            min_value=1,
            max_value=8,
        ),
        "default_min_delay_s": _as_float(
            download_node.get("default_min_delay_s", defaults["default_min_delay_s"]),
            defaults["default_min_delay_s"],
            min_value=0.05,
            max_value=60.0,
        ),
        "default_max_delay_s": _as_float(
            download_node.get("default_max_delay_s", defaults["default_max_delay_s"]),
            defaults["default_max_delay_s"],
            min_value=0.1,
            max_value=180.0,
        ),
        "default_retry_max_attempts": _as_int(
            download_node.get("default_retry_max_attempts", defaults["default_retry_max_attempts"]),
            defaults["default_retry_max_attempts"],
            min_value=1,
            max_value=10,
        ),
        "default_backoff_base_s": _as_float(
            download_node.get("default_backoff_base_s", defaults["default_backoff_base_s"]),
            defaults["default_backoff_base_s"],
            min_value=1.0,
            max_value=600.0,
        ),
        "default_backoff_cap_s": _as_float(
            download_node.get("default_backoff_cap_s", defaults["default_backoff_cap_s"]),
            defaults["default_backoff_cap_s"],
            min_value=5.0,
            max_value=3600.0,
        ),
        "respect_retry_after": _as_bool(
            download_node.get("respect_retry_after"),
            bool(defaults["respect_retry_after"]),
        ),
    }
    if normalized["default_max_delay_s"] < normalized["default_min_delay_s"]:
        normalized["default_max_delay_s"] = normalized["default_min_delay_s"]
    if normalized["default_backoff_cap_s"] < normalized["default_backoff_base_s"]:
        normalized["default_backoff_cap_s"] = normalized["default_backoff_base_s"]
    return normalized


def _normalize_library_node(library_key: str, library_node: dict[str, Any]) -> dict[str, Any]:
    defaults = _dict_or_empty(DEFAULT_NETWORK_SETTINGS["libraries"].get(library_key))
    merged = deepcopy(defaults)
    _deep_merge(merged, _dict_or_empty(library_node))

    normalized = {
        "enabled": _as_bool(merged.get("enabled"), bool(defaults.get("enabled", True))),
        "use_custom_policy": _as_bool(
            merged.get("use_custom_policy"),
            bool(defaults.get("use_custom_policy", library_key == "gallica")),
        ),
        "workers_per_job": _as_int(
            merged.get("workers_per_job", defaults.get("workers_per_job", 2)), 2, min_value=1, max_value=8
        ),
        "min_delay_s": _as_float(
            merged.get("min_delay_s", defaults.get("min_delay_s", 0.6)), 0.6, min_value=0.05, max_value=120.0
        ),
        "max_delay_s": _as_float(
            merged.get("max_delay_s", defaults.get("max_delay_s", 1.6)), 1.6, min_value=0.1, max_value=180.0
        ),
        "retry_max_attempts": _as_int(
            merged.get("retry_max_attempts", defaults.get("retry_max_attempts", 5)),
            5,
            min_value=1,
            max_value=10,
        ),
        "backoff_base_s": _as_float(
            merged.get("backoff_base_s", defaults.get("backoff_base_s", 15.0)),
            15.0,
            min_value=1.0,
            max_value=600.0,
        ),
        "backoff_cap_s": _as_float(
            merged.get("backoff_cap_s", defaults.get("backoff_cap_s", 300.0)),
            300.0,
            min_value=5.0,
            max_value=3600.0,
        ),
        "cooldown_on_403_s": _as_int(
            merged.get("cooldown_on_403_s", defaults.get("cooldown_on_403_s", 0)),
            0,
            min_value=0,
            max_value=7200,
        ),
        "cooldown_on_429_s": _as_int(
            merged.get("cooldown_on_429_s", defaults.get("cooldown_on_429_s", 0)),
            0,
            min_value=0,
            max_value=7200,
        ),
        "burst_window_s": _as_int(
            merged.get("burst_window_s", defaults.get("burst_window_s", 60)),
            60,
            min_value=1,
            max_value=600,
        ),
        "burst_max_requests": _as_int(
            merged.get("burst_max_requests", defaults.get("burst_max_requests", 100)),
            100,
            min_value=1,
            max_value=2000,
        ),
        "respect_retry_after": _as_bool(
            merged.get("respect_retry_after"),
            bool(defaults.get("respect_retry_after", True)),
        ),
        "prewarm_viewer": _as_bool(merged.get("prewarm_viewer"), bool(defaults.get("prewarm_viewer", False))),
        "send_referer_header": _as_bool(
            merged.get("send_referer_header"),
            bool(defaults.get("send_referer_header", True)),
        ),
        "send_origin_header": _as_bool(
            merged.get("send_origin_header"),
            bool(defaults.get("send_origin_header", False)),
        ),
    }

    if normalized["max_delay_s"] < normalized["min_delay_s"]:
        normalized["max_delay_s"] = normalized["min_delay_s"]
    if normalized["backoff_cap_s"] < normalized["backoff_base_s"]:
        normalized["backoff_cap_s"] = normalized["backoff_base_s"]

    return normalized


def ensure_network_defaults(settings_node: dict[str, Any]) -> dict[str, Any]:
    """Ensure `settings.network` exists and is merged over default policy values."""
    network = settings_node.get("network")
    if not isinstance(network, dict):
        network = {}
        settings_node["network"] = network

    baseline = deepcopy(DEFAULT_NETWORK_SETTINGS)
    _deep_merge(baseline, network)
    settings_node["network"] = baseline
    return baseline


def normalize_network_settings(settings_node: dict[str, Any]) -> None:
    """Clamp and sanitize all network settings according to supported ranges."""
    network = ensure_network_defaults(settings_node)
    network["global"] = _normalize_global_node(_dict_or_empty(network.get("global")))
    network["download"] = _normalize_download_node(_dict_or_empty(network.get("download")))

    libraries_raw = _dict_or_empty(network.get("libraries"))
    normalized_libraries: dict[str, dict[str, Any]] = {}
    for library_key in LIBRARY_KEYS:
        normalized_libraries[library_key] = _normalize_library_node(
            library_key, _dict_or_empty(libraries_raw.get(library_key))
        )
    network["libraries"] = normalized_libraries


def resolve_library_network_policy(settings_node: dict[str, Any], library: str | None) -> dict[str, Any]:
    """Return the effective runtime network policy for a given library name."""
    normalize_network_settings(settings_node)
    network = _dict_or_empty(settings_node.get("network"))
    global_node = _dict_or_empty(network.get("global"))
    download_node = _dict_or_empty(network.get("download"))
    libraries = _dict_or_empty(network.get("libraries"))

    library_key = normalize_library_key(library)
    lib_node = _dict_or_empty(libraries.get(library_key))
    use_custom_policy = _as_bool(lib_node.get("use_custom_policy"), library_key == "gallica")

    workers = (
        _as_int(lib_node.get("workers_per_job", 1), 1, min_value=1, max_value=8)
        if use_custom_policy
        else _as_int(download_node.get("default_workers_per_job", 2), 2, min_value=1, max_value=8)
    )
    min_delay = (
        _as_float(lib_node.get("min_delay_s", 0.6), 0.6, min_value=0.05, max_value=120.0)
        if use_custom_policy
        else _as_float(download_node.get("default_min_delay_s", 0.6), 0.6, min_value=0.05, max_value=120.0)
    )
    max_delay = (
        _as_float(lib_node.get("max_delay_s", 1.6), 1.6, min_value=0.1, max_value=180.0)
        if use_custom_policy
        else _as_float(download_node.get("default_max_delay_s", 1.6), 1.6, min_value=0.1, max_value=180.0)
    )
    if max_delay < min_delay:
        max_delay = min_delay

    retry_max_attempts = (
        _as_int(lib_node.get("retry_max_attempts", 5), 5, min_value=1, max_value=10)
        if use_custom_policy
        else _as_int(download_node.get("default_retry_max_attempts", 5), 5, min_value=1, max_value=10)
    )
    backoff_base_s = (
        _as_float(lib_node.get("backoff_base_s", 15.0), 15.0, min_value=1.0, max_value=600.0)
        if use_custom_policy
        else _as_float(download_node.get("default_backoff_base_s", 15.0), 15.0, min_value=1.0, max_value=600.0)
    )
    backoff_cap_s = (
        _as_float(lib_node.get("backoff_cap_s", 300.0), 300.0, min_value=5.0, max_value=3600.0)
        if use_custom_policy
        else _as_float(download_node.get("default_backoff_cap_s", 300.0), 300.0, min_value=5.0, max_value=3600.0)
    )
    if backoff_cap_s < backoff_base_s:
        backoff_cap_s = backoff_base_s

    return {
        "library_key": library_key,
        "library_name": library or "Unknown",
        "enabled": _as_bool(lib_node.get("enabled"), True),
        "use_custom_policy": use_custom_policy,
        "max_concurrent_download_jobs": _as_int(
            global_node.get("max_concurrent_download_jobs", 2),
            2,
            min_value=1,
            max_value=8,
        ),
        "connect_timeout_s": _as_int(global_node.get("connect_timeout_s", 10), 10, min_value=2, max_value=120),
        "read_timeout_s": _as_int(global_node.get("read_timeout_s", 30), 30, min_value=5, max_value=300),
        "transport_retries": _as_int(global_node.get("transport_retries", 3), 3, min_value=0, max_value=10),
        "workers_per_job": workers,
        "min_delay_s": min_delay,
        "max_delay_s": max_delay,
        "retry_max_attempts": retry_max_attempts,
        "backoff_base_s": backoff_base_s,
        "backoff_cap_s": backoff_cap_s,
        "respect_retry_after": (
            _as_bool(lib_node.get("respect_retry_after"), True)
            if use_custom_policy
            else _as_bool(download_node.get("respect_retry_after"), True)
        ),
        "cooldown_on_403_s": (
            _as_int(lib_node.get("cooldown_on_403_s", 0), 0, min_value=0, max_value=7200) if use_custom_policy else 0
        ),
        "cooldown_on_429_s": (
            _as_int(lib_node.get("cooldown_on_429_s", 0), 0, min_value=0, max_value=7200) if use_custom_policy else 0
        ),
        "burst_window_s": (
            _as_int(lib_node.get("burst_window_s", 60), 60, min_value=1, max_value=600) if use_custom_policy else 60
        ),
        "burst_max_requests": (
            _as_int(lib_node.get("burst_max_requests", 100), 100, min_value=1, max_value=2000)
            if use_custom_policy
            else 100
        ),
        "prewarm_viewer": _as_bool(lib_node.get("prewarm_viewer"), False) if use_custom_policy else False,
        "send_referer_header": _as_bool(lib_node.get("send_referer_header"), True) if use_custom_policy else True,
        "send_origin_header": _as_bool(lib_node.get("send_origin_header"), False) if use_custom_policy else False,
    }


def resolve_global_max_concurrent_jobs(settings_node: dict[str, Any]) -> int:
    """Return the globally configured max number of concurrent download jobs."""
    policy = resolve_library_network_policy(settings_node, "Unknown")
    return int(policy.get("max_concurrent_download_jobs") or 2)
