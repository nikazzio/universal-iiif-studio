<p align="center">
  <img src="assets/header.svg" alt="Scriptoria" width="100%">
</p>

<p align="center">
  <a href="https://github.com/nikazzio/scriptoria/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/nikazzio/scriptoria/ci.yml?branch=main&label=CI&style=flat-square"></a>
  <a href="https://github.com/nikazzio/scriptoria/actions/workflows/docs-ci.yml"><img alt="Docs" src="https://img.shields.io/github/actions/workflow/status/nikazzio/scriptoria/docs-ci.yml?branch=main&label=Docs&style=flat-square"></a>
  <a href="https://codecov.io/gh/nikazzio/scriptoria"><img alt="Coverage" src="https://img.shields.io/codecov/c/github/nikazzio/scriptoria?style=flat-square&logo=pytest&label=coverage"></a>
  <a href="https://www.python.org/"><img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10+-3572A5?style=flat-square&logo=python&logoColor=white"></a>
  <a href="https://github.com/nikazzio/scriptoria/releases"><img alt="Release" src="https://img.shields.io/github/v/release/nikazzio/scriptoria?display_name=tag&style=flat-square&color=0b7285"></a>
  <a href="LICENSE"><img alt="MIT" src="https://img.shields.io/badge/license-MIT-22d3ee?style=flat-square"></a>
</p>

<p align="center">
  <strong>Scriptoria</strong> — a research workbench for IIIF manuscripts.
</p>

---

> **Web** &nbsp;`scriptoria` → [127.0.0.1:8000](http://127.0.0.1:8000) &emsp;·&emsp;
> **CLI** &nbsp;`scriptoria-cli "<manifest-url>"`

<!-- TODO: add real screenshots
<p align="center">
  <img src="assets/screenshot-discovery.png" width="32%" alt="Discovery">
  <img src="assets/screenshot-studio.png" width="32%" alt="Studio">
  <img src="assets/screenshot-export.png" width="32%" alt="Export">
</p>
-->

## Quickstart

```bash
git clone https://github.com/nikazzio/scriptoria.git
cd scriptoria
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
scriptoria
```

## How It Works

```mermaid
flowchart LR
    A[🔍 Discovery] --> B[📚 Library]
    B --> C[📖 Studio]
    C --> D[📤 Output]

    A -. search/resolve .-> R[(Provider Registry)]
    B -. local assets .-> V[(Vault)]
    C -. manifests .-> V
    D -. export jobs .-> V
```

| Tab | What it does |
| --- | --- |
| **Discovery** | Resolve URLs, IDs, shelfmarks. Search 10+ IIIF libraries. |
| **Library** | Browse and manage your local manuscript collection. |
| **Studio** | Document workspace — Mirador viewer, OCR transcription, page actions. |
| **Output** | PDF inventory, thumbnail-level actions, export job queue. |

## Key Features

- **10+ IIIF providers** — Vatican, Gallica, Harvard, Bodleian, Heidelberg, LoC, Archive.org, Cambridge, e-codices, Institut
- **Provider registry** — shared resolution for web UI and CLI
- **PDF export profiles** — local and remote high-res modes with quality presets
- **Centralized HTTP** — retries, exponential backoff, per-library network policies
- **Local-first workflow** — reproducible storage, no cloud dependencies

## CLI

```bash
scriptoria-cli "https://digi.vatlib.it/iiif/MSS_Urb.lat.1779/manifest.json"
```

Any IIIF-compliant manifest URL works directly.

## Documentation

| | |
| --- | --- |
| 🗂️ [Docs Home](https://nikazzio.github.io/scriptoria/) | 🚀 [Getting Started](https://nikazzio.github.io/scriptoria/intro/getting-started) |
| 🏗️ [Architecture](https://nikazzio.github.io/scriptoria/explanation/architecture) | ⚙️ [Config Overview](https://nikazzio.github.io/scriptoria/reference/configuration) |
| 💻 [CLI Reference](https://nikazzio.github.io/scriptoria/reference/cli) | 📖 [Wiki](https://github.com/nikazzio/scriptoria/wiki) |

## Development

```bash
pytest tests/                    # tests
ruff check . --fix               # lint
ruff format .                    # format
ruff check . --select C901       # complexity
```

## Troubleshooting

<details>
<summary><code>scriptoria: command not found</code></summary>

```bash
source .venv/bin/activate && pip install -e .
```
</details>

<details>
<summary><code>ruff: command not found</code></summary>

```bash
source .venv/bin/activate && pip install -r requirements-dev.txt
```
</details>

<details>
<summary>Port 8000 already in use</summary>

Stop the conflicting process and restart `scriptoria`.
</details>

<details>
<summary>Studio opens without a document</summary>

Expected. Open an item from Library, or use the recent-work hub at `/studio`.
</details>

---

<p align="center">
  <sub>Built for manuscript-heavy research workflows · <a href="LICENSE">MIT</a></sub>
</p>
