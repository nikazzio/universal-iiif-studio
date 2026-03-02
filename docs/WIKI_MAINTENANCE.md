# Wiki Maintenance Guide

This project uses a "docs-as-source, wiki-as-publish" model.

## Why This Model

- Documentation quality stays in the main repo (`docs/`) with PR review and CI checks.
- GitHub Wiki stays lightweight for readers.
- Sync avoids drift between technical docs and wiki pages.

## Source and Publish Paths

- Wiki source files: `docs/wiki/`
- Sync script: `scripts/sync_wiki.py`
- GitHub Wiki remote: `<repo>.wiki.git`

## Manual Sync

1. Edit wiki pages under `docs/wiki/`.
1. Commit and merge to `main`.
1. Validate with dry-run:

```bash
python scripts/sync_wiki.py --repo owner/repo --dry-run
```

1. Publish with:

```bash
python scripts/sync_wiki.py --repo owner/repo --push
```

Notes:

- `Home.md` is required in `docs/wiki/`.
- By default, sync runs with prune enabled and removes wiki files not present in source.

## Automated Sync in CI

A workflow can publish from `main`:

- Trigger on pushes affecting wiki sources.
- Run a dry-run smoke test first.
- If dry-run passes, run `scripts/sync_wiki.py --push`.
- Use `GITHUB_TOKEN` with `contents: write`.

## Script Options

```bash
python scripts/sync_wiki.py --help
```

Most useful flags:

- `--repo owner/repo`
- `--source-root docs/wiki`
- `--wiki-dir /tmp/iiif-wiki-sync`
- `--dry-run`
- `--push`
- `--no-prune`
