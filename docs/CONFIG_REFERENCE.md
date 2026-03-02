# Configuration Reference

Single source of truth for runtime configuration keys used by this project.

## Scope and Sources

This reference documents the full `config.json` keyspace currently used by the app, based on:
- `src/universal_iiif_core/config_manager.py` (`DEFAULT_CONFIG_JSON`)
- `config.example.json`

If a key appears in one source but not the other, keep this document aligned with runtime behavior in `ConfigManager`.

## Top-Level Schema

```text
config.json
├─ paths
├─ security
├─ api_keys
└─ settings
```

## `paths`

- `paths.downloads_dir` (`string`, default: `data/local/downloads`)
- `paths.exports_dir` (`string`, default: `data/local/exports`)
- `paths.temp_dir` (`string`, default: `data/local/temp_images`)
- `paths.models_dir` (`string`, default: `data/local/models`)
- `paths.logs_dir` (`string`, default: `data/local/logs`)
- `paths.snippets_dir` (`string`, default: `data/local/snippets`)

Notes:
- Relative paths are resolved from current working directory.
- Directories are created on demand by `ConfigManager` getters.

## `security`

- `security.allowed_origins` (`string[]`, example defaults)
  - `http://localhost:8000`
  - `http://127.0.0.1:8000`

## `api_keys`

- `api_keys.openai` (`string`)
- `api_keys.anthropic` (`string`)
- `api_keys.google_vision` (`string`)
- `api_keys.huggingface` (`string`)

## `settings.system`

- `settings.system.max_concurrent_downloads` (`int`, default: `2`)

## `settings.defaults`

- `settings.defaults.default_library` (`string`, default: `Vaticana`)
- `settings.defaults.preferred_ocr_engine` (`string`, default: `openai`)

## `settings.library`

- `settings.library.default_mode` (`string`, default: `operativa`)

## `settings.ui`

- `settings.ui.theme_preset` (`string`, default: `rosewater`)
- `settings.ui.theme_primary_color` (`string`, default: `#7B8CC7`)
- `settings.ui.theme_accent_color` (`string`, default: `#E8A6B6`)
- `settings.ui.theme_color` (`string`, default: `#E8A6B6`)
- `settings.ui.items_per_page` (`int`, default: `12`)
- `settings.ui.toast_duration` (`int`, default: `3000`)

Notes:
- `theme_color` is kept for backward compatibility; current UI uses primary/accent keys and preset.

## `settings.images`

- `settings.images.download_strategy_mode` (`string`, default: `balanced`)
  - allowed: `balanced|quality_first|fast|archival|custom`
- `settings.images.download_strategy_custom` (`string[]`, default: `['3000', '1740', 'max']`)
  - used only when `download_strategy_mode=custom`
- `settings.images.download_strategy` (`string[]`, default: `['3000', '1740', 'max']`)
  - canonical resolved strategy used at runtime (materialized from mode/custom)
- `settings.images.iiif_quality` (`string`, default: `default`)
  - segment used in IIIF URLs: `/full/{size}/0/{quality}.jpg`
- `settings.images.viewer_quality` (`int`, default: `95`)
- `settings.images.probe_remote_max_resolution` (`bool`, default: `true`)
- `settings.images.tile_stitch_max_ram_gb` (`number`, default: `2`)

Runtime notes:
- `download_strategy_mode` defines ordered size attempts before tile stitching.
- `iiif_quality` applies to normal page downloads and temporary remote high-res export fetches.
- `probe_remote_max_resolution` enables `info.json` probing for Studio Export thumbnails.

## `settings.ocr`

- `settings.ocr.ocr_engine` (`string`, optional in example config)
- `settings.ocr.kraken_enabled` (`bool`, default: `false`)

## `settings.pdf`

- `settings.pdf.viewer_dpi` (`int`, default: `150`)
- `settings.pdf.prefer_native_pdf` (`bool`, default: `true`)
- `settings.pdf.create_pdf_from_images` (`bool`, default: `false`)

### `settings.pdf.export`

- `settings.pdf.export.default_format` (`string`, default: `pdf_images`)
- `settings.pdf.export.default_compression` (`string`, default: `Standard`)
- `settings.pdf.export.include_cover` (`bool`, default: `true`)
- `settings.pdf.export.include_colophon` (`bool`, default: `true`)
- `settings.pdf.export.description_rows` (`int`, default: `3`, UI clamp `2..8`)

### `settings.pdf.cover`

- `settings.pdf.cover.logo_path` (`string`, default: empty)
- `settings.pdf.cover.curator` (`string`, default: empty)
- `settings.pdf.cover.description` (`string`, default: empty)

### `settings.pdf.profiles`

