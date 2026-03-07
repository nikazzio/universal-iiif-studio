# Studio Workflow

## Recommended Entry

Open a local document from `Library` using "Apri Studio".
Direct `/studio` without `doc_id` and `library` opens the recent hub (`Riprendi lavoro`).

## Download Manager and Staging

- Download cards show queue/running/pausing/paused/cancelling/cancelled states with page counters.
- Local staging uses `temp_images/<doc_id>` before files are consolidated in `downloads/<library>/<doc_id>/scans/`.
- With `settings.storage.partial_promotion_mode=on_pause`, pausing a running download promotes validated staged pages into `scans/`; existing scans are overwritten only in explicit refresh/redownload flows.
- Resume evaluates both `scans/` and staged temp files, then continues only from truly missing pages.

## Output Tab Model

- Top section: existing PDF inventory for the selected document.
- Sub-tabs:
  - `Crea PDF`: profile selection and optional per-job overrides.
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
