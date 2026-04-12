from studio_ui.components.settings import settings_content


def test_settings_page_exposes_critical_runtime_config_keys():
    """Settings UI should expose the main runtime knobs used by Studio and export.

    Smoke-tests a representative subset of config keys across each settings
    domain to catch accidental removals without being fragile to additions.
    """
    rendered = repr(settings_content())
    critical_keys = [
        "paths.exports_dir",
        "settings.network.global.max_concurrent_download_jobs",
        "settings.network.download.default_workers_per_job",
        "settings.pdf.export.default_format",
        "settings.pdf.profiles.default",
        "settings.ui.theme_preset",
        "settings.images.download_strategy_mode",
        "settings.storage.exports_retention_days",
        "settings.viewer.visual_filters.defaults.hue",
        "settings.testing.run_live_tests",
        "security.allowed_origins",
    ]
    for key in critical_keys:
        assert f'name="{key}"' in rendered, f"Missing settings key: {key}"

    assert 'data-tab="network"' in rendered
    assert 'data-images-tab-btn="images"' in rendered
    assert 'data-network-tab-btn="gallica"' in rendered
    assert "syncCustomStrategyVisibility" in rendered
