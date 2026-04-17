# Architecture Summary

Scriptoria is built as a Python application with a strict separation between the web UI shell, the reusable core services, and the CLI. The split is not stylistic. It is the load-bearing rule that makes the same product work as a FastHTML application, a CLI tool, and a research workbench against unstable upstream providers.

## Three Layers, One Direction Of Dependency

The repository is organized around three packages.

- `studio_ui/` renders the FastHTML and HTMX interface. It owns routes, components, and presentation glue.
- `universal_iiif_core/` owns provider resolution, storage, download orchestration, export logic, OCR services, networking, and runtime policy.
- `universal_iiif_cli/` exposes the CLI entry point on top of the same core services.

The dependency direction is one-way. The UI and CLI both depend on the core layer. The core layer does not import from `studio_ui/` or `universal_iiif_cli/`. That rule is what allows the web and CLI surfaces to share resolution, download, and export behavior without diverging implementations.

## Routes Orchestrate, Core Implements

Inside `studio_ui/`, the route modules in `studio_ui/routes/` exist to register HTTP endpoints and wire user actions to core services. They orchestrate. They do not contain business logic.

The same applies to handlers and helpers under `studio_ui/routes/_studio/` and the panes under `studio_ui/components/`. These exist to keep presentation focused and small. Anything that resolves manuscripts, validates pages, manages jobs, or persists state belongs in `universal_iiif_core/`.

This is the boundary that makes refactors safe. When a route module grows complex, the fix is usually to move logic into a core service, not to keep adding presentation-side conditionals.

## Why The Layering Is The Important Part

Without this separation, the application would still work, but it would behave differently in the CLI than in the web UI, and provider quirks would have to be patched in two places. With the separation, Scriptoria can:

- share resolution and download behavior between web and CLI;
- keep runtime policy in one place;
- make CLI scripts a first-class operational tool rather than a thin demo;
- reduce duplication in storage, networking, and export logic;
- evolve the UI surface without rewriting core behavior.

## Core Service Areas

The core layer is intentionally subdivided so that each service area is replaceable without touching the others.

### Discovery

Discovery uses a shared provider registry and a typed orchestration layer in `universal_iiif_core.discovery`. It classifies user input, runs direct resolution against the appropriate provider, and routes free-text queries to provider-specific search adapters. Results are normalized into a shared search contract before they reach the UI. This is what makes Discovery look like one feature even though every provider behaves differently.

### Downloading

Download orchestration is handled by the core services together with a job manager backed by local state. The runtime prefers native PDF when one is advertised and configured, falls back to IIIF image acquisition otherwise, validates pages in staging, and only promotes them into the local scan set when the configured policy allows it. Resume and retry safety across partial runs is part of the model, not a bolt-on.

### Storage

`VaultManager` and the storage services in `universal_iiif_core/services/storage/` keep track of manuscript records, download and export jobs, UI preferences, and snippet/OCR-related rows. The vault is local SQLite. Runtime files live under managed directories resolved through `ConfigManager`.

### Export

Export is a dedicated service rather than a side effect of the download path. It owns PDF inventory discovery, profile-driven export jobs, local and temporary remote high-resolution image sourcing, and cleanup and retention policies. The capability model is explicit so the UI can advertise roadmap surfaces without faking them.

### OCR

OCR services abstract local Kraken and remote OpenAI/Anthropic engines behind a common workflow, while the UI handles asynchronous job feedback. The core is engine-agnostic so that the UI does not have to know which backend produced a transcription.

### Networking

The centralized HTTP client (`universal_iiif_core.http_client`) is the only sanctioned transport layer for runtime network operations. It owns retry and backoff policy, per-library customization, concurrency and rate limiting, and request hygiene around hostile or fragile upstream services. New code must not create ad-hoc `requests` sessions; doing so bypasses the entire network policy layer.

## Runtime Configuration As An Architectural Concern

Configuration in Scriptoria is not cosmetic. `ConfigManager` is the single source of truth for runtime paths and policy. Hardcoded paths are forbidden because they break test isolation, packaging, and per-user installation. Hardcoded network behavior is also forbidden because providers behave too differently to be served by one fixed policy.

When a feature needs a path or a policy value, it asks `ConfigManager`. This keeps the rest of the codebase free of environmental assumptions.

## End-To-End Flow

The high-level flow across the three layers looks like this.

1. **Discovery to Library**: the user submits a URL, identifier, shelfmark, or query; Discovery resolves or searches through the provider registry; results are normalized; `Add item` writes local metadata without forcing a download.
2. **Download to local working state**: a download job is enqueued through the job manager; the runtime acquires native PDF or IIIF images; pages are validated in staging and promoted into local scans when policy allows.
3. **Library to Studio**: the user opens a local item; Studio builds a workspace context from local records and manifest state; the viewer chooses local or remote mode based on coverage and policy.
4. **Output and export**: the Output tab reads PDF inventory and page state; the user picks a profile or a page-level repair action; export jobs run through the storage-backed job system; artifacts are persisted under managed runtime paths.

Every step in that sequence touches multiple core services but stays inside the rules of the dependency layout: UI orchestrates, core implements, storage persists, networking transports.

## Design Rules That Hold This Together

- `docs/` is the documentation source of truth; wiki pages are derived publish targets.
- Runtime paths are resolved through `ConfigManager`, not hardcoded strings.
- `scans/` is the operational image source for local study workflows.
- Staging and retry behavior must remain safe for partial and resumed downloads.
- UI package structure should reflect responsibility boundaries, not just file size limits.
- The core layer never imports from UI or CLI packages.

## Deep Dive

For the more detailed component breakdown, including current UI package structure and contributor hotspots, see [Project Architecture](../ARCHITECTURE.md).

## Related Docs

- [Storage Model](storage-model.md)
- [Job Lifecycle](job-lifecycle.md)
- [Discovery And Provider Model](discovery-provider-model.md)
- [Export And PDF Model](export-and-pdf-model.md)
- [Security And Path Safety](security-and-path-safety.md)
