# Studio Workflow

`Studio` is the main manuscript workspace in Scriptoria. It is where the product stops being a discovery tool and starts acting like an operational environment for one concrete item.

In Studio, manifest resolution, local-versus-remote reading mode, viewer behavior, OCR and transcription work, page history, and export preparation are intentionally combined. That combination is deliberate. Once a manuscript has entered the local workspace, these concerns are no longer independent.

## Entry Behavior

If `/studio` is opened without `doc_id` and `library`, Scriptoria shows the recent-work hub. That is expected behavior, not an error state.

When Studio is opened for a real manuscript, the application does more than render a viewer. It resolves the current document context and decides which local and remote assets are viable for the session.

## What Studio Resolves On Load

At entry time, Scriptoria determines whether the manuscript row exists for the expected provider, whether a local manifest is available, whether remote fallback is needed, how many local scans and staged pages exist, what the manifest page count appears to be, whether the viewer should run in local or remote mode, and whether Mirador should stay gated until coverage is more complete.

This is why Studio behavior can differ for two manuscripts that both appear in Library. Library presence alone is not enough to define a Studio session.

## Local Manuscript Versus Online Manuscript

Studio effectively distinguishes between two operational states.

### Online Manuscript

The active reading session depends on the remote IIIF source. This usually happens when:

- the item is only saved and not downloaded;
- the local scan set is incomplete;
- policy prefers remote reading for saved items;
- the user explicitly allows remote preview.

### Local Manuscript

The active reading session uses the local workspace as the primary source. This happens when local scans are present in sufficient quantity and policy allows local-first reading.

The distinction is tracked through `read_source_mode`. It affects viewer behavior, manifest selection, and whether export workflows can stay fully local.

## Manifest Resolution In Studio

Studio can resolve the manifest from more than one place.

- If a local cached manifest exists and the current source mode allows it, Scriptoria can use the local manifest path.
- If the local manifest is missing or unsuitable for the current mode, it can fall back to the remote manifest URL stored with the manuscript record.

This matters because manifest source and image source are related but not identical decisions.

Examples:

- a manuscript can use a local manifest while some page behavior still depends on remote availability;
- a manuscript can temporarily use a remote manifest because the local cache is not ready yet;
- a manuscript can have local scans while the manifest source is still being normalized.

## Viewer Gating And Source Policy

The viewer is not always allowed to open in a fully local way.

Two settings are especially important here:

- `settings.viewer.mirador.require_complete_local_images`
- `settings.viewer.source_policy.saved_mode`

In practice, Studio can do one of three things:

- open in remote mode;
- open in local mode;
- gate the local viewer and expose an explicit "open Mirador anyway" path for remote preview.

That gating is useful because partial local coverage can create a false impression that the manuscript is fully local when it is not.

## Why Remote Mode Is Often Correct

Users often interpret remote mode as a failure, but that is usually the wrong reading.

Remote mode is often correct for:

- newly added items;
- partial downloads;
- manuscripts that are still being assembled locally;
- sessions where explicit remote preview is more useful than an incomplete local rendering.

Scriptoria keeps this state visible instead of pretending all saved items are already stable local workspaces.

## Page Context And Studio Tabs

Studio is page-aware. When the active page changes in the viewer, the right-hand workspace updates its tab content to stay aligned with that page.

In practice, page navigation changes transcription context, OCR state, page history, and export-side selection context where relevant. Studio is therefore not only a split layout with a viewer on the left and controls on the right. It is a synchronized document workspace.

## OCR, Transcription, And History

OCR and transcription work are anchored to the manuscript and page context.

Operationally, this means:

- OCR jobs are asynchronous;
- page-level OCR state can be surfaced without blocking the whole workspace;
- transcription saves avoid unnecessary writes when content has not changed;
- page history remains attached to the same manuscript identity in local storage.

This is one of the reasons Scriptoria is more than a viewer. It treats reading and working state as part of the same document lifecycle.

## Output Inside Studio