- `settings.pdf.profiles.default` (`string`, default: `balanced`)
- `settings.pdf.profiles.catalog` (`object`, named profile map)
  - built-in keys: `balanced`, `high_quality`, `archival_highres`, `lightweight`
  - profile fields:
    - `label` (`string`)
    - `compression` (`High-Res|Standard|Light`)
    - `include_cover` (`bool`)
    - `include_colophon` (`bool`)
    - `image_source_mode` (`local_balanced|local_highres|remote_highres_temp`)
    - `image_max_long_edge_px` (`int`, `0` means original size)
    - `jpeg_quality` (`int`, `40..100`)
    - `force_remote_refetch` (`bool`)
    - `cleanup_temp_after_export` (`bool`)
    - `max_parallel_page_fetch` (`int`, `1..8`)
- `settings.pdf.profiles.document_overrides` (`object`, legacy; retained for backward compatibility)

UI/runtime notes:
- Profile creation/edit/delete is handled from **Settings > PDF Export**.
- In Settings, the profile catalog uses one selector with `Nuovo profilo...` for creation and a dedicated delete action.
- Studio item Export only selects one profile for the current job.
- Studio item Export keeps profile selection as the primary control; per-job overrides are optional and collapsed by default.
- `max_parallel_page_fetch` is actively used for parallel remote high-res page staging.

Backward compatibility:
- legacy `settings.pdf.render_dpi` is mapped in-memory to:
  - `settings.pdf.viewer_dpi`
  - `settings.pdf.ocr_dpi` (legacy compatibility only; not part of active UI/runtime controls)

## `settings.thumbnails`

- `settings.thumbnails.max_long_edge_px` (`int`, default: `320`)
- `settings.thumbnails.jpeg_quality` (`int`, default: `70`)
- `settings.thumbnails.page_size` (`int`, default: `48`)
- `settings.thumbnails.page_size_options` (`int[]`, default: `[24, 48, 72, 96]`)

## `settings.housekeeping`

- `settings.housekeeping.temp_cleanup_days` (`int`, default: `7`)

## `settings.storage`

- `settings.storage.exports_retention_days` (`int`, default: `30`)
- `settings.storage.thumbnails_retention_days` (`int`, default: `14`)
- `settings.storage.highres_temp_retention_hours` (`int`, default: `6`)
- `settings.storage.auto_prune_on_startup` (`bool`, default: `false`)
- `settings.storage.max_exports_per_item` (`int`, default: `5`)

Runtime notes:
- `exports_retention_days`: global pruning on export execution and optional startup prune.
- `thumbnails_retention_days`: pruning applied when Studio Export thumbnails are generated.
- `highres_temp_retention_hours`: pruning of temporary remote high-res staging folders.
- `auto_prune_on_startup`: enables startup pruning for exports + high-res temp.

## `settings.logging`

- `settings.logging.level` (`string`, default: `INFO`)

## `settings.testing`

- `settings.testing.run_live_tests` (`bool`, default: `false`)

## `settings.viewer.mirador.openSeadragonOptions`

- `settings.viewer.mirador.openSeadragonOptions.maxZoomPixelRatio` (`number`, default: `5`)
- `settings.viewer.mirador.openSeadragonOptions.maxZoomLevel` (`number`, default: `25`)
- `settings.viewer.mirador.openSeadragonOptions.minZoomLevel` (`number`, default: `0.35`)

## `settings.viewer.visual_filters.defaults`

- `settings.viewer.visual_filters.defaults.brightness` (`number`, default: `1.0`)
- `settings.viewer.visual_filters.defaults.contrast` (`number`, default: `1.0`)
- `settings.viewer.visual_filters.defaults.saturation` (`number`, default: `1.0`)
- `settings.viewer.visual_filters.defaults.hue` (`number`, default: `0`)
- `settings.viewer.visual_filters.defaults.invert` (`bool`, default: `false`)
- `settings.viewer.visual_filters.defaults.grayscale` (`bool`, default: `false`)

## `settings.viewer.visual_filters.presets`

### `settings.viewer.visual_filters.presets.default`

- `brightness` (`number`, default: `1.0`)
- `contrast` (`number`, default: `1.0`)
- `saturation` (`number`, default: `1.0`)
- `hue` (`number`, default: `0`)
- `invert` (`bool`, default: `false`)
- `grayscale` (`bool`, default: `false`)

### `settings.viewer.visual_filters.presets.night`

- `brightness` (`number`, default: `0.9`)
- `contrast` (`number`, default: `1.3`)
- `saturation` (`number`, default: `0.9`)
- `hue` (`number`, default: `0`)
- `invert` (`bool`, default: `false`)
- `grayscale` (`bool`, default: `false`)

### `settings.viewer.visual_filters.presets.contrast`

- `brightness` (`number`, default: `1.05`)
- `contrast` (`number`, default: `1.5`)
- `saturation` (`number`, default: `1.2`)
- `hue` (`number`, default: `0`)
- `invert` (`bool`, default: `false`)
- `grayscale` (`bool`, default: `false`)
