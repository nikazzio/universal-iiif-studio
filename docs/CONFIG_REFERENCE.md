# Configuration Reference

This page is the detailed reference for the runtime `config.json` used by Scriptoria. It is meant for operators, contributors, and advanced users who need the exact keyspace and the practical runtime meaning of each configuration family.

Use [Configuration Overview](reference/configuration.md) if you want the conceptual map first. Use this page when you need to know exactly which key exists, what shape it expects, and how the application interprets it.

## Scope and Sources

This reference documents the `config.json` keyspace currently used by the application, based on:

- `src/universal_iiif_core/config_manager.py` and its runtime defaults;
- validation logic in `src/universal_iiif_core/config_validation.py`;
- `config.example.json`;
- the active Settings UI panes that expose parts of the same tree.

If a key appears in one source but not the others, this document should follow actual runtime behavior first and example files second.

## How To Read This Reference

The file is intentionally dense. A practical reading strategy is:

1. locate the top-level family you need;
2. read the notes attached to that family, not only the raw keys;
3. cross-check with the related UI pane if the key is user-editable from the web interface;
4. treat validation and migration notes as part of the contract, because Scriptoria still carries some alpha-era legacy keys.

## Runtime Validation Policy

At startup, `ConfigManager.load()` runs a non-mutating validation pass over the merged `config.json`:
- `ERROR`: invalid critical structures/types (for example malformed `paths` or `security.allowed_origins`).
- `WARNING`: deprecated keys, unknown keys, and non-fatal semantic anomalies (enum/range/reference issues).

Validation only logs diagnostics; it does **not** rewrite `config.json`.
Sensitive values (for example API keys/tokens) are never emitted in clear text by validation logs.

Deprecated keys currently flagged:
- `settings.system.max_concurrent_downloads`
- `settings.system.download_workers`
- `settings.system.request_timeout`
- `settings.system.ocr_concurrency`
- `settings.defaults.auto_generate_pdf`
- `settings.images.ocr_quality`
- `settings.pdf.ocr_dpi`
- `settings.thumbnails.columns`
- `settings.thumbnails.paginate_enabled`
- `settings.thumbnails.default_select_all`
- `settings.thumbnails.actions_apply_to_all_default`
- `settings.thumbnails.hover_preview_enabled`
- `settings.thumbnails.hover_preview_max_long_edge_px`
- `settings.thumbnails.hover_preview_jpeg_quality`
- `settings.thumbnails.hover_preview_delay_ms`
- `settings.thumbnails.inline_base64_max_tiles`
- `settings.thumbnails.hover_preview_max_tiles`
- `settings.network.tuning_steps`
- `settings.network.libraries.<library>.size_strategy_mode`
- `settings.network.libraries.<library>.size_strategy_custom`
- `settings.network.libraries.<library>.allow_max_size`
- `settings.network.libraries.<library>.iiif_quality`
- `settings.network.libraries.<library>.connect_timeout_s`
- `settings.network.libraries.<library>.read_timeout_s`

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

## `settings.network.global`

Global network settings used by the centralized `HTTPClient` for all HTTP operations.

- `settings.network.global.max_concurrent_download_jobs` (`int`, default: `2`)
  - Maximum number of download jobs (documents) running concurrently
- `settings.network.global.connect_timeout_s` (`int`, default: `10`)
  - Connection timeout for HTTP requests (used by HTTPClient)
- `settings.network.global.read_timeout_s` (`int`, default: `30`)
  - Read timeout for HTTP responses (used by HTTPClient)
- `settings.network.global.transport_retries` (`int`, default: `3`)
  - Transport-level retries for HTTP adapter
- `settings.network.global.per_host_concurrency` (`int`, default: `4`)
  - Default per-host concurrency used when library-specific policy does not override it

**Note**: These settings apply to ALL libraries and cannot be overridden per-library. For per-library customization, use `settings.network.libraries.<library>.*` fields.

## `settings.network.download`

Default download policies used when library-specific override is not enabled.

