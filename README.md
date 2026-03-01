# Universal IIIF Downloader & Studio

[![CI](https://github.com/nikazzio/universal-iiif-downloader/actions/workflows/ci.yml/badge.svg)](https://github.com/nikazzio/universal-iiif-downloader/actions/workflows/ci.yml)
[![Release](https://github.com/nikazzio/universal-iiif-downloader/actions/workflows/release.yml/badge.svg)](https://github.com/nikazzio/universal-iiif-downloader/actions/workflows/release.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Lint: Ruff](https://img.shields.io/badge/lint-ruff-46a2f1?logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/)

Developer-focused toolkit for downloading IIIF manuscripts and working with them via:
- a FastHTML/HTMX web studio (`iiif-studio`)
- a command-line interface (`iiif-cli`)

## Quickstart

```bash
git clone https://github.com/nikazzio/universal-iiif-downloader.git
cd universal-iiif-downloader
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
- Discovery with free-text search plus optional Gallica filters (`all`, `manuscripts`, `printed books`)
- Native PDF-first workflow (configurable)
- Canvas/image fallback with optional compiled PDF generation
- Local Library + Studio workflow: select in Library, analyze in Studio
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
- `Discovery` supports free text/shelfmark/ID/URL search and optional Gallica type filters.
- `Library` is the canonical entrypoint for local documents.
- `Studio` is a document workspace (`/studio?doc_id=...&library=...`).
- `Export` is a dedicated hub for batch/single exports (`/export`).
- `/studio` without context redirects to `/library`.

### CLI

```bash
iiif-cli "<manifest-url>"
```

## Configuration

Runtime configuration is read from `config.json` through `universal_iiif_core.config_manager`.

Key PDF settings:

```json
{
  "settings": {
    "pdf": {
      "viewer_dpi": 150,
      "ocr_dpi": 300,
      "prefer_native_pdf": true,
      "create_pdf_from_images": false
    }
  }
}
```

Meaning:
- `prefer_native_pdf`: if manifest `rendering` contains a native PDF, native flow is attempted first
- `create_pdf_from_images`: when native PDF is not used, build a PDF from downloaded images only if `true`
- `viewer_dpi`: DPI used when extracting JPG pages from native PDF for the web viewer
- `ocr_dpi`: OCR-oriented DPI setting

## Output Layout

For each manuscript:
- `downloads/<Library>/<DocumentId>/scans/`: page images (`pag_XXXX.jpg`)
- `downloads/<Library>/<DocumentId>/pdf/`: native and/or compiled PDF outputs
- `downloads/<Library>/<DocumentId>/data/`: metadata and processing JSON artifacts

All runtime paths are resolved via `ConfigManager`.

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
- Verify `config.json` PDF flags (`prefer_native_pdf`, `create_pdf_from_images`).

No results in Discovery for a known Gallica title
- Keep the `Gallica` filter on `All materials` for broad lookup.
- Use `Manuscripts` or `Printed books` only when you want to narrow down result type.

`/studio` opens Library instead of the editor
- Expected behavior: Studio now requires `doc_id` + `library`.
- Open a document from Library via "Apri Studio".

`config.json` changes not applied
- Validate JSON shape under `settings`.
- Restart the running process.
- Compare with `config.example.json`.

## Documentation

- User/feature guide: `docs/DOCUMENTAZIONE.md`
- Architecture: `docs/ARCHITECTURE.md`
- Config reference (single source for `config.json` keys): `docs/CONFIG_REFERENCE.md`
- Contributor/agent rules: `AGENTS.md`
