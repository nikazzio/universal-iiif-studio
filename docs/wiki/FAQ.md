# FAQ

## Should I keep all pages in high resolution locally?

Not necessarily. A balanced local set is usually enough for normal study and annotation.
Use targeted high-res fetch only on pages that need it.

## Can I generate very high quality PDFs without storing everything high-res?

Yes. Use a profile with `image_source_mode=remote_highres_temp`.
The exporter can fetch high-res pages for that job and clean temporary files afterwards.

## Where should I edit wiki pages?

Edit source files in `docs/wiki/` in the main repository, then sync to GitHub Wiki with:

```bash
python scripts/sync_wiki.py --repo owner/repo --push
```

## Why use repository docs plus wiki sync?

Repository docs support PR review, CI checks, and versioned changes.
Wiki remains easy to browse while staying aligned with reviewed content.
