# Getting Started

## Requirements

- Python 3.10+
- Git

## Installation

```bash
git clone https://github.com/nikazzio/universal-iiif-downloader.git
cd universal-iiif-downloader
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run Web Studio

```bash
iiif-studio
```

Open `http://127.0.0.1:8000`.

## Run CLI

```bash
iiif-cli "<manifest-url>"
```

## Main Navigation

- `Discovery`: resolve and queue downloads.
- `Library`: local assets entrypoint.
- `Studio`: document workspace.
- `Export`: batch/single export hub.
