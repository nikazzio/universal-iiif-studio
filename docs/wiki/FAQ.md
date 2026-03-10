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
- check staging under `data/local/temp_images/<doc_id>/`,
- verify scans are present before opening Studio,
- retry extraction/download for missing pages.

If pages are staged but not promoted yet, review:
- `settings.storage.partial_promotion_mode` (`never|on_pause`)
- `settings.viewer.mirador.require_complete_local_images`

More details: [ARCHITECTURE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/ARCHITECTURE.md)

## 6) Pause works, but why are some pages still in temp?

**Behavior**:
- with `partial_promotion_mode=never`, validated pages can remain in staging until completeness gate is satisfied;
- with `partial_promotion_mode=on_pause`, pausing promotes validated staged pages to `scans/`; existing scans are overwritten only in explicit refresh/redownload flows.

Segmented retries (`retry_missing` / `retry_range`) still converge correctly because completeness checks count previously staged validated pages.

## 7) Native PDF vs generated PDF: which one is used?

**Behavior**:
- if the manifest exposes a native PDF and `settings.pdf.prefer_native_pdf=true`, native flow is preferred;
- otherwise images are used, and PDF generation depends on `settings.pdf.create_pdf_from_images`.

More details: [CONFIG_REFERENCE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/CONFIG_REFERENCE.md)

## 8) Can I export very high quality PDF without keeping everything high-res locally?

Yes. Use an export profile with `image_source_mode=remote_highres_temp`.
High-res pages are fetched for that job and cleaned after export when enabled.

More details: [PDF-Export-Profiles](PDF-Export-Profiles.md)

## 9) Wiki sync ran, but wiki was not updated

**Probable cause**: push not enabled, wiki disabled, or missing permissions.  
**Quick fix**:
- run dry-run first to verify delta:

```bash
python scripts/sync_wiki.py --repo owner/repo --dry-run
```

- then publish with `--push`,
- ensure CI has `contents: write` and wiki is enabled.

More details: [WIKI_MAINTENANCE.md](../WIKI_MAINTENANCE.md)

## 10) Where should I edit wiki pages?

Always edit source pages in `docs/wiki/` inside the main repository.  
The GitHub wiki is a publish target, not the source of truth.

More details: [WIKI_MAINTENANCE.md](../WIKI_MAINTENANCE.md)

## 11) Where is the complete configuration reference?

Use the canonical docs:
- full keys: [CONFIG_REFERENCE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/CONFIG_REFERENCE.md)
- user flow: [DOCUMENTAZIONE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/DOCUMENTAZIONE.md)
- architecture: [ARCHITECTURE.md](https://github.com/nikazzio/universal-iiif-studio/blob/main/docs/ARCHITECTURE.md)

## 12) Why does Studio show remote images instead of local ones?

**Probable cause**: Download is incomplete or `viewer.mirador.require_complete_local_images=true` (default).  
**Behavior**: Studio automatically uses **Remote Mode** when local pages are not fully available. Mirador loads the original manifest and fetches images on-demand from the library server.  
**Quick fix**:
- Complete the download to automatically switch to Local Mode.
- Or add `?allow_remote_preview=true` to Studio URL to explicitly enable Remote Mode.
- Or set `viewer.mirador.require_complete_local_images=false` in config to prefer remote preview by default.

**Status indicator**: Check the READ_SOURCE badge in the status panel:
- **AMBER badge**: Remote mode (fetching from original server)
- **GREEN badge**: Local mode (using downloaded images)

More details: [Studio-Workflow.md](Studio-Workflow.md)

## 13) How do I preview a manuscript while it's still downloading?

**Solution**: Use Remote Mode by adding `?allow_remote_preview=true` to the Studio URL.  
**Behavior**: Mirador will load the original manifest from the library server and display ALL pages, fetching images on-demand as you navigate.  
**Limitation**: Requires internet connection; images are not cached locally in this mode.

More details: [Studio-Workflow.md](Studio-Workflow.md)

## 14) Why do downloads to Gallica seem slower than other libraries?

**Expected behavior**: Gallica has stricter rate limits configured in the HTTP client.  
**Rate limits**:
- Gallica: 4 requests per minute (burst window)
- Other libraries: 20 requests per minute (default)

**Rationale**: Gallica servers use aggressive WAF (Web Application Firewall) and rate limiting. The system automatically applies conservative limits to avoid IP blocks.

**Config location**: `settings.network.libraries.gallica.*` in `config.json`.

More details: [HTTP_CLIENT.md](../HTTP_CLIENT.md)
