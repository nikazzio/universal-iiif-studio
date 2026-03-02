# PDF Export Profiles

Profiles are global presets defined in `Settings > PDF Export` and selected per job in `Studio > Export`.

## Built-in Profiles

- `balanced`
- `high_quality`
- `archival_highres`
- `lightweight`

## Main Profile Fields

- `compression`
- `include_cover`
- `include_colophon`
- `image_source_mode`
- `image_max_long_edge_px`
- `jpeg_quality`
- `force_remote_refetch`
- `cleanup_temp_after_export`
- `max_parallel_page_fetch`

## Source Modes

- `local_balanced`: use local scans in balanced mode.
- `local_highres`: use local scans at higher detail.
- `remote_highres_temp`: fetch remote high-resolution pages for the current job only.

## Practical Strategy

- Keep local workflow balanced for speed and storage.
- Use thumbnail `Online max` vs `Locale` metadata to decide if extra detail is needed.
- Use `remote_highres_temp` only for pages/jobs that require maximum quality.
- Keep `cleanup_temp_after_export` enabled to avoid temp high-res accumulation.
