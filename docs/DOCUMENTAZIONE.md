# User Guide

Universal IIIF Downloader & Studio supports a single working flow:

1. Find or resolve an item in `Discovery`.
2. Save or download it into `Library`.
3. Open it in `Studio`.
4. Export PDFs or refresh single pages from `Output`.

This guide describes the current product behavior as implemented now.

## Core Navigation

- `Discovery` resolves direct inputs and provider-backed search.
- `Library` is the canonical entrypoint for local items.
- `Studio` is the document workspace.
- `Output` is the export surface inside Studio.
- `/studio` without `doc_id` and `library` opens the recent-work hub.

## Discovery

Discovery accepts:

- direct manifest URLs;
- provider item URLs;
- shelfmarks or IDs supported by a provider;
- free-text queries for providers with search adapters.

Current behavior:

- `Add item` performs a lightweight prefetch and saves local metadata.
- Full image download does not start until the user explicitly starts a download.
- Search results use canonical fields such as `manifest`, `library`, `id`, and optional `manifest_status`.
- Providers with real pagination expose `Load more` in the result list.

## Library

Library is the local asset catalog for saved and downloaded material.

Typical actions:

- open an item in Studio;
- review local or partial status;
- retry missing pages;
- clean partial data;
- remove an item and related runtime state.

Local runtime data is stored under the paths resolved by `ConfigManager`, not by hardcoded directory assumptions.

## Studio

Studio combines the document viewer and operational panels for transcription, history, visual inspection, metadata, images, and output.

### Recent-work Hub

If `/studio` is opened without a document context, the app shows a recent-work hub instead of an empty editor. This is expected behavior and is backed by persisted server-side context.

### Viewing Modes

Studio uses two viewing modes for Mirador:

- `Remote mode` for incomplete downloads or explicit remote-preview requests.
- `Local mode` for fully available local page sets.

Mode selection is driven by:

- local page availability;
- `settings.viewer.mirador.require_complete_local_images`;
- the `allow_remote_preview=1` query override.

Use remote mode when you need to inspect an item before the local download is complete. Use local mode when you need offline-safe study with only local assets.

### OCR And Editing

- OCR runs asynchronously.
- Studio tracks job state and exposes progress in the UI.
- Transcription saving avoids unnecessary writes when content has not changed.
- History remains available as document-level working context.

## Output

The `Output` tab is split into a few related responsibilities:

- PDF inventory for the current item;
- PDF generation with profile selection;
- thumbnail-level page actions;
- export job monitoring.

### PDF Profiles

Profiles define how exports are produced. Typical modes include:

- balanced local export;
- higher-detail local export;
- temporary remote high-resolution export.

Use profile selection for the default export decision. Use per-job overrides only for exceptions.

### Page-Level Actions

The page grid exposes single-page actions such as:

- direct high-detail refresh;
- standard refresh using the same strategy as full downloads;
- local scan optimization when enabled by configuration.

These actions are intended to avoid re-running a full-volume workflow when only a small subset of pages needs attention.

## Download And Storage Model

The downloader follows a practical fallback strategy:

1. Prefer a native PDF when the manifest exposes one and configuration allows it.
2. Extract local images for viewer compatibility when native PDF flow is used.
3. Fall back to IIIF image download when native PDF is unavailable or not selected.
4. Optionally build a PDF from images when configured to do so.

Current storage behavior:

- validated pages may remain staged in `temp_images/<doc_id>` before promotion;
- completed local working pages live in `downloads/<Library>/<DocumentId>/scans/`;
- PDF outputs live in the document `pdf/` folder;
- metadata and job artifacts live in the document `data/` folder.

Promotion timing is controlled by `settings.storage.partial_promotion_mode`.

## Configuration

Runtime settings live in `config.json`.

Use these documents together:

- [Configuration Reference](CONFIG_REFERENCE.md) for the full keyspace.
- [HTTP Client Notes](HTTP_CLIENT.md) for transport behavior.
- [Architecture](ARCHITECTURE.md) for system boundaries and component responsibilities.

Important settings families:

- `settings.network.*`
- `settings.images.*`
- `settings.pdf.*`
- `settings.storage.*`
- `settings.viewer.*`
- `settings.discovery.*`

## Troubleshooting

`iiif-studio: command not found`

```bash
source .venv/bin/activate
pip install -e .
```

Studio shows remote images instead of local images:

- This is expected when local page availability is incomplete and local-only gating is enabled.
- Use remote preview intentionally, or complete the local download.

Pages appear staged but not promoted:

- Review `settings.storage.partial_promotion_mode`.
- `never` keeps staged pages until completeness gates are satisfied.
- `on_pause` promotes validated staged pages when a running job is paused.

Gallica or other providers feel slow:

- This can be expected under stricter per-library rate limiting and backoff rules.
- Review `settings.network.global.*` and `settings.network.libraries.<library>.*`.

## Related Docs

- [Documentation Hub](index.md)
- [Studio Workflow Wiki Page](wiki/Studio-Workflow.md)
- [PDF Export Profiles Wiki Page](wiki/PDF-Export-Profiles.md)
- [FAQ](wiki/FAQ.md)
