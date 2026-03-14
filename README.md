# Universal IIIF Downloader & Studio

[![CI](https://github.com/nikazzio/universal-iiif-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/nikazzio/universal-iiif-studio/actions/workflows/ci.yml)
[![Release](https://github.com/nikazzio/universal-iiif-studio/actions/workflows/release.yml/badge.svg)](https://github.com/nikazzio/universal-iiif-studio/actions/workflows/release.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Lint: Ruff](https://img.shields.io/badge/lint-ruff-46a2f1?logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/)

Developer-focused toolkit for downloading IIIF manuscripts and working with them via:
- a FastHTML/HTMX web studio (`iiif-studio`)
- a command-line interface (`iiif-cli`)

## Quickstart

```bash
git clone https://github.com/nikazzio/universal-iiif-studio.git
cd universal-iiif-studio
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
iiif-studio
```

Open: `http://127.0.0.1:8000`

Smoke test CLI:

```bash
iiif-cli "https://digi.vatlib.it/iiif/MSS_Urb.lat.1779/manifest.json"
```

## Features

- IIIF manifest resolution and page download pipeline
- **Centralized HTTP client** with automatic retry, exponential backoff, and per-host rate limiting
- Discovery with shared provider registry for web + CLI
- Discovery with free-text search plus provider-specific filters (currently Gallica type filter with labels `Tutti i materiali`, `Solo manoscritti`, `Solo libri a stampa`)
- Discovery internals split into typed orchestrator/search adapters (`universal_iiif_core.discovery`) and modular UI components (`studio_ui.components.discovery_*`)
- Native PDF-first workflow (configurable)
- Canvas/image fallback with optional compiled PDF generation
- Local Library + Studio workflow: select in Library, analyze in Studio
- Studio Output tab with PDF profiles, source-mode selection (`Locale` / `Remoto temporaneo`) and job monitor
- **Mirador dual viewing modes**: remote preview for incomplete downloads, local-only for offline work
- Thumbnail-level page controls in Studio Output (`Hi`, `Std`, `Opt`) with resolution transparency (`Locale`, `Remote`, verified-direct indicator)
- Professional status panel with color-coded technical indicators
- `src/` package layout with separated `core`, `ui`, and `cli` modules

## Run Modes

### Web Studio

```bash
iiif-studio
```

Alternative entrypoint:

```bash
python3 src/studio_app.py
```

Navigation model:
- `Discovery` supports free text/shelfmark/ID/URL search and provider-specific filters when available.
- `Aggiungi item` in Discovery performs a light prefetch (`metadata.json` + `manifest.json`) without full scans.
- `Library` is the canonical entrypoint for local documents.
- `Studio` is a document workspace (`/studio?doc_id=...&library=...`).
- `Export` is a dedicated hub for batch/single exports (`/export`).
- In Studio, the right tab is now `Output` (renamed from `Export`).
- `/studio` without context opens the `Riprendi lavoro` recent hub (server-side persisted contexts).

### CLI

```bash
iiif-cli "<manifest-url>"
```

Direct resolution is shared across web and CLI for these providers:
- Vaticana
- Gallica
- Institut de France
- Bodleian
- Heidelberg
- Cambridge
- e-codices
- Harvard
- Library of Congress
- Internet Archive

Current discovery search coverage:
- `search_first`: Gallica, Internet Archive
- `fallback`: Vaticana, Institut de France
- `direct + search adapter`: Bodleian, e-codices
- `direct only`: Heidelberg, Cambridge, Harvard, Library of Congress, generic direct manifest URLs

Provider behavior summary:

| Provider | Direct resolution | Free-text search | Notes |
| --- | --- | --- | --- |
| Vaticana | Yes | Yes | Hybrid flow: shelfmark heuristics first, DigiVatLib manuscripts search fallback for free text |
| Gallica | Yes | Yes | Uses SRU search and optional type filter |
| Institut de France | Yes | Yes | HTML search + manifest enrichment |
| Bodleian | Yes | Yes | JSON-LD search surface |
| Heidelberg | Yes | No | Direct resolver only for now |
| Cambridge | Yes | No | Direct resolver only for now |
| e-codices | Yes | Yes | HTML search surface |
| Harvard | Yes | No | Direct resolver only for now |
| Library of Congress | Yes | No | Direct resolver only; live manifest fetch may still be host-blocked in some environments |
| Internet Archive | Yes | Yes | `advancedsearch.php` + IIIF manifest validation |
| Altro / URL Diretto | Yes | No | Generic direct manifest resolution |

Search result contract:
- discovery providers return canonical `SearchResult` items with `manifest`, `library`, and `id`
- providers should populate `viewer_url` when they know the source viewer URL
- `raw` is still available for provider-specific metadata, but UI code should not depend on `raw["viewer_url"]` anymore

## Configuration

Runtime configuration is read from `config.json` through `universal_iiif_core.config_manager`.

Key PDF settings:

```json
{
  "settings": {
    "images": {
      "download_strategy_mode": "balanced",
      "download_strategy_custom": ["3000", "1740", "max"],
      "iiif_quality": "default"
    },
    "pdf": {
      "viewer_dpi": 150,
      "viewer_jpeg_quality": 95,
      "prefer_native_pdf": true,
      "create_pdf_from_images": false,
      "profiles": {
        "default": "balanced"
      }
    }
  }
}
```

Meaning:
- `prefer_native_pdf`: if manifest `rendering` contains a native PDF, native flow is attempted first
- `create_pdf_from_images`: when native PDF is not used, build a PDF from downloaded images only if `true`
- `viewer_dpi`: DPI used when extracting JPG pages from native PDF for the web viewer
- `viewer_jpeg_quality`: JPEG quality used only when rasterizing a native PDF into local scans
- `images.download_strategy_mode`: preset ordering for direct IIIF attempts before stitch fallback (`balanced|quality_first|fast|archival|custom`)
- `images.download_strategy_custom`: size list used when `mode=custom`; it is an ordered attempt list, not a “quality ranking”
- `images.stitch_mode_default`: fallback policy for the standard downloader (`auto_fallback|direct_only|stitch_only`)
- `images.iiif_quality`: IIIF quality segment in image URLs (recommended `default`)
- `images.local_optimize.max_long_edge_px`: in-place optimization max edge for local scans
- `images.local_optimize.jpeg_quality`: in-place optimization JPEG quality for local scans
- `pdf.profiles.default`: default export profile (`balanced`, `high_quality`, `archival_highres`, `lightweight`)
- `pdf.profiles.catalog.<profile>.max_parallel_page_fetch`: parallel fetch cap for remote high-res temp exports
- `storage.partial_promotion_mode`: controls if validated staged pages are promoted from temp to scans (`never|on_pause`)
- `storage.remote_cache.max_bytes|retention_hours|max_items`: persistent remote-resolution cache limits (Studio Output)
- `viewer.mirador.require_complete_local_images`: when `true`, Studio viewer is gated until local page availability is complete (set to `false` or use `?allow_remote_preview=true` URL parameter to enable remote preview mode)
- `viewer.source_policy.saved_mode`: policy for `saved` items in Studio (`remote_first|local_first`)
- `network.global.*`: global HTTP transport settings (timeout, retries, max concurrent jobs)
- `network.libraries.<library>.*`: per-library network policies for rate limiting and backoff (e.g., Gallica has stricter limits: 4 req/min)
- PDF profiles are created/edited in `Settings > PDF Export`; item Output tab selects a profile per job

## Output Layout

For each manuscript:
- `downloads/<Library>/<DocumentId>/scans/`: page images (`pag_XXXX.jpg`)
- `downloads/<Library>/<DocumentId>/pdf/`: native and/or compiled PDF outputs
- `downloads/<Library>/<DocumentId>/data/`: metadata and processing JSON artifacts
- `data/local/temp_images/<DocumentId>/`: staging area for validated pages before final promotion to `scans/`

Prefetch-light behavior:
- `Aggiungi item` creates/updates `downloads/<Library>/<DocumentId>/data/metadata.json` and `manifest.json`.
- Full page images are not downloaded until explicit `download_full`/`start_download`.

All runtime paths are resolved via `ConfigManager`.

Download staging behavior:
- runtime validates pages in `temp_images/<DocumentId>` and promotes to `scans/` when completeness gates are satisfied.
- segmented/retry runs are supported: previously staged validated pages are counted together with current-run pages.
- optional pause-time promotion is controlled by `settings.storage.partial_promotion_mode`.
- with `on_pause`, staged pages are promoted when a running job is paused; existing scans are overwritten only for explicit refresh/redownload flows.
- Studio page actions (`Hi`/`Std`) can overwrite a single local scan immediately without waiting for full-manuscript completeness.

## Dev Commands

```bash
pytest tests/
ruff check . --select C901
ruff format .
```

## Troubleshooting

`iiif-studio: command not found`
- Ensure virtualenv is active and reinstall editable package:
  ```bash
  source .venv/bin/activate
  pip install -e .
  ```

`ruff: command not found`
- Install dev dependencies:
  ```bash
  pip install -r requirements-dev.txt
  ```

`Address already in use` on startup
- Port `8000` is already in use. Stop the conflicting process, then rerun `iiif-studio`.

Studio loads but pages are missing
- Check `downloads/<Library>/<DocumentId>/scans/` for `pag_XXXX.jpg` files.
- Check `data/local/temp_images/<DocumentId>/` for staged pages.
- If pages are intentionally kept staged, use `settings.storage.partial_promotion_mode=on_pause` to promote on pause.
- Verify `config.json` PDF flags (`prefer_native_pdf`, `create_pdf_from_images`).
- For incomplete downloads, use `?allow_remote_preview=true` URL parameter to view all pages via remote preview mode (Mirador fetches images on-demand from original server).

Mirador viewer shows "remote" or no images for incomplete download
- **Expected behavior**: By default (`viewer.mirador.require_complete_local_images=true`), Studio gates the viewer until all pages are downloaded locally.
- **Remote preview mode**: Add `?allow_remote_preview=true` to the Studio URL to enable remote mode, where Mirador loads the original manifest and fetches images on-demand from the library server.
- **Local-only mode**: Once download is complete, Studio automatically switches to local mode using only downloaded images (works offline).
- See `docs/wiki/Studio-Workflow.md` for detailed explanation of viewing modes.

No results in Discovery for a known Gallica title
- Keep the `Gallica` filter on `All materials` for broad lookup.
- Use `Manuscripts` or `Printed books` only when you want to narrow down result type.

`/studio` opens the recent hub instead of the editor
- Expected behavior: without `doc_id` + `library`, Studio shows `Riprendi lavoro`.
- Open a document from Library via "Apri Studio", or use "Riprendi ultimo" in `/studio`.

`config.json` changes not applied
- Validate JSON shape under `settings`.
- Restart the running process.
- Compare with `config.example.json`.

## Documentation

- User/feature guide: `docs/DOCUMENTAZIONE.md`
- Architecture: `docs/ARCHITECTURE.md`
- HTTP Client implementation: `docs/HTTP_CLIENT.md`
- Config reference (single source for `config.json` keys): `docs/CONFIG_REFERENCE.md`
- Wiki maintenance model and sync workflow: `docs/WIKI_MAINTENANCE.md`
- Issue triage and governance policy: `docs/ISSUE_TRIAGE_POLICY.md`
- Contributor/agent rules: `AGENTS.md`
