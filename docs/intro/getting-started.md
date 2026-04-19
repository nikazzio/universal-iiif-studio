# Getting Started

This page is the shortest reliable path to a working local installation and a first useful session. It does not try to document every feature. Its purpose is to get you from clone to a real document workflow without confusion about what the application is doing.

Scriptoria exposes two entry points. `scriptoria` starts the web application and gives you the complete workflow. `scriptoria-cli "<manifest-url>"` is the direct CLI path when you already know the exact item you want. For most users, the web application is the right starting point because it exposes discovery, local cataloging, Studio work, and export in one place.

## Prerequisites

You need Python 3.10 or newer, a local virtual environment, and the project installed in editable mode. No system-level services are required for a first run: Scriptoria stores its catalog in a local SQLite vault and writes runtime data under a managed directory tree.

## Install

```bash
git clone https://github.com/nikazzio/scriptoria.git
cd scriptoria
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

After install, verify the binaries are on your path:

```bash
scriptoria --version
scriptoria-cli --version
```

Both should print the same version. The legacy aliases `iiif-studio` and `iiif-cli` are still installed and point to the same entry points, so older scripts and bookmarks continue to work.

## Start The Web Application

```bash
scriptoria
```

Then open `http://127.0.0.1:8000`. The default port is `8000` and is not currently configurable from the command line; if it is in use, free it on your side or run from a different shell session.

For active development, use the watcher mode:

```bash
scriptoria --reload
```

The watcher reloads on changes to `*.py` and `*.html` files and ignores runtime data directories so it does not restart on every download.

At first start, expect a local-first application rather than a public website. Even when you work against remote IIIF sources, Scriptoria is already building a managed local record of the item and preparing its runtime workspace.

## What You Will See

The interface is organized into four operational surfaces. `Discovery` resolves external inputs into candidate items. `Library` tracks the items already known to your local workspace. `Studio` opens one item in a working context. `Output` handles page inspection, export preparation, and finished artifacts.

Those surfaces are separate because they represent different states in the workflow. Discovery is not Library, and Library is not the same thing as a complete local download.

## Your First Useful Session

The simplest realistic path is:

1. Open `Discovery`.
2. Paste a direct IIIF manifest URL, a provider URL, a shelfmark, or another supported identifier.
3. Use `Add item` to create the local record.
4. Open the item in `Library`.
5. Download scans only if you need a real local working copy.
6. Open the item in `Studio`.
7. Use `Output` when you need page inspection or export.

If you only remember one thing, remember this: saving an item is not the same as downloading it.

## Choosing The Right Input

Scriptoria accepts multiple input styles, but the best one depends on the provider.

The general order of reliability is:

1. direct IIIF manifest URL;
2. provider item URL;
3. provider-specific shelfmark or identifier;
4. free-text query.

That last option is the least universal. Some providers are good at discovery-first search, while others behave much better when you already have a stable record reference. Before doing serious work across libraries, read [Provider Support](../reference/provider-support.md).

## When To Use The CLI

Use the CLI when you already know the exact document and do not need the full interactive workflow.

Example:

```bash
scriptoria-cli "https://digi.vatlib.it/iiif/MSS_Urb.lat.1779/manifest.json"
```

If you run `scriptoria-cli` with no positional argument, it enters an interactive wizard that asks for the URL, an optional output filename, and an optional OCR model. The wizard is intentionally minimal; for anything more advanced use explicit flags.

The CLI is a good fit for:

- direct acquisition of known items;
- shell-based workflows;
- scripted processing;
- environments where you do not need the full Studio and Output surfaces;
- inspecting or repairing local vault state without opening the web app.

See [CLI Reference](../reference/cli.md) for the complete flag list.

## Configuration On First Run

Scriptoria reads its runtime configuration from `config.json`, which controls network policy, image acquisition, viewer defaults, export behavior, storage retention, and test behavior. On first run a default configuration is written if one is not present, and runtime directories are created under `data/local/` (downloads, exports, logs, temp images, models, snippets).

You do not need to touch configuration for a first session. Once you start working seriously across providers, read [Configuration Overview](../reference/configuration.md) and, when you need exact behavior, [Detailed Configuration Reference](../CONFIG_REFERENCE.md).

## When Something Does Not Work

Most first-run friction comes from a small set of predictable cases:

- the input pasted into Discovery is too vague for the chosen provider;
- the item is `saved` but not yet downloaded, so Studio opens in remote mode and looks slower than expected;
- a partial download was interrupted and Library shows the item in a mid-state;
- the upstream provider rate-limited a fast acquisition.

Before assuming a bug, read [Troubleshooting](../guides/troubleshooting.md) and check `Provider Support` for any provider-specific caveats.

## What To Read Next

If this first session worked as expected, continue with [First Manuscript Workflow](../guides/first-manuscript-workflow.md) and then [Discovery And Library](../guides/discovery-and-library.md). When you start using the item workspace seriously, read [Studio Workflow](../guides/studio-workflow.md) and [PDF Export](../guides/pdf-export.md). If you need to tune behavior rather than just use the defaults, move on to [Configuration Overview](../reference/configuration.md).
