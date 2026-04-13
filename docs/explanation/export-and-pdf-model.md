# Export And PDF Model

Export in Scriptoria is profile-driven, source-aware, and explicitly job-based.

## Why Export Is Its Own Subsystem

Scriptoria does not treat export as a trivial "save as PDF" action. The code separates it into a dedicated service because the final result depends on a chain of decisions that are not stable across providers or across manuscripts.

The export service has to resolve item scope, requested format, supported destination, valid pages for the selected source mode, effective profile or document override, source material origin, and whether the result is a PDF or a ZIP of selected images. That is why the UI exposes both a build form and a live jobs monitor.

## Capability Model

The service declares export capabilities explicitly. This is important because the product already reserves UI space for future export targets without pretending they are ready.

Currently enabled are `pdf_images`, `pdf_searchable`, `pdf_facing`, `zip_images`, and the `local_filesystem` destination. Currently declared but disabled are transcription-oriented text exports and destinations such as `google_drive`.

This capability model lets the UI remain honest: visible roadmap, but no fake affordances.

## Profiles As Policy

Profiles are not cosmetic presets. They are policy bundles applied before job execution.

The effective export configuration is resolved in this order:

1. explicit profile selected for the job;
2. document-specific override if present;
3. global default profile;
4. fallback to `balanced`.

The normalized profile payload controls:

- compression label;
- image source mode;
- maximum long edge for export images;
- JPEG quality;
- cover and colophon inclusion;
- forced remote re-fetch;
- temporary asset cleanup;
- maximum parallel page fetch count.

This means export behavior remains deterministic even when the UI surface changes later.

## Source Resolution Model

The export subsystem has three main image source modes:

- `local_balanced`;
- `local_highres`;
- `remote_highres_temp`.

The first two assume that local scans are the working source. The third is different: it allows the service to materialize higher-resolution pages into a temporary staging area for the current job, particularly when local scans are incomplete or not detailed enough.

This source distinction directly changes how page validation works, how many pages are considered available, and whether the job can proceed without a complete local scan set.

## Page Selection Semantics

The export service accepts:

- `all`;
- `custom`.

`custom` is parsed from a human-oriented range syntax such as `1,3-5,9`.

Selection is then validated against the active source:

- in local modes, requested pages must exist in `scans/`;
- in `remote_highres_temp`, the service can use manifest page count when local scans are absent or incomplete.

This is one of the key architectural differences between export and ordinary viewing. Viewing can degrade gracefully to remote access; export must either validate exactly or fail with a clear reason.

## Native PDF Versus Image-Based Output

Scriptoria recognizes two broad output families:

- provider-native PDF;
- image-based output assembled from page images.

The dedicated export service mainly governs the second family, because that is where page selection, quality control, and local-vs-remote materialization matter most.

Provider-native PDF still matters as a capability signal and as a pragmatic shortcut for some libraries, but image-based assembly is the more general path across heterogeneous IIIF sources.

## Job Lifecycle

Each export becomes a stored job row with:

- scope type;
- document ids;
- library identity;
- export format;
- output kind;
- page-selection mode;
- destination;
- progress counters;
- final output path;
- terminal error or cancellation status.

Worker execution happens asynchronously. The route layer creates the job entry first, then spawns the worker thread. That separation is what allows the UI to poll status, cancel active jobs, and still retain the result history after completion.

## Relationship Between Page Actions And Export

The thumbnail page actions are part of the same export-oriented quality model even though they are not export jobs themselves.

They exist because export quality is often constrained by page-level problems:

- one scan may be too compressed;
- one page may have been stitched poorly;
- one provider fetch may need a direct high-resolution retry;
- one manuscript may need local optimization before the final PDF build.

The Output surface therefore combines pre-export repair and final export generation in one workspace.

## Why Thumbnail Derivatives Matter

The export UI does not render the full scans in the selection grid. It uses cached derivatives and remote-resolution metadata so the page review surface stays responsive.

That subsystem keeps local thumbnails for the grid, hover previews for quick inspection, remote dimension cache entries, and retention rules for stale derivatives. Architecturally, this means export inspection is not just a viewer convenience. It is a storage-backed derivative layer with its own cache discipline.

## Relationship With Studio

Studio is the main user-facing surface, but export logic lives in shared services. Studio feeds the job request, while the core service resolves profile, pages, source mode, and artifact generation.

That split is important. Studio owns interaction and feedback. Export services own execution and validation. Storage services own persistence of jobs and artifacts.

## Related Docs

- [PDF Export](../guides/pdf-export.md)
- [Studio Workflow](../guides/studio-workflow.md)
- [Storage Model](storage-model.md)
- [Configuration Overview](../reference/configuration.md)
- [Configuration Reference](../CONFIG_REFERENCE.md)
