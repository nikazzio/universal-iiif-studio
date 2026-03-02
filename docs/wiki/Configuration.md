# Configuration

Runtime settings live in `config.json` and are managed through `universal_iiif_core.config_manager`.

## Essential Sections

- `paths`: runtime directories (`downloads`, `exports`, `temp`, `logs`, `models`, `snippets`).
- `settings.images`: IIIF fetch strategy and quality.
- `settings.pdf`: native PDF behavior, export defaults, and profile catalog.

## Essential PDF Keys

- `settings.pdf.prefer_native_pdf`
- `settings.pdf.create_pdf_from_images`
- `settings.pdf.viewer_dpi`
- `settings.pdf.profiles.default`
- `settings.pdf.profiles.catalog.<profile>.image_source_mode`
- `settings.pdf.profiles.catalog.<profile>.max_parallel_page_fetch`

## Notes

- Keep local scans balanced by default for speed and storage.
- Use export profiles for job-level quality decisions instead of changing global defaults frequently.

## Canonical References

- Main user guide: [DOCUMENTAZIONE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/DOCUMENTAZIONE.md)
- Full key reference: [CONFIG_REFERENCE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/CONFIG_REFERENCE.md)
- Architecture notes: [ARCHITECTURE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/ARCHITECTURE.md)
