# FAQ

## 1) `iiif-studio: command not found`

**Probable cause**: the virtual environment is not active or the project is not installed in editable mode.  
**Quick fix**:

```bash
source .venv/bin/activate
pip install -e .
iiif-studio
```

More details: [README.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/README.md)

## 2) Port `8000` is already in use

**Probable cause**: another process is already bound to the web port.  
**Quick fix**: stop the conflicting process, then rerun `iiif-studio`.

More details: [README troubleshooting](https://github.com/nikazzio/universal-iiif-studio/blob/main/README.md)

## 3) Manifest cannot be resolved

**Probable cause**: wrong URL, temporary provider outage, or access restrictions.  
**Quick fix**:
- verify the manifest URL in the browser first,
- retry after a few minutes,
- switch provider if available.

More details: [DOCUMENTAZIONE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/DOCUMENTAZIONE.md)

## 4) Download stops midway

**Probable cause**: network timeout or remote rate limiting.  
**Quick fix**:
- retry after a short wait,
- reduce concurrency if your network is unstable,
- avoid starting multiple heavy jobs at once.

More details: [CONFIG_REFERENCE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/CONFIG_REFERENCE.md)

## 5) Studio opens but pages are missing

**Probable cause**: scans were not extracted/downloaded as expected.  
**Quick fix**:
- check the document folder under `downloads/...`,
- verify scans are present before opening Studio,
- retry extraction/download for missing pages.

More details: [ARCHITECTURE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/ARCHITECTURE.md)

## 6) Native PDF vs generated PDF: which one is used?

**Behavior**:
- if the manifest exposes a native PDF and `settings.pdf.prefer_native_pdf=true`, native flow is preferred;
- otherwise images are used, and PDF generation depends on `settings.pdf.create_pdf_from_images`.

More details: [CONFIG_REFERENCE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/CONFIG_REFERENCE.md)

## 7) Can I export very high quality PDF without keeping everything high-res locally?

Yes. Use an export profile with `image_source_mode=remote_highres_temp`.
High-res pages are fetched for that job and cleaned after export when enabled.

More details: [PDF-Export-Profiles](PDF-Export-Profiles.md)

## 8) Wiki sync ran, but wiki was not updated

**Probable cause**: push not enabled, wiki disabled, or missing permissions.  
**Quick fix**:
- run dry-run first to verify delta:

```bash
python scripts/sync_wiki.py --repo owner/repo --dry-run
```

- then publish with `--push`,
- ensure CI has `contents: write` and wiki is enabled.

More details: [WIKI_MAINTENANCE.md](../WIKI_MAINTENANCE.md)

## 9) Where should I edit wiki pages?

Always edit source pages in `docs/wiki/` inside the main repository.  
The GitHub wiki is a publish target, not the source of truth.

More details: [WIKI_MAINTENANCE.md](../WIKI_MAINTENANCE.md)

## 10) Where is the complete configuration reference?

Use the canonical docs:
- full keys: [CONFIG_REFERENCE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/CONFIG_REFERENCE.md)
- user flow: [DOCUMENTAZIONE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/DOCUMENTAZIONE.md)
- architecture: [ARCHITECTURE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/ARCHITECTURE.md)
