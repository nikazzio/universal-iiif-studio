from __future__ import annotations

import json

from universal_iiif_core.config_manager import DEFAULT_CONFIG_JSON
from universal_iiif_core.config_validation import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    validate_config,
)


def _clone_default() -> dict:
    return json.loads(json.dumps(DEFAULT_CONFIG_JSON))


def test_validate_config_reports_deprecated_and_unknown_keys():
    """Deprecated and unknown keys should produce warnings."""
    data = _clone_default()
    data["settings"]["thumbnails"]["columns"] = 6
    data["settings"]["extra_section"] = {"foo": "bar"}
    data["settings"]["pdf"]["profiles"]["catalog"]["custom_profile"] = {
        **data["settings"]["pdf"]["profiles"]["catalog"]["balanced"],
        "custom_field": "unused",
    }

    issues = validate_config(data, schema=DEFAULT_CONFIG_JSON)

    assert any(
        issue.severity == SEVERITY_WARNING
        and issue.code == "deprecated_key"
        and issue.path == "settings.thumbnails.columns"
        for issue in issues
    )
    assert any(
        issue.severity == SEVERITY_WARNING and issue.code == "unknown_key" and issue.path == "settings.extra_section"
        for issue in issues
    )
    assert any(
        issue.severity == SEVERITY_WARNING
        and issue.code == "unknown_key"
        and issue.path == "settings.pdf.profiles.catalog.custom_profile.custom_field"
        for issue in issues
    )


def test_validate_config_reports_errors_for_critical_type_mismatch():
    """Critical type mismatches should be reported as errors."""
    data = _clone_default()
    data["security"]["allowed_origins"] = "http://localhost:8000"
    data["paths"] = "data/local"

    issues = validate_config(data, schema=DEFAULT_CONFIG_JSON)

    assert any(
        issue.severity == SEVERITY_ERROR and issue.code == "invalid_type" and issue.path == "paths" for issue in issues
    )
    assert any(
        issue.severity == SEVERITY_ERROR and issue.code == "invalid_type" and issue.path == "security.allowed_origins"
        for issue in issues
    )


def test_validate_config_reports_out_of_range_values():
    """Range checks should emit warnings for non-fatal anomalies."""
    data = _clone_default()
    data["settings"]["thumbnails"]["page_size"] = 500
    data["settings"]["images"]["tile_stitch_max_ram_gb"] = 0.01

    issues = validate_config(data, schema=DEFAULT_CONFIG_JSON)

    assert any(
        issue.severity == SEVERITY_WARNING
        and issue.code == "out_of_range"
        and issue.path == "settings.thumbnails.page_size"
        for issue in issues
    )
    assert any(
        issue.severity == SEVERITY_WARNING
        and issue.code == "out_of_range"
        and issue.path == "settings.images.tile_stitch_max_ram_gb"
        for issue in issues
    )
