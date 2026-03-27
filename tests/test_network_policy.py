from __future__ import annotations

import json

from universal_iiif_core.config_manager import DEFAULT_CONFIG_JSON
from universal_iiif_core.network_policy import (
    migrate_legacy_network_settings,
    resolve_global_max_concurrent_jobs,
    resolve_library_network_policy,
)


def _settings_copy() -> dict:
    return json.loads(json.dumps(DEFAULT_CONFIG_JSON)).get("settings", {})


def test_gallica_safe_defaults_are_applied():
    """Gallica should default to a conservative policy profile."""
    settings = _settings_copy()
    policy = resolve_library_network_policy(settings, "Gallica")

    assert policy["library_key"] == "gallica"
    assert policy["use_custom_policy"] is True
    assert policy["workers_per_job"] == 1
    assert "iiif_quality" not in policy
    assert "size_strategy" not in policy


def test_legacy_migration_maps_system_concurrency_to_network_global():
    """Legacy system concurrency should migrate to network.global value."""
    settings = _settings_copy()
    settings.setdefault("system", {})["max_concurrent_downloads"] = 4
    migrate_legacy_network_settings(settings)
    assert resolve_global_max_concurrent_jobs(settings) == 4


def test_unknown_library_inherits_global_defaults_when_custom_disabled():
    """Unknown library should use global defaults when custom policy is disabled."""
    settings = _settings_copy()
    settings.setdefault("network", {}).setdefault("download", {})["default_workers_per_job"] = 3
    policy = resolve_library_network_policy(settings, "Unknown")

    assert policy["library_key"] == "unknown"
    assert policy["enabled"] is True
    assert policy["use_custom_policy"] is False
    assert policy["workers_per_job"] == 3


def test_library_custom_policy_cannot_override_connect_and_read_timeout():
    """Connection/read timeouts are global and must ignore per-library custom values."""
    settings = _settings_copy()
    settings.setdefault("network", {}).setdefault("global", {})["connect_timeout_s"] = 14
    settings.setdefault("network", {}).setdefault("global", {})["read_timeout_s"] = 55
    libs = settings.setdefault("network", {}).setdefault("libraries", {})
    libs.setdefault("vaticana", {})
    libs["vaticana"]["use_custom_policy"] = True
    libs["vaticana"]["connect_timeout_s"] = 22
    libs["vaticana"]["read_timeout_s"] = 77

    policy = resolve_library_network_policy(settings, "Vaticana")

    assert policy["use_custom_policy"] is True
    assert policy["connect_timeout_s"] == 14
    assert policy["read_timeout_s"] == 55


def test_library_without_custom_policy_uses_global_timeouts():
    """Library without custom policy should inherit global connection/read timeouts."""
    settings = _settings_copy()
    settings.setdefault("network", {}).setdefault("global", {})["connect_timeout_s"] = 13
    settings.setdefault("network", {}).setdefault("global", {})["read_timeout_s"] = 44
    settings.setdefault("network", {}).setdefault("libraries", {}).setdefault("bodleian", {})["use_custom_policy"] = (
        False
    )

    policy = resolve_library_network_policy(settings, "Bodleian")

    assert policy["use_custom_policy"] is False
    assert policy["connect_timeout_s"] == 13
    assert policy["read_timeout_s"] == 44


def test_global_download_defaults_are_fully_applied_when_custom_is_disabled():
    """When custom policy is disabled, library policy must mirror global/download defaults."""
    settings = _settings_copy()
    settings.setdefault("network", {}).setdefault("global", {}).update(
        {
            "connect_timeout_s": 17,
            "read_timeout_s": 61,
            "max_concurrent_download_jobs": 5,
        }
    )
    settings.setdefault("network", {}).setdefault("download", {}).update(
        {
            "default_workers_per_job": 4,
            "default_min_delay_s": 1.1,
            "default_max_delay_s": 2.2,
            "default_retry_max_attempts": 7,
            "default_backoff_base_s": 12.0,
            "default_backoff_cap_s": 144.0,
            "respect_retry_after": False,
        }
    )
    settings.setdefault("network", {}).setdefault("libraries", {}).setdefault("bodleian", {})["use_custom_policy"] = (
        False
    )

    policy = resolve_library_network_policy(settings, "Bodleian")

    assert policy["max_concurrent_download_jobs"] == 5
    assert policy["workers_per_job"] == 4
    assert policy["connect_timeout_s"] == 17
    assert policy["read_timeout_s"] == 61
    assert policy["min_delay_s"] == 1.1
    assert policy["max_delay_s"] == 2.2
    assert policy["retry_max_attempts"] == 7
    assert policy["backoff_base_s"] == 12.0
    assert policy["backoff_cap_s"] == 144.0
    assert policy["respect_retry_after"] is False


def test_custom_policy_overrides_download_defaults_but_not_global_timeouts():
    """Custom policy overrides download tuning fields, but global timeouts stay shared."""
    settings = _settings_copy()
    settings.setdefault("network", {}).setdefault("global", {}).update(
        {
            "connect_timeout_s": 9,
            "read_timeout_s": 33,
        }
    )
    settings.setdefault("network", {}).setdefault("download", {}).update(
        {
            "default_workers_per_job": 2,
            "default_min_delay_s": 0.6,
            "default_max_delay_s": 1.6,
            "default_retry_max_attempts": 5,
            "default_backoff_base_s": 15.0,
            "default_backoff_cap_s": 300.0,
            "respect_retry_after": True,
        }
    )
    libraries = settings.setdefault("network", {}).setdefault("libraries", {})
    libraries.setdefault("gallica", {}).update(
        {
            "use_custom_policy": True,
            "workers_per_job": 1,
            "connect_timeout_s": 21,
            "read_timeout_s": 88,
            "min_delay_s": 2.5,
            "max_delay_s": 6.0,
            "retry_max_attempts": 3,
            "backoff_base_s": 20.0,
            "backoff_cap_s": 240.0,
            "respect_retry_after": False,
        }
    )

    policy = resolve_library_network_policy(settings, "Gallica")

    assert policy["use_custom_policy"] is True
    assert policy["workers_per_job"] == 1
    assert policy["connect_timeout_s"] == 9
    assert policy["read_timeout_s"] == 33
    assert policy["min_delay_s"] == 2.5
    assert policy["max_delay_s"] == 6.0
    assert policy["retry_max_attempts"] == 3
    assert policy["backoff_base_s"] == 20.0
    assert policy["backoff_cap_s"] == 240.0
    assert policy["respect_retry_after"] is False
