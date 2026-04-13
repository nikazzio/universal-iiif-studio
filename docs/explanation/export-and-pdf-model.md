# Export And PDF Model

Export in Scriptoria is profile-driven and storage-aware.

## Main Decisions

- prefer native PDF when available and configured;
- fall back to IIIF image download when native PDF is unavailable or disabled;
- optionally build a PDF from images;
- allow temporary remote high-resolution sourcing for export jobs that need it.

## Why Export Is A Separate System

Export is not treated as a passive file conversion step. It is a separate job system because output quality depends on multiple moving parts:

- whether the provider exposes a native PDF;
- whether the item already has complete local scans;
- whether local scans should be optimized before output;
- whether the export should temporarily re-fetch better remote images;
- whether the user wants all pages or a custom selection;
- whether cleanup should remove temporary high-resolution export assets afterward.

## Why Profiles Matter

Profiles keep export behavior predictable. They let users choose quality, source mode, and cleanup behavior without editing global config for every job.

## PDF Sources

Scriptoria recognizes two main PDF source models:

- `native PDF`: the upstream provider already exposes a PDF representation;
- `image-based PDF`: Scriptoria assembles a PDF from page images, either from local scans or temporary export-specific fetches.

The product can prefer native PDF where appropriate, but image-based export remains the most controllable and generally available path.

## Export Jobs And Scope

Every export run becomes a tracked job with:

- item scope;
- output format;
- page-selection mode;
- destination;
- current progress;
- final output path or error status.

This gives the UI a stable way to monitor long-running exports, cancellations, and retries.

## Relationship With Studio

Studio's Output tab is the primary user surface for export, but the export model is shared and can also be started from other UI contexts. The same core export services decide:

- which pages are included;
- which image source mode is active;
- whether a local artifact can be reused;
- whether an export capability is currently available.

## Related Docs

- [PDF Export](../guides/pdf-export.md)
- [Studio Workflow](../guides/studio-workflow.md)
- [Storage Model](storage-model.md)
- [Configuration Overview](../reference/configuration.md)
- [Configuration Reference](../CONFIG_REFERENCE.md)
