# Getting Started

Use this page for the shortest path to a working local install.

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

## CLI

```bash
scriptoria-cli "<manifest-url>"
```

## Main Navigation

- `Discovery` resolves provider inputs and search results.
- `Library` is the canonical entrypoint for local items.
- `Studio` is the working workspace for a selected document.
- `Output` is the export surface inside Studio.

If `/studio` is opened without `doc_id` and `library`, the app shows the recent-work hub instead of an empty editor.

## Read Next

- [Documentation Hub](../index.md)
- [User Guide](https://github.com/nikazzio/scriptoria/blob/main/docs/DOCUMENTAZIONE.md)
- [Configuration Reference](https://github.com/nikazzio/scriptoria/blob/main/docs/CONFIG_REFERENCE.md)
