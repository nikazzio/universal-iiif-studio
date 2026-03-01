# 🏗️ Project Architecture

## Overview

Universal IIIF Downloader & Studio separates a **FastHTML/htmx-based UI shell** (`studio_ui/`) from the pure Python core (`universal_iiif_core/`). The UI renders HTML elements, wires HTMX for asynchronous swaps, and embeds Mirador, while the back-end keeps all metadata, storage, OCR logic, and network resolution untouchable.

## System Layers

The application is strictly divided into two main layers. The **UI Layer** depends on the **Core Layer**, never the other way around.

### 1. Presentation Layer (`studio_ui/`)

* **Pages**: Layout builders (`studio_layout`, Mirador wiring).
* **Components**: Reusable UI parts (tab sets, toast holder, SimpleMDE-powered editor, Mirador viewer, snippet cards).
* **Routes**:
  * `studio_handlers.py`: Logic-heavy handlers for the editor, viewer, and OCR operations.
  * `discovery_handlers.py`: Orchestrates search, add-to-library, and download manager actions.
  * `library_handlers.py`: Local Assets listing, cleanup, retry, and deletion actions.
* **Common**: Shared utilities (`build_toast`, htmx triggers, Mirador window presets).

### 2. Core Business Logic (`universal_iiif_core/`)

* **Discovery Module**:
  * **Resolvers**: Uses a Dispatcher pattern (`resolve_shelfmark`) to route inputs to specific implementations (`Vatican`, `Gallica`, `Oxford`, `Institut de France`).
  * **Search**: Implements Gallica SRU parsing with optional type filtering (`all`, `manuscripts`, `printed books`) and fallback/stub logic where APIs are limited.
* **Downloader Logic**:
  * Implements the **Golden Flow** (Native PDF check -> Extraction -> Fallback to IIIF).
  * Manages threading and DB updates.
* **Network Layer (`utils.py`)**:
  * Provides a resilient `requests.Session`.
  * Handles WAF Bypass (Browser User-Agents, Dynamic Brotli).
* **OCR Module**:
  * Abstracts differences between local Kraken models and Cloud APIs (OpenAI/Anthropic).
* **Storage**:
  * `VaultManager`: SQLite interface for metadata and job tracking (`queued/running/partial/complete` states).

---

## Interactive Flows

### 1. Discovery, Library Add, and Resolution

1. **User Input**: The user enters free text, shelfmark (e.g., "Urb.lat.1779"), an ID, or a URL.
2. **Dispatcher**: `resolve_shelfmark` detects the library signature and selects the correct strategy.
3. **Normalization**: The resolver converts "dirty" inputs into a canonical IIIF Manifest URL.
4. **Gallica Filter Stage**: Optional type filters are applied on parsed metadata (`dc:type`) to avoid SRU type-filter inconsistencies.
5. **Preview**: The UI fetches basic metadata and lazy-checks native PDF availability.
6. **Action Split**: From each result, the user can either add to local Library (`saved`) or add + enqueue download.

### 2. Download Manager + Golden Flow

Downloads are queued in a DB-backed manager with bounded concurrency (`settings.system.max_concurrent_downloads`).
Queued jobs are promoted FIFO (with optional prioritization) and each running worker follows this flow:

1. **Check Native PDF**: Does the manifest provide a download link?
    * **YES + `settings.pdf.prefer_native_pdf=true`**: Download the PDF. Then, **EXTRACT** pages to high-quality JPGs in `scans/` (Critical for Studio compatibility).
    * **NO**: Fallback to downloading IIIF tiles/canvases one by one into `scans/`.
2. **Optional Compiled PDF**: If (and only if) no native PDF was used **AND** `settings.pdf.create_pdf_from_images=true`, generate a PDF from the downloaded images.
3. **Completion**: Update DB status and manuscript `asset_state` (`complete` or `partial`).

### 3. Studio & OCR

0. **Entry Point**: Library is the canonical selector; `/studio` without `doc_id/library` redirects to `/library`.
1. **Async Request**: Clicking "Run OCR" sends an HTMX POST to `/api/run_ocr_async`.
2. **Job State**: The server spawns a thread and tracks progress in `ocr_state.py`.
3. **Polling**: The UI shows an overlay that polls `/api/check_ocr_status` every 2 seconds.
4. **Completion**: Text is saved to `transcription.json` and the History table.

---

## UI & Configuration Details

* **Viewer Config**: The `config.json` (`settings.viewer`) section directly controls Mirador's behavior (Zoom levels) and the Visual Tab's default image filters.
* **State Persistence**:
  * **Server-side**: SQLite (`vault.db`) and JSON files (`data/local/`).
  * **Client-side**: Sidebar state (collapsed/expanded) is saved in `localStorage`.
* **Visual Feedback**:
  * **Toasts**: Floating notifications anchored to the top-right viewport.
  * **Progress**: Real-time queue/running status driven by DB polling in the Download Manager side panel.

## Key Design Decisions

1. **Scans as Source of Truth**: The `scans/` directory must always contain extracted JPGs. The Viewer, OCR, and Cropper tools rely on these files, regardless of whether the source was a IIIF server or a PDF.
2. **Zero Legacy**: Deprecated APIs are removed or stubbed. No "dead code" is allowed in the codebase.
3. **Network Resilience**: The system assumes library servers are hostile (rate limits, firewalls) and uses aggressive retry logic and header mimicking.
4. **Pure HTTP Front-end**: No heavy client-side frameworks (React/Vue). The UI logic is driven by Python via FastHTML and HTMX.

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
   - Native PDF support is an ingestion strategy, not a runtime storage replacement.
4. **Complexity ceiling (C901 <= 10)**
   - Enforces decomposition into testable single-purpose helpers.
   - Reduces regression risk in flow-heavy services (download, OCR, resolvers).
5. **Procedural policy split**
   - `AGENTS.md`: procedural rules and required command flows only.
   - `docs/ARCHITECTURE.md`: rationale, tradeoffs, and system-level decisions.