- `settings.network.download.default_workers_per_job` (`int`, default: `2`)
  - Number of concurrent workers per download job
- `settings.network.download.default_min_delay_s` (`number`, default: `0.6`)
  - Minimum delay between page requests (used for legacy download flow)
- `settings.network.download.default_max_delay_s` (`number`, default: `1.6`)
  - Maximum delay between page requests (used for legacy download flow)
- `settings.network.download.default_retry_max_attempts` (`int`, default: `5`)
  - Maximum retry attempts for failed requests
- `settings.network.download.default_backoff_base_s` (`number`, default: `15.0`)
  - Base wait time for exponential backoff (HTTPClient)
- `settings.network.download.default_backoff_cap_s` (`number`, default: `300.0`)
  - Maximum wait time cap for exponential backoff (HTTPClient)
- `settings.network.download.respect_retry_after` (`bool`, default: `true`)
  - Whether to respect `Retry-After` headers from servers (HTTPClient)

## `settings.network.libraries.<library>`

Libraries supported: `gallica`, `vaticana`, `bodleian`, `institut_de_france`, `estense`, `internet_culturale` (BETA), `unknown`.

**HTTPClient Integration**: These settings are used by the centralized `HTTPClient` class for per-library network policies (rate limiting, retry, backoff, concurrency).

Global-only fields (never overridden by library):
- `settings.network.global.max_concurrent_download_jobs`
- `settings.network.global.connect_timeout_s`
- `settings.network.global.read_timeout_s`
- `settings.network.global.transport_retries`

Library override fields (used only when `use_custom_policy=true`):
- `enabled` (`bool`, default: `true`)
- `use_custom_policy` (`bool`, default: `true` for `gallica` and `internet_culturale`, otherwise `false`)
  - When `true`, library-specific settings override global defaults
  - When `false`, global defaults from `settings.network.download.*` are used
- `workers_per_job` (`int`, `1..8`)
  - Number of concurrent workers for this library's downloads
- `min_delay_s` / `max_delay_s` (`number`)
  - Delay range between page requests (legacy download flow)
- `retry_max_attempts` (`int`)
  - Maximum retry attempts (HTTPClient)
- `backoff_base_s` / `backoff_cap_s` (`number`)
  - Exponential backoff parameters (HTTPClient)
- `cooldown_on_403_s` / `cooldown_on_429_s` (`int`)
  - Cooldown period after receiving 403/429 errors (HTTPClient rate limiter)
- `burst_window_s` / `burst_max_requests` (`int`)
  - Sliding window rate limiting parameters (HTTPClient)
  - Example: Gallica uses 60s window with 4 max requests (4 req/min)
  - Example: Default uses 60s window with 20 max requests (20 req/min)
- `per_host_concurrency` (`int`)
  - Maximum concurrent requests per host (HTTPClient semaphore)
  - Example: Gallica uses 2, others use 4 (default)
- `respect_retry_after` (`bool`)
  - Whether to honor `Retry-After` HTTP headers (HTTPClient)
- `prewarm_viewer` (`bool`)
  - Whether to prewarm viewer URLs (legacy Session usage)
- `send_referer_header` (`bool`)
  - Whether to send Referer header
- `send_origin_header` (`bool`)
  - Whether to send Origin header

Behavior notes:
- if `use_custom_policy=false`, library override values are ignored and runtime uses `settings.network.download.*`.
- `connect_timeout_s` / `read_timeout_s` are global-only and must be set under `settings.network.global`.
- **Gallica strictest example**: `burst_max_requests=4`, `burst_window_s=60`, `per_host_concurrency=2`, `backoff_base_s=20`, `cooldown_on_403_s=120`, `cooldown_on_429_s=300`.

## `settings.defaults`

- `settings.defaults.default_library` (`string`, default: `Vaticana`)
- `settings.defaults.preferred_ocr_engine` (`string`, default: `openai`)

## `settings.library`

