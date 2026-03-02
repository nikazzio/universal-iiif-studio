# Inactive Features Backlog

This document tracks options/features removed from the UI or marked as inactive during issue #46 refactoring.
Goal: avoid misleading configuration controls in the current product while keeping a clear, implementable evolution backlog.

## Scope

- Runtime status: based on the current implementation under `src/`.
- UI status: based on the current Settings/Studio panels.
- Intended use: technical backlog for future work, not end-user guidance.

## Inactive or Removed UI Features

- `settings.system.download_workers`
  - Current status: removed from UI, not active in the current runtime.
  - Reason: document download concurrency is handled by the job queue manager (`max_concurrent_downloads`).
  - Proposed evolution: dedicated intra-document download pool with dynamic per-host limits.

- `settings.system.request_timeout`
  - Current status: removed from UI, not used as a single global key.
  - Reason: HTTP timeouts are managed in specific pipeline points.
  - Proposed evolution: centralized HTTP client with uniform timeout policy and provider-specific overrides.

- `settings.system.ocr_concurrency`
  - Current status: removed from UI, not wired to the current OCR scheduler.
  - Reason: OCR concurrency is not exposed as a single runtime control.
  - Proposed evolution: dedicated OCR queue with `max_workers`, priority, and explicit retry policy.

- `settings.pdf.ocr_dpi`
  - Current status: not exposed in UI; not used as a primary active control.
  - Reason: current pipeline uses `settings.pdf.viewer_dpi` for native-PDF image extraction.
  - Proposed evolution: formal separation between `viewer_dpi` (viewer extraction) and `ocr_dpi` (OCR preprocessing).

- `settings.images.ocr_quality`
  - Current status: removed from UI, not used by the active OCR pipeline.
  - Reason: no structured OCR quality profile is currently active.
  - Proposed evolution: dedicated OCR profiles (denoise, sharpen, binarization, target quality).

- `settings.thumbnails.columns`
  - Current status: removed from UI.
  - Reason: thumbnail layout is controlled by responsive CSS grid, not by static column count.
  - Proposed evolution: thumbnail layout presets (`compact`, `comfortable`, `research`).

- `settings.thumbnails.paginate_enabled`
  - Current status: removed from UI.
  - Reason: pagination is always active in Studio Export.
  - Proposed evolution: toggle between pagination and infinite scroll.

- `settings.thumbnails.default_select_all`
  - Current status: removed from UI.
  - Reason: initial selection behavior is managed directly in the Studio Export panel flow.
  - Proposed evolution: reusable initial-selection templates for repetitive workflows.

- `settings.thumbnails.actions_apply_to_all_default`
  - Current status: removed from UI.
  - Reason: no automatic bulk-action flow is currently bound to this key.
  - Proposed evolution: persistent bulk-action mode with explicit confirmation.

- `settings.thumbnails.hover_preview_*` and `inline_base64_max_tiles`
  - Current status: removed from UI.
  - Reason: hover-preview pipeline is not active in the current UX.
  - Proposed evolution: progressive hover previews with dedicated cache and memory budget control.

## Features Introduced in Replacement

- Advanced PDF profiles with default + custom presets
  - Keys: `settings.pdf.profiles.catalog`, `settings.pdf.profiles.default`.
  - UX: centralized profile catalog in `Settings > PDF Export`.

- Per-page resolution transparency in Studio Export
  - UI: `Locale` vs `Online max` comparison in thumbnail cards.
  - Goal: enable informed decisions on local balanced workflow vs targeted high-resolution fetches.

- On-demand high-resolution fetch for export
  - UI: per-page `High-Res` action.
  - Runtime: `remote_highres_temp` temporary staging with optional post-export cleanup.

## Recommended Evolution Backlog

- Introduce configuration schema versioning (`settings.schema_version`) with guided migrations.
- Add storage diagnostics endpoints (`/api/storage/report`, `/api/storage/prune`).
- Evaluate distributed `info.json` cache for lower latency on very large manuscripts.
