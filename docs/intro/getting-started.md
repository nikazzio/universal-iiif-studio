# Getting Started

This page is the shortest reliable path to a working local installation and a first useful session. It does not try to document every feature. Its purpose is to get you from clone to a real manuscript workflow without confusion about what the application is doing.

Scriptoria exposes two entry points. `scriptoria` starts the web application and gives you the complete workflow. `scriptoria-cli "<manifest-url>"` is the direct CLI path when you already know the exact item you want. For most users, the web application is the right starting point because it exposes discovery, local cataloging, Studio work, and export in one place.

## Prerequisites

You need Python 3.10 or newer, a local virtual environment, and the project installed in editable mode.

## Install

```bash
git clone https://github.com/nikazzio/scriptoria.git
cd scriptoria
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Start The Web Application

```bash
scriptoria
```

Then open `http://127.0.0.1:8000`.

At first start, expect a local-first application rather than a public website. Even when you work against remote IIIF sources, Scriptoria is already building a managed local record of the item and preparing its runtime workspace.

## What You Will See

The interface is organized into four operational surfaces. `Discovery` resolves external inputs into candidate items. `Library` tracks the items already known to your local workspace. `Studio` opens one manuscript in a working context. `Output` handles page inspection, export preparation, and finished artifacts.

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

Use the CLI when you already know the exact manuscript and do not need the full interactive workflow.

Example:

```bash
scriptoria-cli "https://digi.vatlib.it/iiif/MSS_Urb.lat.1779/manifest.json"
```

The CLI is a good fit for:

- direct acquisition of known items;
- shell-based workflows;
- scripted processing;
- environments where you do not need the full Studio and Output surfaces.

## What To Read Next

If this first session worked as expected, continue with [First Manuscript Workflow](../guides/first-manuscript-workflow.md) and then [Discovery And Library](../guides/discovery-and-library.md). When you start using the item workspace seriously, read [Studio Workflow](../guides/studio-workflow.md) and [PDF Export](../guides/pdf-export.md). If you need to tune behavior rather than just use the defaults, move on to [Configuration Overview](../reference/configuration.md).
