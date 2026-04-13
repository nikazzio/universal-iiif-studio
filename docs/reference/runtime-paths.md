# Runtime Paths

Scriptoria should not rely on hardcoded runtime directories. Paths must be resolved through `ConfigManager`.

## Main Runtime Areas

- downloads: local working pages and document assets;
- exports: generated output artifacts;
- temp: staging, temporary image work, and short-lived export data;
- models: OCR or related local model data;
- logs: runtime logs;
- snippets: local text fragments and related working material.

## Current Defaults

Default path values come from `DEFAULT_CONFIG_JSON` in `universal_iiif_core.config_manager`:

- `data/local/downloads`
- `data/local/exports`
- `data/local/temp_images`
- `data/local/models`
- `data/local/logs`
- `data/local/snippets`

## Practical Rule

If a document or guide needs to mention a runtime path, it should describe the path family and then point readers to configuration, not imply that the default path is permanent.

## Related Docs

- [Configuration Overview](configuration.md)
- [Storage Model](../explanation/storage-model.md)
