# Storage Model

Scriptoria maintains local working state through managed runtime paths and storage services.

## Main Concepts

- manuscripts and metadata are tracked through local storage services;
- staged downloads can exist before final promotion;
- local scans are the operational source for local study workflows;
- export artifacts and job metadata are kept separately from raw scans.

## What A Local Manuscript Contains

A local manuscript workspace is more than one file. In normal operation, the managed document directory can contain:

- local metadata describing the manuscript record;
- a local cached manifest;
- `scans/` with page images used for local reading and export;
- `pdf/` with generated or retrieved PDF artifacts;
- `thumbnails/` and hover-preview derivatives used by Studio export tooling.

The exact path family is configuration-driven, but the conceptual structure is stable: one manuscript identity, one managed local workspace, multiple derived asset types.

## Why Staging Exists

Staging protects against partial and interrupted downloads. Validated output can be promoted only when the configured policy allows it.

This matters because manuscript downloads are large and failure-prone. A temporary page set may exist before the final `scans/` folder is considered trustworthy enough for normal local workflows.

## Scans Versus Thumbnails

Scriptoria distinguishes between the canonical local scans and their derivative previews.

- Scans are the primary local page images.
- Thumbnails are cached reduced-size images used in grid views and export inspection.
- Hover previews are larger-than-thumbnail derivatives intended for quick inspection without loading the full scan.

The derivative cache can be pruned. The scans remain the primary working assets.

## Local Versus Remote Reading State

Storage and reading mode are connected but not identical.

- An item may exist locally in Library while still reading remotely in Studio.
- An item may have some local scans but still be incomplete.
- A local manifest can exist before the scan set is complete.

That is why Scriptoria records flags such as local manifest availability, local scan availability, and current read-source mode instead of collapsing everything into a single boolean.

## Core Rule

Documentation and code should describe storage through managed path families and policies, not through hardcoded absolute assumptions.

## Related Docs

- [Runtime Paths](../reference/runtime-paths.md)
- [Job Lifecycle](job-lifecycle.md)
- [Security And Path Safety](security-and-path-safety.md)
