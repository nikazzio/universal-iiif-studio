# Configuration

Runtime settings live in `config.json` and are managed through `universal_iiif_core.config_manager`.

## Essential Sections

- `paths`: runtime directories (`downloads`, `exports`, `temp`, `logs`, `models`, `snippets`).
- `settings.network`: global transport defaults and per-library download policies.
- `settings.images`: IIIF fetch strategy and quality.
- `settings.pdf`: native PDF behavior, export defaults, and profile catalog.
- `settings.storage`: retention and staging-to-scans promotion policy.
- `settings.viewer.mirador`: viewer gating and OpenSeadragon tuning.

## Essential PDF Keys

- `settings.pdf.prefer_native_pdf`
- `settings.pdf.create_pdf_from_images`
- `settings.pdf.viewer_dpi`
- `settings.pdf.profiles.default`
- `settings.pdf.profiles.catalog.<profile>.image_source_mode`
- `settings.pdf.profiles.catalog.<profile>.max_parallel_page_fetch`

## Essential Storage/Viewer Keys

- `settings.storage.partial_promotion_mode` (`never|on_pause`)
- `settings.viewer.mirador.require_complete_local_images`

## Notes

- `settings.network.global.*` is always shared across libraries (no per-library timeout/concurrency override).
- `settings.network.libraries.<library>.*` applies only when `use_custom_policy=true`.
- Keep local scans balanced by default for speed and storage.
- Use export profiles for job-level quality decisions instead of changing global defaults frequently.
- Staged downloads can live in `temp_images/<doc_id>` before promotion to `scans/`.
- Segmented retries/range downloads count previously staged validated pages before final promotion.
- With `partial_promotion_mode=on_pause`, promotion on pause keeps existing scans by default and overwrites only for explicit refresh/redownload flows.

## Canonical References

- Main user guide: [DOCUMENTAZIONE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/DOCUMENTAZIONE.md)
- Full key reference: [CONFIG_REFERENCE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/CONFIG_REFERENCE.md)
- Architecture notes: [ARCHITECTURE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/ARCHITECTURE.md)
