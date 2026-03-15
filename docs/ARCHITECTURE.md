# 🏗️ Project Architecture

## Overview

Universal IIIF Downloader & Studio separates a **FastHTML/htmx-based UI shell** (`studio_ui/`) from the pure Python core (`universal_iiif_core/`). The UI renders HTML elements, wires HTMX for asynchronous swaps, and embeds Mirador, while the back-end keeps all metadata, storage, OCR logic, and network resolution untouchable.

## System Layers

The application is strictly divided into two main layers. The **UI Layer** depends on the **Core Layer**, never the other way around.

### 1. Presentation Layer (`studio_ui/`)

* **Pages**: Layout builders (`studio_layout`, Mirador wiring).
* **Components**: Reusable UI parts (tab sets, toast holder, SimpleMDE-powered editor, Mirador viewer, snippet cards, professional status panel).
* **Routes**:
  * `studio_handlers.py`: Logic-heavy handlers for the editor, viewer, and OCR operations. Implements Mirador local/remote mode selection.
  * `discovery_handlers.py`: Route entrypoints for search/add/download flows, delegating persistence helpers to `discovery_persistence.py`.
  * `library_handlers.py`: Local Assets listing, cleanup, retry, and deletion actions.
  * `library_query.py`: Shared filtering/query/view-model helpers for Library routes.
* **Common**: Shared utilities (`build_toast`, htmx triggers, Mirador window presets).
* **Status Panel**: Color-coded badges for technical status (read_source: AMBER for remote, GREEN for local; state, scans, staging, PDF info).

### 2. Core Business Logic (`universal_iiif_core/`)

* **Discovery Module**:
  * **Provider Registry**: A shared provider catalog drives web Discovery, settings options, and CLI direct resolution from the same metadata source.
  * **Orchestrator package**: `universal_iiif_core.discovery` now owns typed contracts and orchestration policy (`contracts.py`, `orchestrator.py`) plus search strategy adapter mapping (`search_adapters.py`).
  * **Resolvers**: Direct resolution still ends in provider-specific resolver classes, but registration happens through the provider registry rather than UI/CLI hardcoding.
  * **Search Modes**: Each provider declares `search_mode` (`direct`, `fallback`, `search_first`) plus an optional `search_strategy`. This keeps the UX consistent while allowing provider-specific search adapters.
  * **Search Coverage**: Current searchable providers are `Gallica`, `Vaticana`, `Institut de France`, `Internet Archive`, `Bodleian`, `e-codices`, `Cambridge`, `Heidelberg`, `Harvard`, and `Library of Congress`, but some adapters are intentionally hybrid. For example Cambridge and Heidelberg free-text can degrade to browser handoff results when the public site blocks scripted search or does not expose stable machine-readable hits.
  * **Result Contract**: Provider adapters return canonical `SearchResult` payloads. `viewer_url` is the normalized field for source viewer links; `raw` remains available only for provider-specific extras.
* **Downloader Logic**:
  * Implements the **Golden Flow** (Native PDF check -> Extraction -> Fallback to IIIF).
  * Manages threading and DB updates.
  * Uses staged local pages in `temp_images/<doc_id>` before promoting validated files into `scans/`.
  * Split across `logic/downloader.py` (orchestrator), `logic/downloader_pdf.py` (PDF/native pipeline), and `logic/downloader_runtime.py` (canvas/runtime pipeline).
* **Network Layer (`utils.py`)**:
  * Provides a resilient `requests.Session`.
  * Handles WAF Bypass (Browser User-Agents, Dynamic Brotli).
* **HTTP Client (`http_client.py`)**:
  * Centralized HTTP client with automatic retry, exponential backoff, and per-host rate limiting.
  * Per-library network policies (timeout, concurrency, backoff, rate limits).
  * Metrics tracking for requests, retries, and timeouts.
  * Sliding window rate limiter prevents overwhelming library servers (Gallica: 4 req/min, others: 20 req/min).
  * Used by: downloader, IIIF tiles, resolution probing, manifest fetching, external catalog scraping.
* **OCR Module**:
  * Abstracts differences between local Kraken models and Cloud APIs (OpenAI/Anthropic).
* **Storage**:
  * `VaultManager`: SQLite interface for metadata and job tracking (`queued/running/partial/complete` states).
  * `vault_snippets.py` and `vault_jobs.py` hold extracted repository-style methods attached to `VaultManager`.

