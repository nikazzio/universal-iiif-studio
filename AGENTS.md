# Agent Playbook

This file is procedural only. For architectural rationale, see `docs/ARCHITECTURE.md`.

## Scope

- Project: Universal IIIF Downloader & Studio
- Supported front ends: FastHTML/HTMX UI and CLI
- Package layout: `src/`

## Mandatory Structure Rules

- Keep all Python source code under `src/`.
- Do not add Python source files in repository root.
- Keep CLI entrypoint in `src/universal_iiif_cli/cli.py`.
- Keep web entrypoint in `src/studio_app.py`.

## Dependency and Config Rules

- Add dependencies only in `pyproject.toml` under `[project.dependencies]`.
- Install locally with `pip install -e .`.
- Keep Pyright configuration only in `pyrightconfig.json`.
- Use `universal_iiif_core.config_manager` for runtime config and path resolution.
- Do not hardcode runtime paths.

## Code Quality Rules

- Use Ruff as the only linter/formatter.
- Enforce C901 max complexity 10.
- Use `pathlib.Path` for path operations.

## Runtime Data Rules

- Treat these directories as user/runtime data and keep them in `.gitignore`:
  - `downloads/`
  - `data/local/`
  - `logs/`
  - `temp_images/`

## Build, Run, Test Commands

- Install: `pip install -e .`
- Run web UI: `iiif-studio` (or `python3 src/studio_app.py`)
- Run CLI: `iiif-cli "<manifest-url>"`
- Run tests: `pytest tests/`
- Lint/fix: `ruff check . --fix`
- Complexity check: `ruff check . --select C901`
- Format: `ruff format .`

## User-Data Cleanup Workflow

- Dry-run cleanup first:
  - `python scripts/clean_user_data.py --dry-run`
- Confirm cleanup:
  - `python scripts/clean_user_data.py --yes`
- Include full `data/local` reset only when required:
  - add `--include-data-local`

Pre-PR sequence:
1. Update `.gitignore` for any new runtime directories.
2. Register runtime paths through `ConfigManager` only.
3. Run cleanup dry-run.
4. Run cleanup confirm.
5. Run `pytest tests/`.
6. Run `ruff check . --select C901`.
7. Run `ruff format .`.

## Git and PR Rules

- Never commit directly to `main`.
- Create branches with prefixes: `feat/`, `fix/`, `docs/`, `chore/`.
- Use conventional commit prefixes: `feat:`, `fix:`, `docs:`, `chore:`.
- Use GitHub CLI for remote operations.
- Open PRs with:
  - `gh pr create --fill`
- Check PR status before finalizing:
  - `gh pr status`

## Release Rules

- Keep commit messages descriptive for semantic release.
- Keep canonical version in `src/universal_iiif_core/__init__.py`.
