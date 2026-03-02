# Agent Playbook

This file is procedural only. For architectural rationale, see `docs/ARCHITECTURE.md`.

## Scope

- Project: Universal IIIF Downloader & Studio
- Supported front ends: FastHTML/HTMX UI and CLI
- Package layout: `src/`

## Execution Principles (Pragmatic)

- Plan before execute for complex features, refactors, and cross-module changes.
- Prefer test-first for bug fixes and new behavior that can be specified upfront.
- Keep security checks mandatory on API/routes, file handling, and export/download flows.
- Prefer immutability when practical, but do not force it at the cost of readability in Python code.
- Optimize for simple, reliable flows over speculative abstractions.

## Agent Orchestration (Codex)

- Use `explorer` for planning, architecture checks, and focused codebase analysis.
- Use `worker` for implementation tasks that touch multiple files or require isolated ownership.
- Use `awaiter` for long-running operations (test suites, prolonged commands, monitoring).
- Run agents in parallel only for independent tasks; keep one source of truth for merge decisions.

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

## Security Baseline

- Never hardcode secrets or tokens in source code.
- Validate input at system boundaries (routes, CLI args, external payloads).
- Enforce path safety for file read/write/download/delete operations.
- Use parameterized access patterns for DB operations (no string-built queries).
- Do not leak sensitive details in user-facing error messages.
- Keep permissive CORS only for explicit local/dev scenarios; prefer explicit origins otherwise.

## Runtime Data Rules

- Treat these directories as user/runtime data and keep them in `.gitignore`:
  - `downloads/`
  - `data/local/`
  - `logs/`
  - `temp_images/`

## Build, Run, Test Commands

- Always use project tools from `.venv/bin/` when available (do not assume global executables).
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

## Verification Loop (Before PR)

Run a compact verification loop for every non-trivial change:
1. Build/start sanity check for touched surface (`iiif-studio` or relevant CLI path).
2. Tests: targeted tests first, then `pytest tests/`.
3. Lint/complexity/format: Ruff checks.
4. Security spot-check: traversal/path safety, input validation, and secrets.
5. Review `git diff` for unintended changes.

Coverage note:
- Current repo does not enforce a global coverage gate in CI.
- When coverage tooling is available, target at least 80% on touched critical paths.

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

## Preferred Skills For This Project

Use these skills when available in the active CLI skill path.
These are the default skills for this repository:

- `architecture`
- `architecture-decision-records`
- `api-patterns`
- `async-python-patterns`
- `python-patterns`
- `python-performance-optimization`
- `performance-profiling`
- `python-testing-patterns`
- `test-driven-development`
- `systematic-debugging`
- `webapp-testing`
- `search-specialist`
- `pdf-official`
- `docs-architect`
- `code-refactoring-refactor-clean`
- `search-first`
- `verification-loop`
- `security-review`
- `iterative-retrieval`
- `content-hash-cache-pattern`
- `tdd-workflow`

### Skill Trigger Guidance

- Use `architecture` and `architecture-decision-records` for design decisions and major refactors.
- Use `api-patterns` when changing API contracts, endpoints, payloads, or error models.
- Use `async-python-patterns` and `python-patterns` for concurrency and Python structure choices.
- Use `python-performance-optimization` and `performance-profiling` for slow paths and bottlenecks.
- Use `python-testing-patterns`, `test-driven-development`, and `webapp-testing` for implementation and validation.
- Use `systematic-debugging` for any bug, regression, or failing test before proposing fixes.
- Use `search-specialist` for discovery/research tasks requiring strong source vetting.
- Use `pdf-official` for PDF export/manipulation workflows.
- Use `docs-architect` for technical documentation updates and flow documentation.
- Use `code-refactoring-refactor-clean` for non-trivial code cleanup and maintainability work.
- Use `search-first` before introducing new dependencies or building new utilities.
- Use `verification-loop` before PR creation or after substantial refactors.
- Use `security-review` for auth/input/file-handling/export-sensitive changes.
- Use `iterative-retrieval` for multi-step discovery/refactor tasks with uncertain context.
- Use `content-hash-cache-pattern` when adding cache for expensive file/image/PDF processing.
- Use `tdd-workflow` for new features and bug fixes that require strict red-green-refactor flow.
