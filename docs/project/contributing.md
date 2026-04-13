# Contributing

This page summarizes the contribution rules that matter most before opening a pull request.

## Main Rules

- do not commit directly to `main`;
- use `feat/`, `fix/`, `docs/`, or `chore/` branch prefixes;
- use Conventional Commits;
- keep Python source under `src/`;
- use Ruff for linting and formatting;
- keep runtime paths behind `ConfigManager`.

## Local Validation

Run these commands before opening a PR:

```bash
pytest tests/
ruff check . --select C901
ruff format .
```

## Architectural Guardrails

- `studio_ui/` can depend on `universal_iiif_core/`, never the reverse.
- Routes should orchestrate, not own core logic.
- Shared network behavior should go through the centralized HTTP client.

## Full Policy

For the full repository policy, see
[`CONTRIBUTING.md`](https://github.com/nikazzio/scriptoria/blob/main/CONTRIBUTING.md).
