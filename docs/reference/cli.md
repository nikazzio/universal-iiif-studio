# CLI Reference

The CLI lives in `src/universal_iiif_cli/cli.py` and exposes both direct download flows and local database utilities.

## Basic Usage

```bash
scriptoria-cli "<manifest-or-provider-url>"
```

If no URL is provided, the CLI enters an interactive wizard.

## Main Options

### Download Options

- `-o, --output`
  - Output PDF filename.
- `-w, --workers`
  - Concurrent downloads for the current run.
- `--clean-cache`
  - Clean cache before running.
- `--prefer-images`
  - Force image download even if a native PDF exists.
- `--ocr`
  - Run OCR after download using the provided model name.
- `--create-pdf`
  - Explicitly build a PDF from downloaded images.

### Database And Local State

- `--list`
  - List local manuscripts in the database.
- `--info ID`
  - Show detailed info for a manuscript.
- `--delete ID`
  - Delete a manuscript record.
- `--delete-job JOB_ID`
  - Delete a download job record.
- `--set-status ID STATUS`
  - Force update the stored status.

## Operational Notes

- Resolution and provider classification use the same core registry used by the web UI.
- Local state is backed by `VaultManager`.
- The CLI is useful for direct download workflows and for inspecting local runtime state without opening the web app.

## Examples

```bash
scriptoria-cli "https://digi.vatlib.it/iiif/MSS_Urb.lat.1779/manifest.json"
scriptoria-cli --list
scriptoria-cli --info MSS_Urb.lat.1779
```
