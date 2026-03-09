# Studio Workflow

## Recommended Entry

Open a local document from `Library` using "Apri Studio".
Direct `/studio` without `doc_id` and `library` opens the recent hub (`Riprendi lavoro`).

## Mirador Viewing Modes

Studio supports **two viewing modes** for the Mirador viewer:

### Remote Mode (Incomplete Downloads)
- **When**: Download is incomplete or paused; not all pages available locally.
- **Behavior**: Mirador loads the original manifest from the library server (e.g., `gallica.bnf.fr`).
- **Pages shown**: ALL pages (complete manuscript), fetched on-demand from remote server.
- **Use case**: Preview the full manuscript while download is in progress or paused.
- **Internet**: Required.
- **Manual override**: Add `?allow_remote_preview=true` to Studio URL.

### Local Mode (Complete Downloads)
- **When**: All pages downloaded and available in `scans/` directory.
- **Behavior**: Mirador loads local manifest (`/iiif/manifest/...`) served by Studio.
- **Pages shown**: Only downloaded pages using local images.
- **Use case**: Offline work, transcription, analysis with complete local dataset.
- **Internet**: Not required (works completely offline).
- **Config**: Controlled by `viewer.mirador.require_complete_local_images` (default: `true`).

**Status indicator**: The status panel shows a color-coded READ_SOURCE badge:
- **AMBER**: Remote mode (fetching from original server)
- **GREEN**: Local mode (using downloaded images)

## Download Manager and Staging

- Download cards show queue/running/pausing/paused/cancelling/cancelled states with page counters.
- Local staging uses `temp_images/<doc_id>` before files are consolidated in `downloads/<library>/<doc_id>/scans/`.
- With `settings.storage.partial_promotion_mode=on_pause`, pausing a running download promotes validated staged pages into `scans/`; existing scans are overwritten only in explicit refresh/redownload flows.
- Resume evaluates both `scans/` and staged temp files, then continues only from truly missing pages.

## Output Tab Model

- Top section: existing PDF inventory for the selected document.
- Sub-tabs:
  - `Crea PDF`: profile selection and optional per-job overrides.
  - `Pagine`: thumbnail gallery with per-page actions:
    - `High-Res`: fetch high-resolution version of individual pages from remote source.
    - **Ottimizza scans locali**: in-place lossy optimization of local scan images to reduce storage footprint (configurable via `settings.images.local_optimize.max_long_edge_px` and `settings.images.local_optimize.jpeg_quality`).
      - **Security**: Optimization validates all file paths to prevent symlink-based path traversal attacks. Only files within the downloads directory are processed.
  - `Job`: export queue and progress.
- Source mode is explicit per job:
  - `PDF da Locale (bilanciato/high-res)`
  - `PDF da Remoto temporaneo`

## Profile-First Behavior

- Main control is `Profilo PDF`.
- `Gestisci profili` links to `Settings > PDF Export`.
- Overrides are collapsed by default and should be opened only for exceptions.

## Thumbnail Decisions

- Each thumbnail shows local resolution (`Locale`) and probed remote max resolution (`Online max`).
- `High-Res` allows targeted page fetch without forcing full-document high-res download.
- Scope controls let you export `Tutte le pagine` or `Solo selezione`.

## Info Tab

Info is organized in sub-tabs:

- `Panoramica`
- `Pagina corrente`
- `Metadati e fonti`

External resources are shown as explicit outbound actions (`Apri ...`) to avoid long raw URLs in the layout.
