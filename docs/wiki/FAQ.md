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

## Which PDF source is used?

- Native PDF is preferred when the manifest exposes one and `settings.pdf.prefer_native_pdf=true`.
- Otherwise the workflow falls back to image-based download.
- Image-based PDF generation depends on `settings.pdf.create_pdf_from_images`.

## Can I export higher quality without keeping everything high resolution locally?

Yes. Use a PDF profile that fetches temporary remote high-resolution images for the export job.

## Why do some providers feel slower than others?

Per-library rate limiting and backoff settings can be stricter for fragile upstream services. Review `settings.network.global.*` and `settings.network.libraries.<library>.*`.

## Wiki sync ran, but the wiki did not update

Run a dry-run first:

```bash
python scripts/sync_wiki.py --repo owner/repo --dry-run
```

Then publish:

```bash
python scripts/sync_wiki.py --repo owner/repo --push
```

Also confirm that the repository wiki is enabled and that the workflow token has `contents: write`.

## Where should I edit wiki pages?

Always edit source pages in `docs/wiki/` inside the main repository. The GitHub Wiki is a publish target, not the source of truth.

## Read Next

- [Studio Workflow](Studio-Workflow.md)
- [Configuration](Configuration.md)
- [Documentation Hub](../index.md)
