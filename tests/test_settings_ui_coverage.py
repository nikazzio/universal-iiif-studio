from studio_ui.components.settings import settings_content


def test_settings_page_exposes_critical_runtime_config_keys():
    """Settings UI should expose the main runtime knobs used by Studio and export."""
    rendered = repr(settings_content())
    expected_keys = [
        "paths.exports_dir",
        "settings.system.max_concurrent_downloads",
        "settings.system.request_timeout",
        "settings.pdf.export.default_format",
        "settings.pdf.export.default_compression",
        "settings.pdf.export.include_cover",
        "settings.pdf.export.include_colophon",
        "settings.pdf.export.description_rows",
        "settings.ui.theme_preset",
        "settings.ui.theme_primary_color",
        "settings.ui.theme_accent_color",
        "settings.ui.items_per_page",
        "settings.ui.toast_duration",
        "settings.thumbnails.page_size",
        "settings.thumbnails.page_size_options",
        "settings.thumbnails.max_long_edge_px",
        "settings.thumbnails.jpeg_quality",
        "settings.viewer.visual_filters.defaults.hue",
        "settings.viewer.visual_filters.defaults.invert",
        "settings.viewer.visual_filters.defaults.grayscale",
        "settings.viewer.visual_filters.presets.default.brightness",
        "settings.viewer.visual_filters.presets.night.contrast",
        "settings.viewer.visual_filters.presets.contrast.saturation",
        "settings.testing.run_live_tests",
        "security.allowed_origins",
    ]
    for key in expected_keys:
        assert f'name="{key}"' in rendered

    assert 'data-tab="thumbnails"' in rendered
