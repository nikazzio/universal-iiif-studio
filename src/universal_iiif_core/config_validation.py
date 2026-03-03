"""Runtime validation for config.json.

The validator is non-mutating by design: it reports anomalies as issues
without rewriting user configuration files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SEVERITY_WARNING = "WARNING"
SEVERITY_ERROR = "ERROR"


@dataclass(frozen=True)
class ConfigValidationIssue:
    """One validation diagnostic produced by the config validator."""

    severity: str
    path: str
    code: str
    message: str


DEPRECATED_KEYS: tuple[str, ...] = (
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
    "settings.network.libraries.gallica.size_strategy_mode",
    "settings.network.libraries.gallica.size_strategy_custom",
    "settings.network.libraries.gallica.allow_max_size",
    "settings.network.libraries.gallica.iiif_quality",
    "settings.network.libraries.vaticana.size_strategy_mode",
    "settings.network.libraries.vaticana.size_strategy_custom",
    "settings.network.libraries.vaticana.allow_max_size",
    "settings.network.libraries.vaticana.iiif_quality",
    "settings.network.libraries.bodleian.size_strategy_mode",
    "settings.network.libraries.bodleian.size_strategy_custom",
    "settings.network.libraries.bodleian.allow_max_size",
    "settings.network.libraries.bodleian.iiif_quality",
    "settings.network.libraries.institut_de_france.size_strategy_mode",
    "settings.network.libraries.institut_de_france.size_strategy_custom",
    "settings.network.libraries.institut_de_france.allow_max_size",
    "settings.network.libraries.institut_de_france.iiif_quality",
    "settings.network.libraries.unknown.size_strategy_mode",
    "settings.network.libraries.unknown.size_strategy_custom",
    "settings.network.libraries.unknown.allow_max_size",
    "settings.network.libraries.unknown.iiif_quality",
)


PROFILE_PAYLOAD_SCHEMA: dict[str, Any] = {
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
}

_CRITICAL_PREFIXES = ("paths", "security", "api_keys")
_FLOAT_COMPATIBLE_PATHS = {
    "settings.images.tile_stitch_max_ram_gb",
    "settings.network.download.default_min_delay_s",
    "settings.network.download.default_max_delay_s",
    "settings.network.download.default_backoff_base_s",
    "settings.network.download.default_backoff_cap_s",
    "settings.viewer.mirador.openSeadragonOptions.maxZoomPixelRatio",
    "settings.viewer.mirador.openSeadragonOptions.maxZoomLevel",
    "settings.viewer.mirador.openSeadragonOptions.minZoomLevel",
    "settings.viewer.visual_filters.defaults.brightness",
    "settings.viewer.visual_filters.defaults.contrast",
    "settings.viewer.visual_filters.defaults.saturation",
    "settings.viewer.visual_filters.defaults.hue",
    "settings.viewer.visual_filters.presets.default.brightness",
    "settings.viewer.visual_filters.presets.default.contrast",
    "settings.viewer.visual_filters.presets.default.saturation",
    "settings.viewer.visual_filters.presets.default.hue",
    "settings.viewer.visual_filters.presets.night.brightness",
    "settings.viewer.visual_filters.presets.night.contrast",
    "settings.viewer.visual_filters.presets.night.saturation",
    "settings.viewer.visual_filters.presets.night.hue",
    "settings.viewer.visual_filters.presets.contrast.brightness",
    "settings.viewer.visual_filters.presets.contrast.contrast",
    "settings.viewer.visual_filters.presets.contrast.saturation",
    "settings.viewer.visual_filters.presets.contrast.hue",
}


def validate_config(data: dict[str, Any], schema: dict[str, Any]) -> list[ConfigValidationIssue]:
    """Validate merged config data against schema and runtime expectations."""
    issues: list[ConfigValidationIssue] = []
    _validate_structure(data, schema, path="", issues=issues)
    _validate_deprecated_keys(data, issues)
    _validate_semantics(data, issues)
    return issues


def _validate_structure(
    node: Any,
    schema: Any,
    *,
    path: str,
    issues: list[ConfigValidationIssue],
) -> None:
    if path == "settings.pdf.profiles.catalog":
        _validate_profiles_catalog(node, path=path, issues=issues)
        return

    if path == "settings.pdf.profiles.document_overrides":
        if not isinstance(node, dict):
            _add_error(
                issues,
                path=path,
                code="invalid_type",
                message=f"Expected object, got {_type_name(node)}.",
            )
        return

    if isinstance(schema, dict):
        _validate_object_structure(node, schema, path=path, issues=issues)
        return

    if isinstance(schema, list):
        _validate_array_structure(node, schema, path=path, issues=issues)
        return

    _validate_scalar_structure(node, schema, path=path, issues=issues)


def _validate_object_structure(
    node: Any,
    schema: dict[str, Any],
    *,
    path: str,
    issues: list[ConfigValidationIssue],
) -> None:
    if not isinstance(node, dict):
        _add_type_issue(issues, path=path or "$", expected="object", value=node)
        return
    for key in node:
        if key not in schema:
            _add_warning(
                issues,
                path=_join(path, key),
                code="unknown_key",
                message="Unknown config key.",
            )
    for key, child_schema in schema.items():
        if key in node:
            _validate_structure(node[key], child_schema, path=_join(path, key), issues=issues)


def _validate_array_structure(
    node: Any,
    schema: list[Any],
    *,
    path: str,
    issues: list[ConfigValidationIssue],
) -> None:
    if not isinstance(node, list):
        _add_type_issue(issues, path=path, expected="array", value=node)
        return
    if not schema:
        return
    sample = schema[0]
    for idx, item in enumerate(node):
        _validate_structure(item, sample, path=f"{path}[{idx}]", issues=issues)


def _validate_scalar_structure(
    node: Any,
    schema: Any,
    *,
    path: str,
    issues: list[ConfigValidationIssue],
) -> None:
    expected_type = type(schema)
    if (
        expected_type is int
        and path in _FLOAT_COMPATIBLE_PATHS
        and isinstance(node, (int, float))
        and not isinstance(node, bool)
    ):
        return
    if _matches_type(node, expected_type):
        return
    _add_type_issue(issues, path=path, expected=expected_type.__name__, value=node)


def _validate_profiles_catalog(
    node: Any,
    *,
    path: str,
    issues: list[ConfigValidationIssue],
) -> None:
    if not isinstance(node, dict):
        _add_error(
            issues,
            path=path,
            code="invalid_type",
            message=f"Expected object, got {_type_name(node)}.",
        )
        return

    for profile_name, payload in node.items():
        profile_path = _join(path, str(profile_name))
        if not isinstance(payload, dict):
            _add_error(
                issues,
                path=profile_path,
                code="invalid_type",
                message=f"Expected object, got {_type_name(payload)}.",
            )
            continue
        for key in payload:
            if key not in PROFILE_PAYLOAD_SCHEMA:
                _add_warning(
                    issues,
                    path=_join(profile_path, key),
                    code="unknown_key",
                    message="Unknown profile field.",
                )
        for key, expected in PROFILE_PAYLOAD_SCHEMA.items():
            if key not in payload:
                continue
            if not _matches_type(payload[key], type(expected)):
                _add_error(
                    issues,
                    path=_join(profile_path, key),
                    code="invalid_type",
                    message=f"Expected {type(expected).__name__}, got {_type_name(payload[key])}.",
                )


def _validate_deprecated_keys(data: dict[str, Any], issues: list[ConfigValidationIssue]) -> None:
    for key_path in DEPRECATED_KEYS:
        if _path_exists(data, key_path):
            _add_warning(
                issues,
                path=key_path,
                code="deprecated_key",
                message="Deprecated config key is present and ignored by current runtime.",
            )


def _validate_semantics(data: dict[str, Any], issues: list[ConfigValidationIssue]) -> None:
    _validate_allowed_origins(data, issues)
    _validate_int_range(data, issues, "settings.network.global.max_concurrent_download_jobs", 1, 8)
    _validate_int_range(data, issues, "settings.network.global.connect_timeout_s", 2, 120)
    _validate_int_range(data, issues, "settings.network.global.read_timeout_s", 5, 300)
    _validate_int_range(data, issues, "settings.network.global.transport_retries", 0, 10)
    _validate_int_range(data, issues, "settings.network.download.default_workers_per_job", 1, 8)
    _validate_float_range(data, issues, "settings.network.download.default_min_delay_s", 0.05, 120.0)
    _validate_float_range(data, issues, "settings.network.download.default_max_delay_s", 0.1, 180.0)
    _validate_int_range(data, issues, "settings.network.download.default_retry_max_attempts", 1, 10)
    _validate_float_range(data, issues, "settings.network.download.default_backoff_base_s", 1.0, 600.0)
    _validate_float_range(data, issues, "settings.network.download.default_backoff_cap_s", 5.0, 3600.0)
    _validate_int_range(data, issues, "settings.ui.items_per_page", 1, 200)
    _validate_int_range(data, issues, "settings.ui.toast_duration", 500, 15000)
    _validate_int_range(data, issues, "settings.images.viewer_quality", 10, 100)
    _validate_float_range(data, issues, "settings.images.tile_stitch_max_ram_gb", 0.1, 64.0)
    _validate_int_range(data, issues, "settings.thumbnails.page_size", 1, 120)
    _validate_int_range(data, issues, "settings.thumbnails.max_long_edge_px", 64, 2000)
    _validate_int_range(data, issues, "settings.thumbnails.jpeg_quality", 10, 100)
    _validate_int_range(data, issues, "settings.storage.exports_retention_days", 1, 3650)
    _validate_int_range(data, issues, "settings.storage.thumbnails_retention_days", 1, 3650)
    _validate_int_range(data, issues, "settings.storage.highres_temp_retention_hours", 1, 24 * 365)
    _validate_int_range(data, issues, "settings.storage.max_exports_per_item", 1, 1000)
    _validate_enum(
        data,
        issues,
        "settings.library.default_mode",
        {"operativa", "archivio"},
    )
    _validate_enum(
        data,
        issues,
        "settings.defaults.preferred_ocr_engine",
        {"openai", "anthropic", "google_vision", "kraken", "huggingface"},
    )
    _validate_enum(
        data,
        issues,
        "settings.ocr.ocr_engine",
        {"openai", "anthropic", "google_vision", "kraken", "huggingface"},
    )
    _validate_enum(
        data,
        issues,
        "settings.images.download_strategy_mode",
        {"balanced", "quality_first", "fast", "archival", "custom"},
    )
    _validate_enum(
        data,
        issues,
        "settings.pdf.export.default_format",
        {"pdf_images", "pdf_searchable", "pdf_facing"},
    )
    _validate_enum(
        data,
        issues,
        "settings.pdf.export.default_compression",
        {"High-Res", "Standard", "Light"},
    )
    _validate_enum(
        data,
        issues,
        "settings.logging.level",
        {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"},
        normalize_case=True,
    )
    _validate_network_library_profiles(data, issues)
    _validate_profile_default_exists(data, issues)
    _validate_thumbnail_options(data, issues)


def _validate_network_library_profiles(data: dict[str, Any], issues: list[ConfigValidationIssue]) -> None:
    exists, libraries = _get_path(data, "settings.network.libraries")
    if not exists:
        return
    if not isinstance(libraries, dict):
        _add_warning(
            issues,
            path="settings.network.libraries",
            code="invalid_type",
            message=f"Expected object, got {_type_name(libraries)}.",
        )
        return

    for library_key, node in libraries.items():
        base = f"settings.network.libraries.{library_key}"
        if not isinstance(node, dict):
            _add_warning(
                issues,
                path=base,
                code="invalid_type",
                message=f"Expected object, got {_type_name(node)}.",
            )
            continue
        _validate_int_range(data, issues, f"{base}.workers_per_job", 1, 8)
        _validate_float_range(data, issues, f"{base}.min_delay_s", 0.05, 120.0)
        _validate_float_range(data, issues, f"{base}.max_delay_s", 0.1, 180.0)
        _validate_int_range(data, issues, f"{base}.retry_max_attempts", 1, 10)
        _validate_float_range(data, issues, f"{base}.backoff_base_s", 1.0, 600.0)
        _validate_float_range(data, issues, f"{base}.backoff_cap_s", 5.0, 3600.0)
        _validate_int_range(data, issues, f"{base}.cooldown_on_403_s", 0, 7200)
        _validate_int_range(data, issues, f"{base}.cooldown_on_429_s", 0, 7200)
        _validate_int_range(data, issues, f"{base}.burst_window_s", 1, 600)
        _validate_int_range(data, issues, f"{base}.burst_max_requests", 1, 2000)


def _validate_allowed_origins(data: dict[str, Any], issues: list[ConfigValidationIssue]) -> None:
    exists, value = _get_path(data, "security.allowed_origins")
    if not exists:
        return
    if not isinstance(value, list):
        _add_error(
            issues,
            path="security.allowed_origins",
            code="invalid_type",
            message=f"Expected array of strings, got {_type_name(value)}.",
        )
        return
    for idx, item in enumerate(value):
        if not isinstance(item, str):
            _add_error(
                issues,
                path=f"security.allowed_origins[{idx}]",
                code="invalid_type",
                message=f"Expected string, got {_type_name(item)}.",
            )


def _validate_profile_default_exists(data: dict[str, Any], issues: list[ConfigValidationIssue]) -> None:
    default_exists, default_name = _get_path(data, "settings.pdf.profiles.default")
    catalog_exists, catalog = _get_path(data, "settings.pdf.profiles.catalog")
    if not default_exists or not catalog_exists:
        return
    if isinstance(default_name, str) and isinstance(catalog, dict) and default_name not in catalog:
        _add_warning(
            issues,
            path="settings.pdf.profiles.default",
            code="invalid_reference",
            message=f"Default profile '{default_name}' is not present in catalog.",
        )


def _validate_thumbnail_options(data: dict[str, Any], issues: list[ConfigValidationIssue]) -> None:
    exists, value = _get_path(data, "settings.thumbnails.page_size_options")
    if not exists:
        return
    if not isinstance(value, list):
        _add_warning(
            issues,
            path="settings.thumbnails.page_size_options",
            code="invalid_type",
            message=f"Expected array, got {_type_name(value)}.",
        )
        return
    for idx, item in enumerate(value):
        if not isinstance(item, int) or isinstance(item, bool):
            _add_warning(
                issues,
                path=f"settings.thumbnails.page_size_options[{idx}]",
                code="invalid_type",
                message=f"Expected int, got {_type_name(item)}.",
            )
            continue
        if not (1 <= item <= 120):
            _add_warning(
                issues,
                path=f"settings.thumbnails.page_size_options[{idx}]",
                code="out_of_range",
                message=f"Expected value in range [1, 120], got {item}.",
            )


def _validate_enum(
    data: dict[str, Any],
    issues: list[ConfigValidationIssue],
    path: str,
    allowed_values: set[str],
    *,
    normalize_case: bool = False,
) -> None:
    exists, value = _get_path(data, path)
    if not exists:
        return
    if not isinstance(value, str):
        _add_warning(
            issues,
            path=path,
            code="invalid_type",
            message=f"Expected string enum, got {_type_name(value)}.",
        )
        return
    candidate = value.upper() if normalize_case else value
    if candidate not in allowed_values:
        _add_warning(
            issues,
            path=path,
            code="invalid_enum",
            message=f"Unexpected enum value '{value}'.",
        )


def _validate_int_range(
    data: dict[str, Any],
    issues: list[ConfigValidationIssue],
    path: str,
    min_value: int,
    max_value: int,
) -> None:
    exists, value = _get_path(data, path)
    if not exists:
        return
    if not isinstance(value, int) or isinstance(value, bool):
        _add_warning(
            issues,
            path=path,
            code="invalid_type",
            message=f"Expected int, got {_type_name(value)}.",
        )
        return
    if not (min_value <= value <= max_value):
        _add_warning(
            issues,
            path=path,
            code="out_of_range",
            message=f"Expected value in range [{min_value}, {max_value}], got {value}.",
        )


def _validate_float_range(
    data: dict[str, Any],
    issues: list[ConfigValidationIssue],
    path: str,
    min_value: float,
    max_value: float,
) -> None:
    exists, value = _get_path(data, path)
    if not exists:
        return
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        _add_warning(
            issues,
            path=path,
            code="invalid_type",
            message=f"Expected number, got {_type_name(value)}.",
        )
        return
    numeric = float(value)
    if not (min_value <= numeric <= max_value):
        _add_warning(
            issues,
            path=path,
            code="out_of_range",
            message=f"Expected value in range [{min_value}, {max_value}], got {numeric}.",
        )


def _path_exists(data: dict[str, Any], dotted_path: str) -> bool:
    exists, _ = _get_path(data, dotted_path)
    return exists


def _get_path(data: dict[str, Any], dotted_path: str) -> tuple[bool, Any]:
    node: Any = data
    for part in dotted_path.split("."):
        if not part:
            continue
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = node[part]
    return True, node


def _matches_type(value: Any, expected: type[Any]) -> bool:
    if expected is bool:
        return isinstance(value, bool)
    if expected is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if expected is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, expected)


def _type_name(value: Any) -> str:
    return type(value).__name__


def _join(base: str, key: str) -> str:
    return f"{base}.{key}" if base else key


def _add_warning(
    issues: list[ConfigValidationIssue],
    *,
    path: str,
    code: str,
    message: str,
) -> None:
    issues.append(
        ConfigValidationIssue(
            severity=SEVERITY_WARNING,
            path=path,
            code=code,
            message=message,
        )
    )


def _add_error(
    issues: list[ConfigValidationIssue],
    *,
    path: str,
    code: str,
    message: str,
) -> None:
    issues.append(
        ConfigValidationIssue(
            severity=SEVERITY_ERROR,
            path=path,
            code=code,
            message=message,
        )
    )


def _add_type_issue(
    issues: list[ConfigValidationIssue],
    *,
    path: str,
    expected: str,
    value: Any,
) -> None:
    issue = ConfigValidationIssue(
        severity=SEVERITY_ERROR if _is_critical_path(path) else SEVERITY_WARNING,
        path=path,
        code="invalid_type",
        message=f"Expected {expected}, got {_type_name(value)}.",
    )
    issues.append(issue)


def _is_critical_path(path: str) -> bool:
    if path in {"$", ""}:
        return True
    return any(path == prefix or path.startswith(f"{prefix}.") for prefix in _CRITICAL_PREFIXES)
