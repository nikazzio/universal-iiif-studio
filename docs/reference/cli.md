# CLI Reference

The CLI lives in `src/universal_iiif_cli/cli.py` and is exposed by the `scriptoria-cli` entry point. It shares the same provider registry, resolver layer, and local vault used by the web application, so anything resolved or stored from the CLI shows up in the same Library that Studio reads.

The CLI exists for two situations: direct acquisition when you already know the manuscript you want, and quick inspection or repair of local state without opening the web app.

## Basic Usage

```bash
scriptoria-cli "<manifest-or-provider-url>"
```

If the input is a known provider URL, shelfmark, or supported identifier, it is normalized to a manifest URL through the same resolver chain used by Discovery. If the input cannot be classified and is not an HTTP URL, the CLI exits with an error and points you toward pasting a direct `manifest.json` link.

If you call `scriptoria-cli` with no positional argument, it enters an interactive wizard.

## Wizard Mode

Wizard mode is intentionally minimal. It asks for a manuscript or viewer URL, an optional output filename, and an optional OCR model name. It is meant for one-off downloads where you do not want to remember flag names. Anything more advanced should use explicit flags.

```text
🌍  UNIVERSAL IIIF DOWNLOADER  🌍

Paste the URL (Manifest or Viewer link): ...
Output filename (optional, press Enter for auto): ...
OCR Model (optional, e.g. 'kraken', press Enter to skip): ...
```

## Download Options

These flags control the acquisition run started by a positional URL or by the wizard.

- `-o, --output`
  - Output PDF filename. Without this flag, Scriptoria picks a name from the manuscript identifier.
- `-w, --workers`
  - Concurrent downloads for the current run. Default `4`. Increase only if both your network and the upstream provider can absorb it without rate-limiting penalties.
- `--clean-cache`
  - Clear cached working state before running. Use when a previous attempt left inconsistent staged data and you want a fresh acquisition.
- `--prefer-images`
  - Force per-page image download even if the provider exposes a native PDF. The default is to use a native PDF when one is advertised, because that path is usually faster and produces a more faithful artifact.
- `--ocr MODEL`
  - Run OCR after download using the given Kraken model filename. Only meaningful when the model is reachable from the configured local model directory.
- `--create-pdf`
  - Explicitly build a PDF from the downloaded images at the end of the run. Use this when the provider has no native PDF and you still want a final PDF artifact.

## Database And Local State

These flags do not start a download. They read or modify the local vault directly through `VaultManager`.

- `--list`
  - List local manuscripts in the database. The output shows manuscript id, status, page progress, and provider library, with a status icon: ✅ complete, ⏳ downloading, ❌ error, ⚪ other.
- `--info ID`
  - Show stored fields for one manuscript (provider identity, status, paths, progress, manifest URL, and related metadata).
- `--delete ID`
  - Delete a manuscript record from the vault. This removes the local catalog entry; runtime files on disk are handled by separate cleanup flows.
- `--delete-job JOB_ID`
  - Remove a single download job row from the internal `download_jobs` table. Mostly useful during development or when stray records survive a crash.
- `--set-status ID STATUS`
  - Force the stored status for a manuscript. Standard values are `pending`, `downloading`, `complete`, and `error`. Other strings are accepted with a warning, but the rest of the system reasons in terms of the standard set.

## Other Options

- `--version`
  - Print the installed Scriptoria version and exit.

## Where Files End Up

The CLI does not invent paths. Output and runtime locations come from `ConfigManager` exactly as in the web application:

- downloaded scans go under the configured downloads directory;
- temporary working files go under the temp directory;
- logs go under the configured log directory.

If you need to change those locations, edit `config.json` rather than passing path overrides on the command line. See [Runtime Paths](runtime-paths.md) and [Configuration Overview](configuration.md).

## Operational Notes

- Resolution and provider classification use the same registry as the web UI. If a URL resolves in the CLI, it will resolve the same way in Discovery.
- Local state is shared with Studio. A manuscript downloaded from the CLI is immediately visible in Library and openable in Studio without further import.
- The CLI is the right surface for shell pipelines, scripted batch acquisition, headless environments, and local-state inspection.
- The legacy entry points `iiif-cli` and `iiif-studio` are still installed as aliases for `scriptoria-cli` and `scriptoria` to avoid breaking older scripts. New work should use the `scriptoria` names.

## Examples

Download a manuscript by direct manifest URL:

```bash
scriptoria-cli "https://digi.vatlib.it/iiif/MSS_Urb.lat.1779/manifest.json"
```

Force image-based download and build the PDF explicitly, with eight workers:

```bash
scriptoria-cli "https://gallica.bnf.fr/ark:/12148/btv1b8470209j" \
  --prefer-images --create-pdf --workers 8
```

Inspect and repair local state without launching the web app:

```bash
scriptoria-cli --list
scriptoria-cli --info MSS_Urb.lat.1779
scriptoria-cli --set-status MSS_Urb.lat.1779 complete
```

## Related Docs

- [Getting Started](../intro/getting-started.md)
- [Configuration Overview](configuration.md)
- [Runtime Paths](runtime-paths.md)
- [Provider Support](provider-support.md)
