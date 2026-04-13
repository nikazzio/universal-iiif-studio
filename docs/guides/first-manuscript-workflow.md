# First Manuscript Workflow

This guide covers the shortest complete workflow for a real manuscript, while also explaining the decisions Scriptoria asks you to make along the way.

## 1. Resolve The Source

Start in `Discovery` and submit one of:

- a IIIF manifest URL;
- a supported provider URL;
- a shelfmark or provider-specific identifier;
- a free-text query for providers with search adapters.

`Add item` stores local metadata. It does not force a full download.

That distinction is intentional. Scriptoria lets you build a research shortlist before you commit network time and local storage to a full image acquisition.

## 2. Build The Local Workspace

Open the new item in `Library` and decide whether to:

- keep it as metadata-only for later;
- start the full download;
- retry missing pages if a prior run was partial.

This separation matters. Scriptoria treats discovery and asset acquisition as different operations.

At this stage, you should think in three states:

- `saved`: the item exists in local catalog state, but the reading assets may still be remote;
- `partial`: some local pages or files exist, but the local working copy is incomplete;
- `complete`: the local working copy is considered complete enough for fully local reading and export workflows.

## 3. Work In Studio

`Studio` is the main research surface:

- the viewer handles local and remote image sourcing;
- transcription and OCR flows stay attached to the document context;
- page-level actions let you refresh or optimize only the pages that need attention.

Opening an item in Studio does not simply “open a viewer”. Scriptoria also resolves:

- whether the manifest should come from the local cache or the remote endpoint;
- whether page images should come from local scans or remain remote;
- whether the current local asset state is complete enough for the configured reading policy.

This is why Studio may show a document in remote mode even when the item already exists in Library.

## 4. Export Only When Needed

Use `Output` for:

- PDF inventory review;
- profile-based export;
- page refresh actions;
- export job monitoring.

Profiles should be the default decision point. Per-job overrides should remain exceptional.

The product is deliberately conservative here. Export is treated as a tracked workflow because PDF generation may depend on:

- native upstream PDF availability;
- local scan availability and quality;
- temporary remote refetch for higher-resolution pages;
- page selection rules;
- output cleanup and retention policy.

## Common Pitfalls

- If Studio opens without a document, you are on the recent-work hub.
- If remote images are shown, the item may still be incomplete locally.
- If pages remain staged, check the storage promotion policy.
- If a provider search feels unreliable, switch from free text to a shelfmark, record URL, or direct manifest URL.

## Related Docs

- [Discovery and Library](discovery-and-library.md)
- [Studio Workflow](studio-workflow.md)
- [PDF Export](pdf-export.md)
- [Troubleshooting](troubleshooting.md)
