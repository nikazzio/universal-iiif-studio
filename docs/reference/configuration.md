# Configuration Overview

Scriptoria uses `config.json` as the runtime control surface for network behavior, image acquisition, export policy, local storage, viewer defaults, and testing. If you are operating the application seriously, configuration is part of the product, not an afterthought.

This page is the readable map. It explains what each configuration family is for, when you would touch it, and what parts of the application it changes. For the full key-by-key specification, use [Detailed Configuration Reference](../CONFIG_REFERENCE.md).

## How Configuration Works

At startup, `ConfigManager` loads the default configuration, merges user configuration, normalizes a small set of legacy keys, and runs a validation pass. Validation is intentionally non-destructive: Scriptoria reports structural or semantic problems but does not silently rewrite your file. That matters because the configuration is operational state, not just preferences.

In practice, configuration affects:

- how aggressively Scriptoria talks to upstream libraries;
- how it downloads or stitches images;
- when Studio prefers local or remote reading;
- what defaults the export form applies;
- how local derivative caches are retained or pruned;
- which UI and testing behaviors are enabled.

## Where To Edit It

There are two legitimate ways to work with configuration:

- use the Settings UI for normal operational adjustments;
- edit `config.json` directly when you need full control or reproducible deployment-style configuration.

The Settings UI maps onto the same configuration tree. It does not invent a separate preference model. Some areas are split across panes for usability reasons: for example, `settings.pdf.*` is written partly from `Processing Core` and partly from `PDF Export`, but the runtime still sees one coherent `pdf` subtree.

## Top-Level Structure

The runtime file is organized around four top-level sections:

- `paths`
- `security`
- `api_keys`
- `settings`

The `settings` subtree is where most of the operational logic lives.

## Paths

The `paths.*` keys define the local runtime directories used by Scriptoria.

These paths cover:

- downloads and local manuscript workspaces;
- export output;
- temporary image staging;
- model caches;
- logs;
- snippets and other local working artifacts.

This section matters when you want to relocate runtime data, keep large image volumes off the repository path, or integrate Scriptoria into a stricter local filesystem layout.

## Security

The `security.*` section is intentionally small. Its main job is to constrain origin handling and other boundary-sensitive runtime behavior.

In the current product, the most visible key is `security.allowed_origins`, which matters if you are exposing the local UI in a less permissive environment than the default local workstation scenario.

## API Keys

The `api_keys.*` section stores credentials for OCR or external AI-related integrations.

These values are optional until you enable the corresponding features, but they are still part of the active configuration surface because live tests and some OCR paths depend on them.

## Settings Families

The rest of the configuration lives under `settings.*`. The sections below explain the high-impact families in practical terms.

### `settings.network.*`

This family controls transport behavior, retry policy, pacing, and per-library override policy.

It is split into three layers:

- `settings.network.global.*` for application-wide transport limits;
- `settings.network.download.*` for default document download behavior;
- `settings.network.libraries.<provider>.*` for provider-specific overrides.

You touch this family when:

- a provider rate-limits too aggressively;
- downloads need to be slower or more parallel;
- one library needs stricter policy than the global default;
- you want reproducible network behavior across machines.

This family is directly reflected in the Settings `Network` pane.

### `settings.images.*`

This family controls how Scriptoria acquires and manipulates page images.

It includes:

- direct-download strategy presets;
- custom download attempt sequences;
- fallback mode between direct fetch and tile stitching;
- IIIF quality segment behavior;
- RAM limits for large stitch jobs;
- local optimization parameters.

This section is operationally important because it affects both initial page acquisition and later page repair actions from Studio Output. It also determines the direct-attempt order that the downloader derives at runtime from the selected strategy preset.

### `settings.thumbnails.*`

This family governs the derivative images used in the Output page grid.

It controls:

- the number of thumbnails shown per slice;
- available page-size selector values;
- thumbnail max edge;
- thumbnail JPEG quality.

These are not only UI cosmetics. Thumbnail behavior influences the inspection surface used before export and during page-level repair work.

### `settings.viewer.*`

This family controls Studio reading behavior and image presentation.

The most important concerns here are:

- when Studio requires complete local images before switching fully local;
- whether saved-but-incomplete items open remote-first or local-first;
- OpenSeadragon zoom limits inside Mirador;
- visual filter defaults and presets.

If users are confused about why Studio opens remotely, why local mode is blocked, or why the viewer feels too constrained or too aggressive in zoom, this is the family to inspect.

### `settings.pdf.*`

This family controls PDF behavior at multiple levels.

It includes native-PDF preference, PDF rasterization defaults, export defaults, cover metadata, and the profile catalog used by Studio Output.

This is one of the most important parts of the configuration tree because export in Scriptoria is profile-driven. The product does not treat PDF generation as a single-button side effect. It also means you need to keep apart three layers that often get confused:

- processing defaults used when Scriptoria ingests a native upstream PDF;
- export defaults applied to a new Output form;
- named PDF profiles that bundle image source mode, compression, cover policy, and remote-fetch behavior.

### `settings.storage.*`

This family defines retention, pruning, staging, and cache constraints.

It affects:

- export retention;
- thumbnail retention;
- temporary high-resolution export staging retention;
- persistent remote-resolution cache limits;
- startup pruning;
- staged-page promotion behavior.

This section is what lets Scriptoria behave like a controlled local workspace instead of an ever-growing pile of temporary files.

### `settings.ui.*`

This family covers presentation and polling defaults used by the web UI.

Examples include:

- theme settings;
- item pagination;
- toast duration;
- polling intervals for active download surfaces.

These values do not usually change the core acquisition pipeline, but they can strongly affect perceived responsiveness and usability. Theme migration is also handled here: old `theme_color` values are mapped to the current accent-color key at load time.

### `settings.discovery.*`

This section controls discovery-specific behavior, especially the size and shape of provider result lists.

If discovery feels too sparse or too noisy, this is the first place to look.

### `settings.ocr.*`

This family selects OCR engine behavior and toggles OCR-related runtime options.

It matters both for production use and for test environments where external services may be unavailable or intentionally disabled. The current UI exposes the most common engines, while the runtime and validator also accept `huggingface` for direct configuration.

### `settings.housekeeping.*`, `settings.logging.*`, `settings.testing.*`

These sections cover the operational envelope around the app:

- cleanup windows for temporary material;
- log verbosity;
- whether live-network tests are allowed to run.

They are especially relevant for development environments, CI, and long-lived local workstations.

## Recommended Reading Path

If you need a stable way to approach configuration:

1. Read this page to understand the families.
2. Open [Detailed Configuration Reference](../CONFIG_REFERENCE.md) for exact keys.
3. Read [Runtime Paths](runtime-paths.md) to understand where local data really lives.
4. Read [Provider Support](provider-support.md) if the configuration change is driven by a specific library.

## What Usually Needs Tuning First

In practice, the first settings most teams or users tune are network concurrency and retry behavior, image download strategy, local optimization quality, thumbnail page size, viewer source policy, PDF profile defaults, and storage retention windows.

Those settings change the day-to-day operating feel of the product far more than purely cosmetic options.

## Related Docs

- [Detailed Configuration Reference](../CONFIG_REFERENCE.md)
- [Runtime Paths](runtime-paths.md)
- [Provider Support](provider-support.md)
- [Export And PDF Model](../explanation/export-and-pdf-model.md)
- [Storage Model](../explanation/storage-model.md)