- `settings.library.default_mode` (`string`, default: `operativa`)
  - allowed: `operativa` | `archivio`
  - Determines the initial view mode displayed in the Library interface.
  - `operativa` opens the working view oriented around active study items.
  - `archivio` opens the archival view used for retained items and completed workspaces.

## `settings.ui`

- `settings.ui.theme_preset` (`string`, default: `rosewater`)
- `settings.ui.theme_primary_color` (`string`, default: `#7B8CC7`)
- `settings.ui.theme_accent_color` (`string`, default: `#E8A6B6`)
- `settings.ui.items_per_page` (`int`, default: `12`)
- `settings.ui.toast_duration` (`int`, default: `3000`)
- `settings.ui.studio_recent_max_items` (`int`, default: `8`, allowed range: `1..20`)
- `settings.ui.polling.download_manager_interval_seconds` (`int`, default: `3`, allowed range: `1..30`)
- `settings.ui.polling.download_status_interval_seconds` (`int`, default: `3`, allowed range: `1..30`)

Notes:
- `theme_color` is a legacy input accepted only during migration; `ConfigManager` rewrites it in-memory to `theme_accent_color` and removes the old key from the loaded tree.
- Download polling values are used by Discovery HTMX fragments only (Download Manager and single status card).

## `settings.images`

- `settings.images.download_strategy_mode` (`string`, default: `balanced`)
  - allowed: `balanced|quality_first|fast|archival|custom`
- `settings.images.download_strategy_custom` (`string[]`, default: `['3000', '1740', 'max']`)
  - used only when `download_strategy_mode=custom`
- `settings.images.stitch_mode_default` (`string`, default: `auto_fallback`)
  - allowed: `auto_fallback|direct_only|stitch_only`
- `settings.images.iiif_quality` (`string`, default: `default`)
  - segment used in IIIF URLs: `/full/{size}/0/{quality}.jpg`
- `settings.images.probe_remote_max_resolution` (`bool`, default: `true`)
- `settings.images.tile_stitch_max_ram_gb` (`number`, default: `2`)
- `settings.images.local_optimize.max_long_edge_px` (`int`, default: `2600`, allowed range: `512..12000`)
- `settings.images.local_optimize.jpeg_quality` (`int`, default: `82`, allowed range: `10..100`)

Runtime notes:
- `download_strategy_mode` defines ordered direct size attempts before tile stitching.
- The Studio `Std` button uses the same strategy as a normal volume download.
- `download_strategy_custom` is an ordered attempt list (`3000`, `1740`, `max`), not a guarantee that `max` is larger than every explicit numeric attempt.
- `download_strategy` is not a stable persisted config key anymore. Earlier configs may still contain it, but `ConfigManager` drops it and runtime recomputes the effective direct-attempt sequence from `download_strategy_mode` plus `download_strategy_custom`.
- `stitch_mode_default` controls whether the standard volume strategy can fall back to stitching after direct attempts.
- `iiif_quality` applies to normal page downloads and temporary remote high-res export fetches.
- `probe_remote_max_resolution` drives the Studio thumbnail “Remote” informational line by probing `info.json`; it does not change download behavior.
- local optimize keys are used by `POST /api/studio/export/optimize_scans` (in-place lossy rewrite of `scans/`).

## `settings.ocr`

- `settings.ocr.ocr_engine` (`string`, default: `openai`)
  - allowed: `openai|anthropic|google_vision|kraken|huggingface`
- `settings.ocr.kraken_enabled` (`bool`, default: `false`)

Notes:
- `settings.defaults.preferred_ocr_engine` seeds workflows that have not selected an engine explicitly.
- `settings.ocr.ocr_engine` is the operational OCR engine used by Studio OCR flows.
- The current Settings UI exposes `openai`, `anthropic`, `google_vision`, and `kraken`. Validation and OCR runtime also accept `huggingface`, so direct `config.json` editing can still select it.

## `settings.pdf`

- `settings.pdf.viewer_dpi` (`int`, default: `150`)
- `settings.pdf.viewer_jpeg_quality` (`int`, default: `95`)
- `settings.pdf.prefer_native_pdf` (`bool`, default: `true`)
- `settings.pdf.create_pdf_from_images` (`bool`, default: `false`)