The `Output` tab is the export and page-quality workspace for the current manuscript. It is not a detached tools drawer.

The Output area is split into three subtabs:

- `Pages`
- `Build`
- `Jobs`

These exist because page inspection, export generation, and job monitoring are different tasks and should not be collapsed into one overloaded panel.

### Pages

The `Pages` subtab is the thumbnail-driven operational surface.

It is used for:

- visual inspection of locally available scans;
- page selection for export;
- page-by-page repair actions;
- checking local size and remote size metadata before export.

The grid is built from cached derivatives rather than from the full scans every time, which keeps the workspace responsive.

### Build

The `Build` subtab is where a new export is configured and launched.

It contains two secondary views:

- `Generate`, for the export form;
- `Files`, for the inventory of already generated local PDF files under the manuscript workspace.

This separation is useful because creating a PDF and reviewing what already exists are different operations.

### Jobs

The `Jobs` subtab is the manuscript-scoped monitor for export activity. It surfaces queued, running, completed, cancelled, and failed jobs relevant to the current item.

This is the operational view you use when export is long-running or when you need to check the result path after the build finishes.

## Scans, Thumbnails, Hover Previews

Studio Output does not treat all images as equivalent. `scans/` contains the canonical local page images. `thumbnails/` contains reduced JPEG derivatives for the page grid. The same derivative family can also include hover previews used for quick inspection.

These derivative assets are cached and can be pruned. The scans remain the primary local working images.

## What The Page Buttons Do

The page actions in Output are operationally distinct.

### `Scarica`

Reruns the normal progressive download strategy for that page. This includes the same fallback logic used for standard acquisition and can involve stitching when the direct path is insufficient.

### `Hi-res`

Requests the highest-resolution page image directly from the provider without going through the normal fallback sequence. Use this when one page needs a stronger source than the standard path produced.

### `Opt`

Optimizes the local scan already on disk. This is useful when the local page exists but should be reduced in size or normalized before later export work.

These controls exist because page quality problems are often local and uneven. Re-running an entire manuscript workflow for one weak page would be wasteful.

## Page Selection In Output

Page selection is part of the same workspace rather than a detached modal concept.

Scriptoria supports:

- full selection of all available pages;
- custom selection by card interaction;
- explicit range entry such as `1-10,12,20-25`.

Selection state is synchronized across the visible page grid, the hidden form fields, and the export build form. That is why selection survives UI swaps inside the Output workflow.

## Profiles, Overrides, And Build Parameters

The normal export workflow in Studio should be:

1. choose a PDF profile;
2. allow the profile to populate the main export parameters;
3. open the override panel only when the current job is exceptional.

The override panel can change:

- export format;
- compression;
- cover and colophon inclusion;
- source mode;
- max long edge;
- JPEG quality;
- forced remote re-fetch;
- cleanup of temporary high-resolution material;
- parallel remote page fetch count;
- cover metadata fields.

Profiles are repeatable policy. Overrides are local exceptions for one job.

## How Studio Connects To Storage

Studio is deeply tied to managed runtime paths. It does not assume arbitrary filesystem structure.

The workspace uses managed paths for:

- manuscript metadata;
- local manifest cache;
- scans;
- thumbnails and hover previews;
- PDF inventory;
- OCR-related material;
- page history and related context.

This is why path handling belongs to `ConfigManager` and storage services rather than to ad hoc file assumptions in the UI.

## Typical Reading Of Studio State

When a manuscript opens remotely, check local completeness before assuming a bug. If Mirador is gated, inspect viewer source policy and local page counts. If export feels constrained, look at the page grid and current profile before changing global settings. If local and remote behavior appear mixed, remember that manifest source and image source are resolved independently.

## Related Docs

- [PDF Export](pdf-export.md)
- [Configuration Overview](../reference/configuration.md)
- [Storage Model](../explanation/storage-model.md)
- [Job Lifecycle](../explanation/job-lifecycle.md)
- [Export And PDF Model](../explanation/export-and-pdf-model.md)
