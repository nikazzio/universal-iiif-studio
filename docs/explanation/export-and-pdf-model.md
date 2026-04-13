# Export And PDF Model

Export in Scriptoria is profile-driven and storage-aware.

## Main Decisions

- prefer native PDF when available and configured;
- fall back to IIIF image download when native PDF is unavailable or disabled;
- optionally build a PDF from images;
- allow temporary remote high-resolution sourcing for export jobs that need it.

## Why Profiles Matter

Profiles keep export behavior predictable. They let users choose quality, source mode, and cleanup behavior without editing global config for every job.

## Related Docs

- [PDF Export](../guides/pdf-export.md)
- [Configuration Overview](../reference/configuration.md)
- [Configuration Reference](../CONFIG_REFERENCE.md)
