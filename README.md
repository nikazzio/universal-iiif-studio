# Universal IIIF Downloader & Studio

<p align="center">
  <a href="https://github.com/nikazzio/universal-iiif-studio/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/nikazzio/universal-iiif-studio/ci.yml?branch=main&style=for-the-badge&label=CI"></a>
  <a href="https://github.com/nikazzio/universal-iiif-studio/actions/workflows/docs-ci.yml"><img alt="Docs CI" src="https://img.shields.io/github/actions/workflow/status/nikazzio/universal-iiif-studio/docs-ci.yml?branch=main&style=for-the-badge&label=Docs"></a>
  <a href="https://github.com/nikazzio/universal-iiif-studio/actions/workflows/wiki-sync.yml"><img alt="Wiki Sync" src="https://img.shields.io/github/actions/workflow/status/nikazzio/universal-iiif-studio/wiki-sync.yml?branch=main&style=for-the-badge&label=Wiki"></a>
  <a href="https://www.python.org/"><img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-0f172a?style=for-the-badge&logo=python&logoColor=white"></a>
  <a href="https://docs.astral.sh/ruff/"><img alt="Ruff" src="https://img.shields.io/badge/Lint-Ruff-1d4ed8?style=for-the-badge&logo=ruff&logoColor=white"></a>
  <a href="https://github.com/nikazzio/universal-iiif-studio/releases"><img alt="Release" src="https://img.shields.io/github/v/release/nikazzio/universal-iiif-studio?display_name=tag&style=for-the-badge"></a>
  <a href="LICENSE"><img alt="License MIT" src="https://img.shields.io/badge/License-MIT-0b7285?style=for-the-badge"></a>
</p>

<p align="center">
  <img src="docs/assets/readme-hero.svg" alt="Universal IIIF Downloader &amp; Studio hero" width="1200">
</p>

```text
 _   _       _                          _   ___ ___ ___ _____
| | | |_ __ (_)_   _____ _ __ ___  __ _| | |_ _|_ _|_ _|  ___|
| | | | '_ \| \ \ / / _ \ '__/ __|/ _` | |  | | | | | || |_
| |_| | | | | |\ V /  __/ |  \__ \ (_| | |  | | | | | ||  _|
 \___/|_| |_|_| \_/ \___|_|  |___/\__,_|_| |___|___|___|_|

 ____                      _                 _              _ _
|  _ \  _____      ___ __ | | ___   __ _  __| | ___ _ __   | (_)_ __   ___ _ __
| | | |/ _ \ \ /\ / / '_ \| |/ _ \ / _` |/ _` |/ _ \ '__|  | | | '_ \ / _ \ '__|
| |_| | (_) \ V  V /| | | | | (_) | (_| | (_| |  __/ |     | | | | | |  __/ |
|____/ \___/ \_/\_/ |_| |_|_|\___/ \__,_|\__,_|\___|_|     |_|_|_| |_|\___|_|
```

Download IIIF material, keep local working copies under control, and move from discovery to study to export without leaving one toolchain.

## Why This Project

Universal IIIF Downloader & Studio combines two workflows that are usually split apart:

- `iiif-studio` for Discovery, Library, Studio, and PDF export.
- `iiif-cli` for direct manifest-driven downloads and scripting.
- Shared provider resolution, storage, and configuration for both entrypoints.

The project is optimized for manuscript-heavy research workflows where you need fast iteration, reproducible local storage, and enough control over remote IIIF servers to avoid brittle ad-hoc tooling.

```mermaid
flowchart LR
    A[Discovery] --> B[Library]
    B --> C[Studio]
    C --> D[Output]
    D --> E[PDF Export]

    A -. resolve/search .-> X[(Provider Registry)]
    B -. local assets .-> Y[(Vault + Downloads)]
    C -. manifests/scans .-> Y
    E -. profiles/cache/jobs .-> Y
```

## Quickstart

```bash
git clone https://github.com/nikazzio/universal-iiif-studio.git
cd universal-iiif-studio
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
iiif-studio
```

Open `http://127.0.0.1:8000`.

CLI smoke test:

```bash
iiif-cli "https://digi.vatlib.it/iiif/MSS_Urb.lat.1779/manifest.json"
```

## Feature Highlights

- Shared provider registry for web and CLI resolution.
- Search adapters for major IIIF sources plus direct manifest handling.
- Local-first study workflow with Library, Studio workspace, and Output tab.
- Remote preview vs local-only viewing modes in Mirador.
- PDF profile system with local and temporary remote high-resolution export modes.
- Centralized HTTP client with retries, backoff, and per-library policies.

## Run Modes

### Web Studio

```bash
iiif-studio
```

Alternative entrypoint:

```bash
python3 src/studio_app.py
```

### CLI

```bash
iiif-cli "<manifest-url>"
```

## Documentation Map

- [Documentation Hub](docs/index.md)
- [User Guide](docs/DOCUMENTAZIONE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Configuration Reference](docs/CONFIG_REFERENCE.md)
- [HTTP Client Notes](docs/HTTP_CLIENT.md)
- [Wiki Maintenance](docs/WIKI_MAINTENANCE.md)
- [GitHub Wiki Source](docs/wiki/Home.md)

## Current Product Shape

- `Discovery` resolves URLs, IDs, shelfmarks, and provider-specific free-text search.
- `Library` is the canonical entrypoint for local items.
- `Studio` opens a document workspace and falls back to a recent-work hub when no item is selected.
- `Output` handles PDF inventory, thumbnail-level page actions, and export jobs.

## Troubleshooting

`iiif-studio: command not found`

```bash
source .venv/bin/activate
pip install -e .
```

`ruff: command not found`

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Port `8000` already in use:

- Stop the conflicting process and start `iiif-studio` again.

Studio opens without a document:

- Expected behavior. Open an item from `Library`, or resume from the recent-work hub at `/studio`.

## Development Commands

```bash
pytest tests/
ruff check . --select C901
ruff format .
```
