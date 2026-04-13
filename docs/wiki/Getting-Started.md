# Getting Started

Use this page for the shortest path to a working local install. Continue to the docs site for the full documentation set.

## Quick Start

```bash
git clone https://github.com/nikazzio/scriptoria.git
cd scriptoria
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
scriptoria
```

Open `http://127.0.0.1:8000`.

## CLI Quick Path

```bash
scriptoria-cli "<manifest-url>"
```

Any supported IIIF manifest URL can be used directly. Provider URLs and supported identifiers can be resolved through the web application.

## Main Workflow

1. Resolve an item in `Discovery`.
2. Add it to `Library`.
3. Download only when you need local assets.
4. Open it in `Studio`.
5. Export from `Output`.

## Read Next

- [Docs Home](../index.md)
- [First Manuscript Workflow](../guides/first-manuscript-workflow.md)
- [Common Workflows](Common-Workflows.md)
