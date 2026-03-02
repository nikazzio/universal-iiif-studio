# Configuration

Runtime settings live in `config.json` and are managed through `universal_iiif_core.config_manager`.

## Key Sections

- `paths`: runtime directories (`downloads`, `exports`, `temp`, `logs`, `models`, `snippets`).
- `settings.images`: IIIF fetch strategy and quality.
- `settings.pdf`: native PDF behavior, export defaults, and profile catalog.
- `settings.storage`: retention and pruning policies.
- `settings.viewer`: Mirador zoom options and visual filter presets.

## High-Value PDF Keys

- `settings.pdf.prefer_native_pdf`
- `settings.pdf.create_pdf_from_images`
- `settings.pdf.viewer_dpi`
- `settings.pdf.profiles.default`
- `settings.pdf.profiles.catalog.<profile>.image_source_mode`
- `settings.pdf.profiles.catalog.<profile>.max_parallel_page_fetch`

## Detailed References

- Main user guide: `docs/DOCUMENTAZIONE.md`
- Full key reference: `docs/CONFIG_REFERENCE.md`
- Architecture notes: `docs/ARCHITECTURE.md`
