# First Manuscript Workflow

This guide covers the shortest complete workflow for a real manuscript.

## 1. Resolve The Source

Start in `Discovery` and submit one of:

- a IIIF manifest URL;
- a supported provider URL;
- a shelfmark or provider-specific identifier;
- a free-text query for providers with search adapters.

`Add item` stores local metadata. It does not force a full download.

## 2. Build The Local Workspace

Open the new item in `Library` and decide whether to:

- keep it as metadata-only for later;
- start the full download;
- retry missing pages if a prior run was partial.

This separation matters. Scriptoria treats discovery and asset acquisition as different operations.

## 3. Work In Studio

`Studio` is the main research surface:

- the viewer handles local and remote image sourcing;
- transcription and OCR flows stay attached to the document context;
- page-level actions let you refresh or optimize only the pages that need attention.

## 4. Export Only When Needed

Use `Output` for:

- PDF inventory review;
- profile-based export;
- page refresh actions;
- export job monitoring.

Profiles should be the default decision point. Per-job overrides should remain exceptional.

## Common Pitfalls

- If Studio opens without a document, you are on the recent-work hub.
- If remote images are shown, the item may still be incomplete locally.
- If pages remain staged, check the storage promotion policy.

## Related Docs

- [Discovery and Library](discovery-and-library.md)
- [Studio Workflow](studio-workflow.md)
- [PDF Export](pdf-export.md)
- [Troubleshooting](troubleshooting.md)
