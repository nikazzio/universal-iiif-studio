# Studio Workflow

`Studio` is the main document workspace. It combines viewer behavior, document context, OCR flows, transcription editing, and output operations.

## Entry Behavior

If `/studio` is opened without `doc_id` and `library`, Scriptoria shows the recent-work hub. This is expected.

When Studio is opened for a real item, it resolves both the document context and the best currently available asset source. That means Studio is not just a static page renderer; it makes runtime decisions based on manifest availability, local scans, and viewer policy.

## Viewer Modes

Studio uses two reading modes:

- `Remote mode` for incomplete local datasets or explicit remote preview;
- `Local mode` for fully available local page sets.

Mode selection depends on:

- local page availability;
- `settings.viewer.mirador.require_complete_local_images`;
- the `allow_remote_preview=1` query override.

### Local Manuscript Versus Online Manuscript

In practical terms, an item can behave in one of two ways:

- `Online manuscript`: Scriptoria is reading from the remote IIIF source because the local asset set is missing, incomplete, or intentionally bypassed.
- `Local manuscript`: Scriptoria is reading from the local working copy because local scans exist and current policy allows local-first reading.

This distinction is tracked as `read_source_mode`. It is not just cosmetic. It affects which manifest URL is used, which images the viewer loads, and whether local export workflows can stay fully offline.

### How Manifest Resolution Works In Studio

Studio tries to use a local cached manifest when it exists. If the local manifest is missing, it can load the remote manifest instead. The selected manifest source and the selected image source are related, but they are not identical decisions.

That means:

- a document may use a local manifest but still fall back to remote images in some conditions;
- a document may use a remote manifest when the local one is not available yet;
- local scans can exist even while the manifest path is still being refreshed or normalized.

### Why Remote Mode Is Not An Error

Remote mode is often the correct behavior for:

- newly saved items that have not been downloaded yet;
- incomplete downloads;
- cases where the current policy prefers remote reading for saved items;
- explicit temporary remote preview.

## OCR And Editing

- OCR jobs run asynchronously;
- progress is surfaced in the UI;
- transcription saves avoid unnecessary writes when content is unchanged;
- document history remains part of the working context.

Studio is therefore both a reader and a working environment. Reading, transcription, OCR, and export preparation all stay attached to the same manuscript identity in local storage.

## Output Inside Studio

The `Output` tab covers:

- PDF inventory;
- profile-based export;
- page-level image actions;
- export job monitoring.

### Images, Scans, And Thumbnails

Scriptoria stores full local page images as scans. These are the operational image assets used for local reading, optimization, and image-based export.

The Export tab also generates smaller derivatives:

- thumbnails for the export grid;
- larger hover previews derived from the local scans;
- optional optimized scans used to reduce size or normalize export behavior.

These derivatives are cached and pruned according to retention settings. They are not the canonical manuscript images. The scans remain the primary local page source.

### Why The Thumbnail Grid Matters

The thumbnail grid is not just visual navigation. It is an operational control surface for:

- page-level refresh;
- high-detail re-fetch for a specific page;
- targeted optimization;
- spotting missing or problematic pages before export.

## Related Docs

- [PDF Export](pdf-export.md)
- [Provider Support](../reference/provider-support.md)
- [Storage Model](../explanation/storage-model.md)
- [Job Lifecycle](../explanation/job-lifecycle.md)
- [Export And PDF Model](../explanation/export-and-pdf-model.md)
