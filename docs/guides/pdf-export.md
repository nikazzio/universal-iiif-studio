# PDF Export

Scriptoria treats PDF export as a profile-driven workflow, not a one-off button.

## Main Model

The `Output` tab supports:

- current PDF inventory review;
- PDF creation with profile selection;
- thumbnail-level page actions;
- export job monitoring.

The export system exists because manuscript output is not uniform across providers. Some items expose a native upstream PDF, some only expose IIIF image resources, and some need temporary remote re-fetching to produce a higher-quality result than the current local scans can provide.

## Profiles

Typical export modes:

- balanced local export;
- higher-detail local export;
- temporary remote high-resolution export.

Prefer profile choice for the default decision. Use overrides only when the current job is exceptional.

Profiles are meant to capture repeatable decisions such as:

- image source mode;
- image resizing policy;
- JPEG quality;
- temporary remote re-fetch behavior;
- cleanup expectations after export.

That keeps PDF behavior predictable across runs and across users.

## Page Actions

The page grid exposes targeted recovery or quality actions:

- direct high-detail refresh;
- standard refresh using the same strategy as full downloads;
- local scan optimization when enabled.

These actions exist to avoid rerunning a full-volume pipeline when only a few pages need attention.

### What The Output Tab Is Really Showing

The Output tab combines three distinct concepts:

- existing local PDF artifacts for the current item;
- the current set of local scans and their thumbnail-derived inspection view;
- tracked export jobs, including queued, running, completed, error, and cancelled states.

### Native PDF Versus Image-Based PDF

Scriptoria can prefer a native PDF when the provider exposes one and configuration allows it. When no suitable native PDF exists, Scriptoria falls back to image-based export from scans or temporary remote image fetches.

In practice:

- native PDF is usually the most direct path when available and acceptable;
- image-based PDF is the portable fallback and often the only route for strict page-level control;
- page-selection and image-quality controls are most useful in image-based workflows.

### Local Scans, Optimized Scans, And Temporary High-Resolution Fetches

The export system distinguishes between:

- the current local scans already stored for the item;
- optimized local derivatives used to reduce weight or standardize output;
- temporary remote fetches used only to improve export quality for the current job.

Temporary export assets can be cleaned automatically after the job, while the main local scans remain part of the manuscript workspace.

## Related Docs

- [Studio Workflow](studio-workflow.md)
- [Provider Support](../reference/provider-support.md)
- [Configuration Overview](../reference/configuration.md)
- [Export And PDF Model](../explanation/export-and-pdf-model.md)
