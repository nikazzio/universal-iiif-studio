# FAQ

## `scriptoria: command not found`

Activate the virtual environment and reinstall in editable mode:

```bash
source .venv/bin/activate
pip install -e .
scriptoria
```

## Studio opens without a document

This is expected. Opening `/studio` without `doc_id` and `library` shows the recent-work hub.

## Studio shows remote images instead of local images

This is expected when local page availability is incomplete and local-only gating is enabled.

Review:

- `settings.viewer.mirador.require_complete_local_images`
- the `allow_remote_preview=1` query override
- current local page availability in the item workspace

## Why are pages still in staging?

`settings.storage.partial_promotion_mode` controls when validated staged pages are promoted into local scans.

- `never` keeps them staged until completeness gates are satisfied.
- `on_pause` promotes validated staged pages when a running job is paused.

## Why do some providers feel slower than others?

Per-library rate limiting and backoff settings can be stricter for fragile upstream services. Review `settings.network.global.*` and `settings.network.libraries.<library>.*`.

## Wiki sync ran, but the wiki did not update

Run a dry-run first:

```bash
python3 scripts/sync_wiki.py --repo owner/repo --dry-run
```

Then publish:

```bash
python3 scripts/sync_wiki.py --repo owner/repo --push
```

Also confirm that the repository wiki is enabled and that the workflow token has `contents: write`.

## Read Next

- [Troubleshooting](Troubleshooting.md)
- [Docs Home](../index.md)
