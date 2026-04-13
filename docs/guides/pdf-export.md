# PDF Export

Scriptoria treats export as a controlled, profile-driven workflow. The product assumes that output quality depends on source quality, page selection, provider behavior, and local workspace state. For that reason, export is not presented as a single-button afterthought.

## Where Export Lives

The main export workflow lives inside `Studio`, under the `Output` tab. That area is split into `Pages` for inspection and selection, `Build` for form-based export generation and local PDF inventory, and `Jobs` for monitoring active and past export runs.

There is also a standalone `Export` page that exposes overall capability status and the general jobs monitor, but item-level export generation still happens from the Studio workflow.

## Supported Export Formats

The current export service exposes four active formats: `PDF (solo immagini)`, `PDF ricercabile`, `PDF testo a fronte`, and `ZIP immagini`.

The code also declares future export targets such as transcription-oriented formats and external destinations, but they are intentionally marked as unavailable in the current product.

## The Normal Export Sequence

For one manuscript, the intended sequence is:

1. open the item in `Studio`;
2. inspect the current page set in `Output > Pages`;
3. select all pages or a curated subset;
4. move to `Output > Build`;
5. choose a PDF profile;
6. keep profile defaults or open the override panel for a one-off job;
7. start the export;
8. monitor progress in `Jobs`;
9. download the result from the job entry or the local PDF inventory.

This order matters. Page inspection often needs to happen before the final PDF decision.

## Profiles

Profiles are the main control surface for export behavior.

The built-in catalog currently includes:

- `balanced`
- `high_quality`
- `archival_highres`
- `lightweight`

Each profile can define:

- compression mode;
- image source mode;
- maximum long edge;
- JPEG quality;
- cover inclusion;
- colophon inclusion;
- forced remote re-fetch;
- cleanup of temporary high-resolution export assets;
- maximum parallel page fetch count.

Profiles should be the default choice. Use per-job overrides only when the current export needs to depart from the normal policy.

## Source Modes

The build form exposes three source modes:

- `local_balanced`
- `local_highres`
- `remote_highres_temp`

These are not superficial labels.

### `local_balanced`

Uses the current local scan set with a balanced profile intended for routine output.

### `local_highres`

Uses the local scan set but keeps a larger image target and higher JPEG quality for export.

### `remote_highres_temp`

Temporarily stages higher-resolution remote material for the current job when the local scans are not sufficient for the target output.

This third mode is particularly important when the local manuscript exists but the current scan quality is not enough for a final preservation-oriented or publication-oriented PDF.

## Page Selection

Page selection supports:

- `all`
- `custom`

Custom selection accepts explicit values and ranges such as `1,3-5,9`.

Validation depends on the active source mode:

- in local modes, requested pages must exist in the local scan set;
- in remote temporary mode, Scriptoria can validate against the manifest page count even when the local scan set is incomplete.

This is one of the key reasons export is implemented as a service with explicit validation rather than a thin UI action.

## What The Page Grid Tells You

The thumbnail grid is the practical inspection surface for export readiness. For each visible page, Scriptoria can show local dimensions, declared remote IIIF dimensions, directly verified remote dimensions, local file size, and progress feedback for repair actions.

This lets you make a more informed export decision before starting a long-running job.

## Page-Level Repair Actions

The page grid exposes three action types.

### `Scarica`

Runs the normal progressive acquisition strategy for that page, including fallback logic and stitching where necessary.

### `Hi-res`

Requests a direct maximum-resolution page fetch from the provider without using the normal fallback sequence.

### `Opt`

Runs local optimization on the scan already stored on disk.

These actions are essential because real-world export failures are often local to a few pages rather than global to the whole manuscript.

## Thumbnails, Hover Previews, And Scans

The export grid is based on cached derivatives, not on the full scans themselves. `scans/` stores the canonical local page images. `thumbnails/` stores reduced JPEG derivatives used for the grid. Larger hover previews can exist in the same derivative family for quick inspection.

These derivatives are generated on demand and reused until source scans change or retention policy prunes them.

## Native PDF Versus Image-Based Export

Scriptoria distinguishes between two broad output models:

- provider-native PDF
- image-based output assembled from page images

Native PDF can be the most direct path when the provider exposes one and policy allows it. Image-based export remains the more controllable route when you care about page subsets, page repair, explicit quality settings, or local reproducibility.

ZIP image export belongs to the second family in operational terms. It is useful when the downstream consumer needs selected page images rather than a bound PDF.

## Cover And Metadata Controls

The build form can include a generated cover page, a colophon page, curator text, descriptive text, and an optional logo path.

These values come from profile-aware settings and export defaults, but they can be overridden for the current job when needed.

## Jobs And Result Storage

Every export becomes a tracked job with item scope, export format, selection mode, destination, progress counters, and either an output path or a terminal error state.

Finished PDF files are stored inside the manuscript workspace under the item PDF area. The `Files` subview inside `Build` is effectively a local inventory of those generated artifacts.

## When To Use Which Strategy

- Use `balanced` for routine working PDFs.
- Use `high_quality` when the local scans are already good and you want stronger output.
- Use `archival_highres` when local material is insufficient and provider-side high-resolution fetch is still available.
- Use `lightweight` when portability matters more than fidelity.
- Use page-level repair before export when only a few pages are problematic.
- Use `ZIP immagini` when you need the selected image set itself rather than a PDF.

## Related Docs

- [Studio Workflow](studio-workflow.md)
- [Configuration Overview](../reference/configuration.md)
- [Storage Model](../explanation/storage-model.md)
- [Export And PDF Model](../explanation/export-and-pdf-model.md)