Notes:
- `viewer_dpi`, `viewer_jpeg_quality`, `prefer_native_pdf`, and `create_pdf_from_images` are edited from the Settings `Processing Core` pane even though they live under `settings.pdf.*`.
- `prefer_native_pdf=true` means Scriptoria will prefer a source PDF exposed by the upstream manifest when that produces a cleaner local acquisition path and no page subset has been requested.
- `create_pdf_from_images=true` adds a compiled PDF artifact from local images when a native PDF was not used.

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
- Studio item Output only selects one profile for the current job.
- Studio item Output keeps profile selection as the primary control; job-specific overrides are optional and collapsed by default.
- `max_parallel_page_fetch` is actively used for parallel remote high-res page staging.
- `document_overrides` still exists in runtime because `pdf_profiles.py` can persist per-document override state, but it is not the main operator-facing control surface anymore.

Backward compatibility:
- legacy `settings.pdf.render_dpi` is mapped in-memory to:
  - `settings.pdf.viewer_dpi`
  - `settings.pdf.ocr_dpi` (legacy compatibility only; not part of active UI/runtime controls)

## `settings.thumbnails`

- `settings.thumbnails.max_long_edge_px` (`int`, default: `320`)
- `settings.thumbnails.jpeg_quality` (`int`, default: `70`)
- `settings.thumbnails.page_size` (`int`, default: `48`)
- `settings.thumbnails.page_size_options` (`int[]`, default: `[24, 48, 72, 96]`)
- `settings.thumbnails.studio_page_size_max` (`int`, default: `72`)

Notes:
- `page_size` and every entry in `page_size_options` are expected to stay in the `1..120` range.
- `studio_page_size_max` is a runtime guard used by Studio thumbnail routes to cap oversized page-size requests even if the options list contains larger values.

## `settings.housekeeping`

- `settings.housekeeping.temp_cleanup_days` (`int`, default: `7`)
  - Number of days before temporary files are eligible for cleanup
  - Applied to files in `paths.temp_dir` during housekeeping operations
  - Files older than this threshold may be automatically removed to free disk space

## `settings.storage`

- `settings.storage.exports_retention_days` (`int`, default: `30`)
- `settings.storage.thumbnails_retention_days` (`int`, default: `14`)
- `settings.storage.highres_temp_retention_hours` (`int`, default: `6`)
- `settings.storage.auto_prune_on_startup` (`bool`, default: `false`)
- `settings.storage.max_exports_per_item` (`int`, default: `5`)
- `settings.storage.partial_promotion_mode` (`string`, default: `never`)
  - allowed: `never` | `on_pause`
- `settings.storage.remote_cache.max_bytes` (`int`, default: `104857600`, allowed range: `1MB..20GB`)
- `settings.storage.remote_cache.retention_hours` (`int`, default: `72`, allowed range: `1..8760`)
- `settings.storage.remote_cache.max_items` (`int`, default: `2000`, allowed range: `100..100000`)

Runtime notes:
- `exports_retention_days`: global pruning on export execution and optional startup prune.
- `thumbnails_retention_days`: pruning applied when Studio Export thumbnails are generated.
- `highres_temp_retention_hours`: pruning of temporary remote high-res staging folders.
- `auto_prune_on_startup`: enables startup pruning for exports + high-res temp.
- `remote_cache.*`: pruning policy for persistent per-item remote resolution cache (`data/remote_resolution_cache.json`).
- `partial_promotion_mode`: promotes validated staged pages from temp to scans only when a running download is paused (`on_pause`); existing scans are overwritten only for explicit refresh/redownload jobs.
- staged completeness checks count validated pages already in `temp_images/<doc_id>` plus current-run pages (segmented retry/range runs converge correctly).

## `settings.logging`

