# Changelog

All notable changes to this project are documented in this file.

## Changelog Format Policy

- Every release section must use this heading format: `## [vX.Y.Z] - YYYY-MM-DD`.
- Every release must include all three sections:
  - `### Added`
  - `### Changed`
  - `### Fixed`
- Every non-empty bullet should reference an issue or PR number using the `(#123)` suffix.
- If a section has no items, use `- None.`

## [v0.6.1] - 2026-03-02

### Added

- Added global, non-mutating `config.json` validation with severity-based diagnostics (`WARNING`/`ERROR`) during `ConfigManager.load()` (#73).
- Added dedicated tests for config schema/deprecation validation and load-time logging behavior (#73).

### Changed

- Deprecated thumbnail keys are now explicitly reported as runtime warnings instead of being silently ignored (#73).
- Validation logs avoid leaking sensitive config values such as API keys and tokens (#73).

### Fixed

- Improved startup diagnostics for malformed configuration roots and invalid JSON payloads (`ERROR` severity where appropriate) (#73).

## [v0.6.0] - 2026-01-23

### Added

- Snippet SQLite feature set (#6).

### Changed

- None.

### Fixed

- Moved runtime data from `var/` to `data/local/` and served snippets from `/assets/snippets/` (chore/docs) (#15).

## [v0.5.0] - 2026-01-19

### Added

- **Rich Text Editor**: Replaced the legacy plain text editor with an advanced RTE based on a dedicated Quill wrapper (#4).
  - Text formatting support (bold, italic, underline).
  - Bullet and numbered lists.
  - Superscript and subscript.
  - Hybrid save mode (HTML for rendering, plain text for indexing).
- **History Restoration**: Improved history restore logic to correctly handle RTE content (#4).

### Changed

- **Logging**: Refactored logging to use centralized setup (`get_logger`) instead of scattered direct calls, improving debuggability and consistency (#4).
- **Config**: Improved dependency/import handling to reduce circular import conflicts (#4).

### Fixed

- Resolved critical merge conflicts during integration of branch `add-rich-text` (#4).
- Fixed minor issues in legacy UI session-state handling during save operations (#4).

## [v0.4.0] - 2026-01-19

### Added

- **Local PDF Import**: Added local PDF import into `downloads/Local` with automatic page image extraction (#3).
- **Studio UI Remaster**: Introduced a redesigned Studio page with collapsible sidebar and improved navigation (#3).
- **Global Search**: Added a page to search text across all saved transcriptions (#3).

### Changed

- Improved UI notification handling (#3).
- Improved performance for high-resolution image loading (#3).

### Fixed

- None.
