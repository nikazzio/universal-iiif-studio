# Configuration

Runtime settings live in `config.json` and are resolved through `universal_iiif_core.config_manager`.

## Main Sections

- `paths` for runtime directories.
- `security` for allowed origins.
- `api_keys` for OCR and remote service credentials.
- `settings.network.*` for transport behavior.
- `settings.images.*` for page download strategy and local optimization.
- `settings.pdf.*` for native PDF behavior and export profiles.
- `settings.storage.*` for retention and staged-page promotion.
- `settings.viewer.*` for read-source policy and Mirador behavior.
- `settings.discovery.*` for search result sizing.

## High-Impact Keys

- `settings.network.global.max_concurrent_download_jobs`
- `settings.network.global.connect_timeout_s`
- `settings.network.global.read_timeout_s`
- `settings.network.global.transport_retries`
- `settings.network.global.per_host_concurrency`
- `settings.network.download.default_retry_max_attempts`
- `settings.images.download_strategy_mode`
- `settings.images.stitch_mode_default`
- `settings.pdf.prefer_native_pdf`
- `settings.pdf.create_pdf_from_images`
- `settings.pdf.profiles.default`
- `settings.storage.partial_promotion_mode`
- `settings.viewer.mirador.require_complete_local_images`

## Practical Notes

- Keep local workflows balanced by default.
- Use export profiles for quality changes instead of repeatedly editing global settings.
- Treat `download_strategy_custom` as an ordered attempt list, not a promise that one value is always the largest real image.
- Remote preview and local-only viewing behavior are controlled by the combination of local availability, config policy, and explicit URL override.

## Canonical References

- [Documentation Hub](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/index.md)
- [User Guide](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/DOCUMENTAZIONE.md)
- [Configuration Reference](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/CONFIG_REFERENCE.md)
