# Getting Started

Scriptoria supports two primary entry points:

- `scriptoria` for the web application;
- `scriptoria-cli "<manifest-url>"` for direct CLI-driven download and inspection tasks.

## Install

```bash
git clone https://github.com/nikazzio/scriptoria.git
cd scriptoria
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Start The Web App

```bash
scriptoria
```

Open `http://127.0.0.1:8000`.

## First Workflow

1. Open `Discovery`.
2. Resolve a manifest URL, provider URL, shelfmark, or supported identifier.
3. Add the item to `Library`.
4. Start the download only when you actually want local assets.
5. Open the item in `Studio`.
6. Export a PDF from `Output` when needed.

## CLI Quick Start

```bash
scriptoria-cli "https://digi.vatlib.it/iiif/MSS_Urb.lat.1779/manifest.json"
```

Use the CLI when you need a direct, scriptable workflow without opening the web interface.

## Next Steps

- [First Manuscript Workflow](../guides/first-manuscript-workflow.md)
- [Configuration Overview](../reference/configuration.md)
- [CLI Reference](../reference/cli.md)
