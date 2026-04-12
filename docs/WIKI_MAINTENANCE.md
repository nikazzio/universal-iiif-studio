# Wiki Maintenance Guide

This repository uses a `docs-as-source, wiki-as-publish` model.

## Source Of Truth

- Repository documentation in `docs/` is the primary source of truth.
- GitHub Wiki content is derived from `docs/wiki/`.
- The published wiki should remain shorter and more reader-friendly than the full repository documentation.

## Publishing Rules

- Always edit wiki source pages in `docs/wiki/`.
- Do not treat the GitHub Wiki as an editable source.
- Keep wiki pages concise and link back to canonical repo docs for depth.
- All documentation prose must be English-only.

## Sync Tool

- Source pages: `docs/wiki/`
- Sync script: `scripts/sync_wiki.py`
- Wiki remote: `<repo>.wiki.git`

The sync script is responsible for more than file copy:

- mirroring wiki source pages into the wiki repository;
- rewriting links so published pages do not point to non-published local paths;
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

## CI Model

The repository already contains a dedicated wiki workflow.

Expected behavior:

- `Wiki Sync` runs a dry-run validation first.
- Publishing only happens after the dry-run job succeeds.
- The workflow uses `GITHUB_TOKEN` with `contents: write`.

## Authoring Guidelines

- Keep page titles stable.
- Prefer task-oriented headings.
- Use links to canonical docs instead of duplicating full technical detail.
- Keep internal wiki links relative within `docs/wiki/`.
- Use absolute GitHub links only for documents that are not published into the wiki.

## Required Wiki Pages

- `Home.md`
- `Getting-Started.md`
- `Configuration.md`
- `Studio-Workflow.md`
- `PDF-Export-Profiles.md`
- `FAQ.md`
