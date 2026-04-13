# Getting Started

Use this page when you need the shortest reliable path to a working local install.

## Quick Install

```bash
git clone https://github.com/nikazzio/scriptoria.git
cd scriptoria
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
scriptoria
```

Then open `http://127.0.0.1:8000`.

## What To Do First

The normal first workflow is straightforward:

1. resolve a manuscript in `Discovery`;
2. add it to `Library`;
3. download only when local assets are actually needed;
4. open it in `Studio`;
5. use `Output` for inspection and export.

## CLI Shortcut

```bash
scriptoria-cli "<manifest-url>"
```

Use the CLI when you already have the exact IIIF manifest and do not need the full interactive workflow.

## Read Next

- [Docs Home](../index.md)
- [First Manuscript Workflow](../guides/first-manuscript-workflow.md)
- [Provider Support](../reference/provider-support.md)