---

## Interactive Flows

### 1. Discovery, Library Add, and Resolution

1. **User Input**: The user enters free text, shelfmark (e.g., "Urb.lat.1779"), an ID, or a URL.
2. **Provider Lookup**: Discovery resolves the selected library through the shared provider registry.
3. **Provider Resolution**: The provider decides whether to try direct resolution first, search first, or direct resolution with search fallback.
4. **Normalization**: Provider resolvers convert "dirty" inputs into canonical IIIF Manifest URLs only when `can_resolve()` positively identifies the input as direct.
5. **Search Adapter Stage**: Optional provider-specific filters are applied before invoking the provider search adapter (for example the Gallica type filter).
6. **Preview / Result List**: Search adapters return canonical `SearchResult` entries; direct resolution fetches manifest details for preview and lazy-checks native PDF availability. Results without a `manifest` are rendered as consult-only cards that open the upstream catalog but cannot be added/downloaded.
7. **Action Split**: From each result, the user can either add to local Library (`saved`) or add + enqueue download.

### 2. Download Manager + Golden Flow

Downloads are queued in a DB-backed manager with bounded concurrency (`settings.network.global.max_concurrent_download_jobs`).
Queued jobs are promoted FIFO (with optional prioritization) and each running worker follows this flow:

1. **Check Native PDF**: Does the manifest provide a download link?
    * **YES + `settings.pdf.prefer_native_pdf=true`**: Download the PDF. Then, **EXTRACT** pages to high-quality JPGs in `scans/` (Critical for Studio compatibility).
    * **NO**: Fallback to downloading IIIF tiles/canvases one by one into staging (`temp_images/<doc_id>`), then promote validated pages into `scans/`.
2. **Optional Compiled PDF**: If (and only if) no native PDF was used **AND** `settings.pdf.create_pdf_from_images=true`, generate a PDF from the downloaded images.
3. **Completion**: Update DB status and manuscript `asset_state` (`complete` or `partial`).
4. **Segmented Resume Safety**: Retry/range runs count already-staged validated pages together with current-run pages before promotion, so partial batches converge without deadlock.

### 3. Studio & OCR

0. **Entry Point**: Library is the canonical selector; `/studio` without `doc_id/library` renders the Studio recent hub (`Riprendi lavoro`) using server-side persisted contexts.
1. **Async Request**: Clicking "Run OCR" sends an HTMX POST to `/api/run_ocr_async`.
2. **Job State**: The server spawns a thread and tracks progress in `ocr_state.py`.
3. **Polling**: The UI shows an overlay that polls `/api/check_ocr_status` every 2 seconds.
4. **Completion**: Text is saved to `transcription.json` and the History table.

### 4. Mirador Viewing Modes

Studio supports **two distinct viewing modes** for the Mirador viewer, automatically selected based on download completeness:

* **REMOTE MODE** (for incomplete/paused downloads):
  - Mirador loads the **original manifest** from the library server (e.g., `gallica.bnf.fr`).
  - Displays **ALL pages** by fetching images on-demand from the remote server.
  - Useful for previewing documents before full download completes.
  - Requires internet connection.
  - User can force this mode with `?allow_remote_preview=true` URL parameter.

* **LOCAL MODE** (for completed downloads):
  - Mirador loads the **local manifest** (`/iiif/manifest/...`) served by Studio.
  - Displays **only downloaded pages** using local images from `scans/`.
  - Works completely offline.
  - Default mode when `viewer.mirador.require_complete_local_images=true` (default) and all pages are available locally.

**Mode Selection Logic** (`studio_handlers.py`):
- `_resolve_studio_read_source_mode()`: Determines if local images are sufficient or remote preview is needed.
- `_select_studio_manifest_url()`: Returns appropriate manifest URL (local or remote) based on mode.
- Config setting: `viewer.mirador.require_complete_local_images` (default: `true`) gates local viewer until download completes.
- User override: `?allow_remote_preview=true` URL parameter forces remote mode regardless of settings.

---

## UI & Configuration Details

* **Viewer Config**: The `config.json` (`settings.viewer`) section directly controls Mirador's behavior (Zoom levels, viewing modes) and the Visual Tab's default image filters.
* **Mirador Modes**: Automatic switching between remote preview (incomplete downloads) and local-only (complete downloads) based on `viewer.mirador.require_complete_local_images` setting.
* **State Persistence**:
  * **Server-side**: SQLite (`vault.db`) and JSON files (`data/local/`).
  * **Client-side**: Sidebar state (collapsed/expanded) is saved in `localStorage`.
