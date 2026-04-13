# Studio Workflow

`Studio` is the main document workspace. It combines viewer behavior, document context, OCR flows, transcription editing, and output operations.

## Entry Behavior

If `/studio` is opened without `doc_id` and `library`, Scriptoria shows the recent-work hub. This is expected.

## Viewer Modes

Studio uses two reading modes:

- `Remote mode` for incomplete local datasets or explicit remote preview;
- `Local mode` for fully available local page sets.

Mode selection depends on:

- local page availability;
- `settings.viewer.mirador.require_complete_local_images`;
- the `allow_remote_preview=1` query override.

## OCR And Editing

- OCR jobs run asynchronously;
- progress is surfaced in the UI;
- transcription saves avoid unnecessary writes when content is unchanged;
- document history remains part of the working context.

## Output Inside Studio

The `Output` tab covers:

- PDF inventory;
- profile-based export;
- page-level image actions;
- export job monitoring.

## Related Docs

- [PDF Export](pdf-export.md)
- [Job Lifecycle](../explanation/job-lifecycle.md)
- [Export And PDF Model](../explanation/export-and-pdf-model.md)