- `settings.logging.level` (`string`, default: `INFO`)
  - allowed: `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`
  - Controls logging verbosity across the application
  - `DEBUG`: detailed logging for troubleshooting (significantly increases log file size)
  - `INFO`: standard operational messages (recommended for normal usage)
  - `WARNING`: only warnings and errors
  - `ERROR`: only errors and critical issues
  - `CRITICAL`: only critical failures

## `settings.testing`

- `settings.testing.run_live_tests` (`bool`, default: `false`)
  - Enables tests that make real API calls to external services during test suite execution
  - ⚠️  **Warning**: Requires valid API keys configured in `api_keys` section
  - ⚠️  **Warning**: Consumes API quota from your OpenAI, Anthropic, Google Vision, and HuggingFace accounts
  - Only needed for development/CI environments; safe to keep `false` for normal usage
  - When `false`, tests requiring network access are automatically skipped

## `settings.viewer.mirador`

- `settings.viewer.mirador.require_complete_local_images` (`bool`, default: `true`)
  - Gates local Studio viewer when local page availability is incomplete.
  - When `true`: Studio uses **Remote Mode** for incomplete downloads (Mirador loads original manifest from library server, fetches images on-demand).
  - When `false`: Studio prefers **Local Mode** even for incomplete downloads (displays only available local pages).
  - User can override with `?allow_remote_preview=true` URL parameter to force Remote Mode.
  - **Remote Mode**: Shows ALL pages, requires internet, useful for preview during download.
  - **Local Mode**: Shows only downloaded pages, works offline, default for complete downloads.

## `settings.viewer.source_policy`

- `settings.viewer.source_policy.saved_mode` (`string`, default: `remote_first`)
  - allowed: `remote_first` | `local_first`
  - controls Studio source mode for `saved` items without full local coverage.

## `settings.viewer.mirador.openSeadragonOptions`

- `settings.viewer.mirador.openSeadragonOptions.maxZoomPixelRatio` (`number`, default: `5`)
- `settings.viewer.mirador.openSeadragonOptions.maxZoomLevel` (`number`, default: `25`)
- `settings.viewer.mirador.openSeadragonOptions.minZoomLevel` (`number`, default: `0.35`)

Notes:
- These values are presented in the Settings `Viewer > Zoom & Navigation` pane.
- They shape the feel of the Mirador/OpenSeadragon canvas rather than the downloaded image quality itself.

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

## `settings.discovery`

Discovery search configuration. Editable from Settings > Discovery tab in the web UI.

- `max_results_per_provider` (`int`, default: `20`)
  - Maximum number of results returned by each search provider per query.
  - Clamped to [1, 50] at runtime and on save.
  - For paginatable providers (Archive.org, Harvard, LOC, Gallica, Estense, Internet Culturale (BETA)), additional results can be loaded via the "Carica altri risultati" button.
  - Non-paginatable providers (Vatican, Bodleian, Cambridge, Heidelberg, Institut, e-codices) return at most this many results from a single API call.
  - For Internet Culturale (BETA) the upstream page size is fixed at 20 regardless of `max_results_per_provider`; the "has more" check relies on the authoritative `totalPages` parsed from the HTML instead of the result cap.

## Migration Notes

Scriptoria is still carrying a small amount of alpha-era config migration logic. The important consequence is that a historical `config.json` may continue to load even after keys have moved.

Currently migrated in-memory:

- `settings.system.max_concurrent_downloads` -> `settings.network.global.max_concurrent_download_jobs`
- `settings.system.download_workers` -> `settings.network.download.default_workers_per_job`
- `settings.system.request_timeout` -> `settings.network.global.connect_timeout_s` and `settings.network.global.read_timeout_s`
- `settings.pdf.render_dpi` -> `settings.pdf.viewer_dpi` and legacy `settings.pdf.ocr_dpi`
- `settings.images.viewer_quality` -> `settings.pdf.viewer_jpeg_quality`
- `settings.ui.theme_color` -> `settings.ui.theme_accent_color`
- `settings.images.download_strategy` -> removed and recomputed at runtime

This migration is non-destructive at runtime. It keeps old configs working, but the canonical file shape for new documentation and new edits is the one described in the sections above.
