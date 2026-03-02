# Getting Started

Quick setup for running Universal IIIF Studio locally.

## Quick Start

```bash
git clone https://github.com/nikazzio/universal-iiif-studio.git
cd universal-iiif-studio
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
iiif-studio
```

Open `http://127.0.0.1:8000`.

## CLI

```bash
iiif-cli "<manifest-url>"
```

## Main Navigation (Web Studio)

- `Discovery`: resolve and queue downloads.
- `Library`: local assets entrypoint.
- `Studio`: document workspace.
- `Export`: batch/single export hub.

## Canonical Docs

- Full setup and troubleshooting: [README.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/README.md)
- User guide: [DOCUMENTAZIONE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/DOCUMENTAZIONE.md)
- Architecture details: [ARCHITECTURE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/ARCHITECTURE.md)
