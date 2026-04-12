# Project Architecture

## Overview

Scriptoria separates a Python UI shell from reusable core services:

- `studio_ui/` renders the FastHTML and HTMX interface.
- `universal_iiif_core/` owns provider resolution, storage, download orchestration, export logic, OCR services, and runtime policy.
- `universal_iiif_cli/` exposes the CLI entrypoint on top of the same core services.

The UI depends on the core layer. The core layer does not depend on UI modules.

## Current UI Structure

The Studio-facing UI is now organized as focused packages rather than large single-file modules.

### Routes And Workspace Helpers

- `studio_ui/routes/studio.py` registers the Studio routes.
- `studio_ui/routes/studio_handlers.py` acts as the public handler surface and orchestration entrypoint.
- `studio_ui/routes/_studio/` contains focused helpers for:
  - workspace context;
  - manifest and read-source selection;
  - thumbnail/export fragments;
  - page-level job preferences;
  - UI utility glue.

This keeps the route surface stable while moving implementation detail into narrower modules.

### Settings UI

- `studio_ui/components/settings/panes/` contains domain-specific settings panes.
- The package is organized by responsibility such as general, images, network, PDF, system, viewer, and discovery settings.

### Studio Output UI

- `studio_ui/components/studio/export/` owns the Output tab assembly.
- The package is split into:
  - PDF inventory rendering;
  - page actions;
  - thumbnail rendering;
  - output tab assembly;
  - client-side tab script generation.

## Core Services

### Discovery

Discovery uses a shared provider registry and typed orchestration in `universal_iiif_core.discovery`.

Responsibilities:

- classify user input;
- resolve direct provider inputs;
- route free-text search to provider search adapters;
- normalize results into the shared search contract;
- support provider-specific filters and pagination where available.

### Downloading

Download orchestration is handled by core services and a job manager backed by local state.

Runtime behavior includes:

- native PDF-first strategy when configured;
- IIIF image fallback;
- staged page validation before promotion;
- resume and retry safety across partial runs.

### Storage

`VaultManager` and related storage modules keep track of:

- manuscripts and metadata;
- download and export jobs;
- UI preferences and local working state;
- snippet and OCR-related local records.

### Export

Export services manage:

- PDF inventory discovery;
- profile-driven export jobs;
- local and temporary remote high-resolution image sourcing;
- cleanup and retention policies.

### OCR

OCR services abstract local and remote engines behind a common workflow, while the UI handles asynchronous job feedback.

### Networking

The centralized HTTP client is the primary transport layer for runtime network operations.

Responsibilities:

- retry and backoff policy;
- per-library network customization;
- concurrency and rate limiting;
- metrics and request hygiene around hostile or fragile upstream services.

## End-To-End Flow

### 1. Discovery To Library

1. The user submits a URL, identifier, shelfmark, or query.
2. Discovery resolves or searches through the provider registry.
3. Results are normalized into the shared search contract.
4. `Add item` writes local metadata without forcing a full download.

### 2. Download To Local Working State

1. A download job starts through the job manager.
2. The runtime prefers native PDF when available and configured.
3. Otherwise it downloads IIIF images and validates them in staging.
4. Validated output is promoted into local scans when the promotion policy allows it.

### 3. Library To Studio

1. The user opens a local item from Library.
2. Studio builds a workspace context from local records and manifest state.
3. The viewer chooses remote or local mode based on completeness and policy.
4. The user works across transcription, history, metadata, image actions, and output.

### 4. Output And Export

1. The Output tab reads current PDF inventory.
2. The user selects an export profile or uses a page-level refresh action.
3. Export jobs run through the storage-backed job system.
4. Output artifacts are persisted under runtime-managed paths.

## Design Rules

1. `docs/` is the documentation source of truth; wiki pages are derived publish targets.
2. Runtime paths are resolved through `ConfigManager`, not hardcoded strings.
3. `scans/` is the operational image source for local study workflows.
4. Staging and retry behavior must remain safe for partial and resumed downloads.
5. UI package structure should reflect responsibility boundaries, not just file size limits.

## Current Hotspots For Contributors

- Discovery orchestration and provider search behavior.
- Studio workspace and read-source selection.
- Output tab assembly and thumbnail/page-action rendering.
- Settings panes for network, PDF, viewer, and system behavior.
- Config reference and runtime validation alignment.
