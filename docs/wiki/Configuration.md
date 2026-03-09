# Configuration

Runtime settings live in `config.json` and are managed through `universal_iiif_core.config_manager`.

## Essential Sections

- `paths`: runtime directories (`downloads`, `exports`, `temp`, `logs`, `models`, `snippets`).
- `settings.network.global`: global HTTP transport (timeout, retries, max concurrent jobs).
- `settings.network.download`: default download policies (workers, delays, retry, backoff).
- `settings.network.libraries.<library>`: per-library network policies for HTTPClient (rate limiting, concurrency, backoff - e.g., Gallica has stricter limits).
- `settings.images`: IIIF fetch strategy and quality.
- `settings.pdf`: native PDF behavior, export defaults, and profile catalog.
- `settings.storage`: retention and staging-to-scans promotion policy.
- `settings.viewer`: mirador gating/source policy and OpenSeadragon tuning.

## Essential PDF Keys

- `settings.pdf.prefer_native_pdf`
- `settings.pdf.create_pdf_from_images`
- `settings.pdf.viewer_dpi`
- `settings.pdf.profiles.default`
- `settings.pdf.profiles.catalog.<profile>.image_source_mode`
- `settings.pdf.profiles.catalog.<profile>.max_parallel_page_fetch`

## Essential Storage/Viewer Keys

- `settings.storage.partial_promotion_mode` (`never|on_pause`)
- `settings.storage.remote_cache.max_bytes|retention_hours|max_items`
- `settings.viewer.mirador.require_complete_local_images` (default: `true` - gates viewer until complete; set `false` or use `?allow_remote_preview=true` for remote preview mode)
- `settings.viewer.source_policy.saved_mode` (`remote_first|local_first`)

## Essential Network/HTTP Client Keys

- `settings.network.global.max_concurrent_download_jobs` (default: `2`)
- `settings.network.global.connect_timeout_s` / `read_timeout_s` (global timeout for all libraries)
- `settings.network.download.default_retry_max_attempts` / `default_backoff_base_s` (default retry/backoff)
- `settings.network.libraries.<library>.use_custom_policy` (enable per-library overrides)
- `settings.network.libraries.<library>.burst_max_requests` / `burst_window_s` (rate limiting - e.g., Gallica: 4 req/60s)
- `settings.network.libraries.<library>.per_host_concurrency` (max parallel requests per host - e.g., Gallica: 2, others: 4)

## Essential Local Optimization Keys

- `settings.images.local_optimize.max_long_edge_px`
- `settings.images.local_optimize.jpeg_quality`

## Notes

- `settings.network.global.*` is always shared across libraries (no per-library timeout/concurrency override).
- `settings.network.libraries.<library>.*` applies only when `use_custom_policy=true`.
- HTTPClient automatically applies per-library rate limiting and backoff (Gallica: 4 req/min, others: 20 req/min).
- Keep local scans balanced by default for speed and storage.
- Use export profiles for job-level quality decisions instead of changing global defaults frequently.
- Staged downloads can live in `temp_images/<doc_id>` before promotion to `scans/`.
- Segmented retries/range downloads count previously staged validated pages before final promotion.
- With `partial_promotion_mode=on_pause`, promotion on pause keeps existing scans by default and overwrites only for explicit refresh/redownload flows.
- Mirador viewing modes: Remote Mode (incomplete downloads, fetches images on-demand) vs Local Mode (complete downloads, offline-capable).

## Canonical References

- Main user guide: [DOCUMENTAZIONE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/DOCUMENTAZIONE.md)
- Full key reference: [CONFIG_REFERENCE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/CONFIG_REFERENCE.md)
- Architecture notes: [ARCHITECTURE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/ARCHITECTURE.md)
