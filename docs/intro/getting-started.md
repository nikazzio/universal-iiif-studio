# Getting Started

Scriptoria supports two primary entry points:

- `scriptoria` for the web application;
- `scriptoria-cli "<manifest-url>"` for direct CLI-driven download and inspection tasks.

The recommended starting point is the web application. It exposes the full workflow: discovery, local cataloging, Studio reading, and PDF export. The CLI is useful when you already know the document you need and want a direct download-oriented path.

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

## What To Expect In The Interface

The application is local-first. Even when you work with remote IIIF material, Scriptoria builds a managed local record for the item and can progressively enrich that record with downloaded assets.

At a high level:

- `Discovery` resolves identifiers, URLs, and provider search results into candidate items;
- `Library` stores the known items and their local state;
- `Studio` opens one item in a reading and working context;
- `Output` manages PDF exports and page-level asset actions.

## First Workflow

1. Open `Discovery`.
2. Resolve a manifest URL, provider URL, shelfmark, or supported identifier.
3. Add the item to `Library`.
4. Start the download only when you actually want local assets.
5. Open the item in `Studio`.
6. Export a PDF from `Output` when needed.

## Choosing The Right Input

Scriptoria accepts several input styles, but not every provider is equally good at all of them.

- Best case: a direct IIIF manifest URL.
- Very good: a provider item URL that the resolver knows how to normalize.
- Often good: a provider-specific identifier or shelfmark, such as `Urb.lat.1779`.
- Variable: free-text search. Some providers expose reliable search adapters; others are better handled with explicit identifiers or URLs.

Before you start large-scale work, read [Provider Support](../reference/provider-support.md). It explains what kind of reference is most reliable for each supported library.

## CLI Quick Start

```bash
scriptoria-cli "https://digi.vatlib.it/iiif/MSS_Urb.lat.1779/manifest.json"
```

Use the CLI when you need a direct, scriptable workflow without opening the web interface.

Typical CLI use cases:

- resolve and download one known manuscript quickly;
- inspect local database state;
- work in shell scripts or batch-oriented environments;
- avoid the web UI when you only need direct acquisition.

## Next Steps

- [First Manuscript Workflow](../guides/first-manuscript-workflow.md)
- [Discovery And Library](../guides/discovery-and-library.md)
- [Studio Workflow](../guides/studio-workflow.md)
- [Configuration Overview](../reference/configuration.md)
- [CLI Reference](../reference/cli.md)