* **Visual Feedback**:
  * **Toasts**: Floating notifications anchored to the top-right viewport.
  * **Progress**: Real-time queue/running status driven by DB polling in the Download Manager side panel.
  * **Studio page jobs**: per-page `Hi/Std` actions are stored as `studio_export_page` jobs and rendered in Discovery as a compact auxiliary section, not as full document download cards.
  * **Status Panel**: Professional color-coded badges for technical status (read_source, state, scans, staging, PDF info).

## Key Design Decisions

1. **Scans as Operational Source + Temp Staging**: `scans/` is the operational source for Viewer/OCR/Cropper, but runtime can stage validated pages in `temp_images/<doc_id>` before promotion. Promotion policy can stay strict (`never`) or happen on pause (`settings.storage.partial_promotion_mode=on_pause`), with overwrite of existing scans enabled only for explicit refresh/redownload flows.
2. **Zero Legacy**: Deprecated APIs are removed or stubbed. No "dead code" is allowed in the codebase.
3. **Network Resilience**: The system assumes library servers are hostile (rate limits, firewalls) and uses aggressive retry logic, header mimicking, and centralized HTTP client with per-host rate limiting.
4. **Pure HTTP Front-end**: No heavy client-side frameworks (React/Vue). The UI logic is driven by Python via FastHTML and HTMX.
5. **Studio PR3 route scope (decision log, 2026-03-05)**: do not add dedicated `/studio/partial/viewer` and `/studio/partial/availability` routes for now. Keep viewer gating and availability in the main `/studio` flow to avoid route surface growth and duplicated state logic. Re-evaluate only if measured UI payload/latency or independent refresh requirements justify a split.
6. **Centralized HTTP Client (Issue #71, 2026-03-09)**: Eliminated ~200+ lines of duplicate retry/backoff logic by introducing `HTTPClient` class with automatic retry, exponential backoff, per-host rate limiting, and metrics. Most IIIF core modules use this client; some discovery provider surfaces still use legacy request paths and are tracked for migration.
7. **Current Discovery Refactor Boundary (2026-03-14)**: discovery orchestration and search adapter dispatch are now extracted in `universal_iiif_core.discovery`, and UI rendering is split into dedicated modules (`discovery_form`, `discovery_results`, `discovery_download_panel`, `discovery_page`) with a compatibility aggregator. Remaining technical debt is mostly inside provider-specific parser/search code still hosted in `universal_iiif_core.resolvers.discovery`.

## Local Data & Cleanup

- Runtime directories (`downloads/`, `data/local/*`, `logs/`, `temp_images/`) are resolved via `universal_iiif_core.config_manager` and treated as regenerable data. Do not store config assets or secrets in these directories.
- `scripts/clean_user_data.py` uses the manager to resolve paths and supports `--dry-run`, `--yes`, `--include-data-local`, and `--extra` while preserving `config.json`.
- For full build/test/debug cycles, clean runtime data first (recommended: `--dry-run`, then `--yes`, `pytest tests/`, `ruff check . --select C901`, `ruff format .`) and register new runtime paths in `.gitignore`.

## Engineering Rationale and Governance

This section centralizes design rationale that is intentionally excluded from `AGENTS.md`.

1. **`src/`-only source layout**
   - Keeps import behavior explicit and avoids root-level script drift.
   - Reduces ambiguity between package code and tooling scripts.
2. **ConfigManager as single runtime path/config authority**
   - Prevents path fragmentation and hidden assumptions in handlers/services.
   - Ensures local/user data locations are environment-resolved consistently.
3. **Scans-first runtime model**
   - `scans/` remains the operational source for viewer, OCR, and crop tools.
   - `temp_images/<doc_id>` is a staging layer for validated pages and segmented retries.
   - Native PDF support is an ingestion strategy, not a runtime storage replacement.
4. **Complexity ceiling (C901 <= 10)**
   - Enforces decomposition into testable single-purpose helpers.
   - Reduces regression risk in flow-heavy services (download, OCR, resolvers).
5. **Procedural policy split**
   - `AGENTS.md`: procedural rules and required command flows only.
   - `docs/ARCHITECTURE.md`: rationale, tradeoffs, and system-level decisions.
