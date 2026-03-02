# Studio Workflow

## Recommended Entry

Open a local document from `Library` using "Apri Studio".
Direct `/studio` without `doc_id` and `library` redirects to `Library`.

## Export Tab Model

- Top section: existing PDF inventory for the selected document.
- Sub-tabs:
  - `Crea PDF`: profile selection and optional per-job overrides.
  - `Job`: export queue and progress.

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
