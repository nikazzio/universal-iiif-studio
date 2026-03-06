from studio_ui.components.settings import settings_content


def test_settings_page_exposes_critical_runtime_config_keys():
    """Settings UI should expose the main runtime knobs used by Studio and export."""
    rendered = repr(settings_content())
    expected_keys = [
        "paths.exports_dir",
        "settings.network.global.max_concurrent_download_jobs",
        "settings.network.global.connect_timeout_s",
        "settings.network.download.default_workers_per_job",
        "settings.network.download.default_retry_max_attempts",
        "settings.network.libraries.gallica.use_custom_policy",
        "settings.network.libraries.gallica.workers_per_job",
        "settings.pdf.export.default_format",
        "settings.pdf.export.default_compression",
        "settings.pdf.profiles.default",
        "settings.pdf.export.include_cover",
        "settings.pdf.export.include_colophon",
        "settings.pdf.export.description_rows",
        "settings.pdf.profiles.editor.key",
        "settings.pdf.profiles.editor.max_parallel_page_fetch",
        "settings.pdf.profiles.editor.action",
        "settings.pdf.profiles.editor.selected",
        "settings.ui.theme_preset",
        "settings.ui.theme_primary_color",
        "settings.ui.theme_accent_color",
        "settings.library.default_mode",
        "settings.ui.items_per_page",
        "settings.ui.toast_duration",
        "settings.ui.polling.download_manager_interval_seconds",
        "settings.ui.polling.download_status_interval_seconds",
        "settings.images.download_strategy_mode",
        "settings.images.download_strategy_custom",
        "settings.images.iiif_quality",
        "settings.images.probe_remote_max_resolution",
        "settings.images.local_optimize.max_long_edge_px",
        "settings.images.local_optimize.jpeg_quality",
        "settings.ocr.ocr_engine",
        "settings.thumbnails.page_size",
        "settings.thumbnails.page_size_options",
        "settings.thumbnails.max_long_edge_px",
        "settings.thumbnails.jpeg_quality",
        "settings.storage.exports_retention_days",
        "settings.storage.thumbnails_retention_days",
        "settings.storage.max_exports_per_item",
        "settings.storage.partial_promotion_mode",
        "settings.storage.remote_cache.max_bytes",
        "settings.storage.remote_cache.retention_hours",
        "settings.storage.remote_cache.max_items",
        "settings.viewer.visual_filters.defaults.hue",
        "settings.viewer.visual_filters.defaults.invert",
        "settings.viewer.visual_filters.defaults.grayscale",
        "settings.viewer.mirador.require_complete_local_images",
        "settings.viewer.source_policy.saved_mode",
        "settings.viewer.visual_filters.presets.default.brightness",
        "settings.viewer.visual_filters.presets.night.contrast",
        "settings.viewer.visual_filters.presets.contrast.saturation",
        "settings.testing.run_live_tests",
        "security.allowed_origins",
    ]
    for key in expected_keys:
        assert f'name="{key}"' in rendered

    assert "Imaging Pipeline" in rendered
    assert 'data-images-tab-btn="images"' in rendered
    assert 'data-images-tab-btn="thumbnails"' in rendered
    assert 'data-images-tab-btn="ocr"' in rendered
    assert 'data-network-tab-btn="gallica"' in rendered
    assert 'data-network-tab-btn="vaticana"' in rendered
    assert 'data-network-tab-btn="bodleian"' in rendered
    assert 'data-network-tab-btn="institut_de_france"' in rendered
    assert "Gallica Safe" not in rendered
    assert "Other Libraries" not in rendered
    assert 'data-tab="network"' in rendered
