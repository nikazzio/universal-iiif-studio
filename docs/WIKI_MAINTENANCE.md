# Wiki Maintenance Guide

This repository uses a `docs-site-as-canonical, wiki-as-entry-layer` model.

## Source Of Truth

- Canonical public documentation lives in the Docusaurus docs site built from `docs/`.
- GitHub Wiki content is derived from `docs/wiki/`.
- The published wiki is intentionally short and should not behave like a second documentation set.

## Publishing Rules

- Always edit wiki source pages in `docs/wiki/`.
- Do not edit the GitHub Wiki directly.
- Keep wiki pages concise and task-oriented.
- Canonical links in wiki pages should point to the public docs site, not repository file views.
- All documentation prose must be English-only.

## Sync Tool

- Source pages: `docs/wiki/`
- Sync script: `scripts/sync_wiki.py`
- Wiki remote: `<repo>.wiki.git`

The sync script is responsible for:

- mirroring wiki source pages into the wiki repository;
- rewriting canonical docs links to the public docs site;
- failing in dry-run when a wiki page contains an invalid or non-publishable link.

## Manual Sync

Dry-run first:

```bash
python scripts/sync_wiki.py --repo owner/repo --dry-run
```

Publish when dry-run is clean:

```bash
python scripts/sync_wiki.py --repo owner/repo --push
```

## Required Wiki Pages

- `Home.md`
- `Getting-Started.md`
- `Common-Workflows.md`
- `Troubleshooting.md`
- `FAQ.md`
