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

- `settings.system.download_workers` (`int`, default: `4`)
- `settings.system.ocr_concurrency` (`int`, default: `1`)
- `settings.system.request_timeout` (`int`, default: `30`)

## `settings.defaults`

- `settings.defaults.default_library` (`string`, default: `Vaticana (BAV)`)
- `settings.defaults.preferred_ocr_engine` (`string`, default: `openai`)

## `settings.ui`

- `settings.ui.theme_color` (`string`, default: `#FF4B4B`)
- `settings.ui.items_per_page` (`int`, default: `12`)
- `settings.ui.toast_duration` (`int`, default: `3000`)

## `settings.images`

- `settings.images.download_strategy` (`string[]`, default: `['max', '3000', '1740']`)
- `settings.images.iiif_quality` (`string`, default: `default`)
- `settings.images.viewer_quality` (`int`, default: `95`)
- `settings.images.ocr_quality` (`int`, default: `95`)
- `settings.images.tile_stitch_max_ram_gb` (`number`, default: `2`)

## `settings.ocr`

- `settings.ocr.ocr_engine` (`string`, optional in example config)
- `settings.ocr.kraken_enabled` (`bool`, default: `false`)

## `settings.pdf`

- `settings.pdf.viewer_dpi` (`int`, default: `150`)
- `settings.pdf.ocr_dpi` (`int`, default: `300`)
- `settings.pdf.prefer_native_pdf` (`bool`, default: `true`)
- `settings.pdf.create_pdf_from_images` (`bool`, default: `false`)

### `settings.pdf.cover`

- `settings.pdf.cover.logo_path` (`string`, default: empty)
- `settings.pdf.cover.curator` (`string`, default: empty)
- `settings.pdf.cover.description` (`string`, default: empty)

Backward compatibility:
- legacy `settings.pdf.render_dpi` is mapped in-memory to:
  - `settings.pdf.viewer_dpi`
  - `settings.pdf.ocr_dpi`

## `settings.thumbnails`

- `settings.thumbnails.max_long_edge_px` (`int`, default: `320`)
- `settings.thumbnails.jpeg_quality` (`int`, default: `70`)
- `settings.thumbnails.columns` (`int`, default: `6`)
- `settings.thumbnails.paginate_enabled` (`bool`, default: `true`)
- `settings.thumbnails.page_size` (`int`, default: `48`)
- `settings.thumbnails.default_select_all` (`bool`, default: `true`)
- `settings.thumbnails.actions_apply_to_all_default` (`bool`, default: `false`)
- `settings.thumbnails.hover_preview_enabled` (`bool`, default: `true`)
- `settings.thumbnails.hover_preview_max_long_edge_px` (`int`, default: `900`)
- `settings.thumbnails.hover_preview_jpeg_quality` (`int`, default: `82`)
- `settings.thumbnails.hover_preview_delay_ms` (`int`, default: `550`)
- `settings.thumbnails.inline_base64_max_tiles` (`int`, default: `120`)
- `settings.thumbnails.hover_preview_max_tiles` (`int`, default: `72`)

## `settings.housekeeping`

- `settings.housekeeping.temp_cleanup_days` (`int`, default: `7`)

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
