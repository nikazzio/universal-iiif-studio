# PDF Export

Scriptoria treats PDF export as a profile-driven workflow, not a one-off button.

## Main Model

The `Output` tab supports:

- current PDF inventory review;
- PDF creation with profile selection;
- thumbnail-level page actions;
- export job monitoring.

## Profiles

Typical export modes:

- balanced local export;
- higher-detail local export;
- temporary remote high-resolution export.

Prefer profile choice for the default decision. Use overrides only when the current job is exceptional.

## Page Actions

The page grid exposes targeted recovery or quality actions:

- direct high-detail refresh;
- standard refresh using the same strategy as full downloads;
- local scan optimization when enabled.

These actions exist to avoid rerunning a full-volume pipeline when only a few pages need attention.

## Related Docs

- [Studio Workflow](studio-workflow.md)
- [Configuration Overview](../reference/configuration.md)
- [Export And PDF Model](../explanation/export-and-pdf-model.md)
