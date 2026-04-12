# Contributing to Scriptoria

Thanks for your interest in contributing! This guide will help you get started.

## Prerequisites

- Python 3.10+
- pip
- Git

## Setup

```bash
git clone https://github.com/nikazzio/scriptoria.git
cd scriptoria
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Development Workflow

### Branch Naming

Create branches with a prefix that describes the type of change:

- `feat/` — new features
- `fix/` — bug fixes
- `docs/` — documentation
- `chore/` — maintenance, dependencies, CI

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add batch download support
fix: resolve thumbnail cache invalidation
docs: update configuration reference
chore: bump ruff to 0.8.x
```

### Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting. Before submitting:

```bash
ruff check . --fix    # lint
ruff format .         # format
ruff check . --select C901   # complexity check (max 10)
```

### Running Tests

```bash
pytest tests/              # full suite
pytest tests/test_foo.py   # single file
```

### Running the App

```bash
scriptoria              # web UI
scriptoria-cli "<url>"  # CLI
```

## Submitting a Pull Request

1. Fork the repo and create your branch from `main`
2. Make your changes
3. Run lint and tests
4. Open a PR with a clear title and description
5. Reference any related issues (e.g. `Closes #42`)

### PR Guidelines

- Keep PRs focused — one logical change per PR
- Update tests if you change behavior
- Don't commit to `main` directly

## Architecture

For architectural context before making structural changes, read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

Key constraints:

- `studio_ui/` depends on `universal_iiif_core/`, never the reverse
- Routes orchestrate, they don't implement logic — logic goes in `universal_iiif_core/`
- Use the centralized HTTP client (`universal_iiif_core.http_client`)
- Use `pathlib.Path` for all path operations

## Reporting Bugs

Open a [GitHub issue](https://github.com/nikazzio/scriptoria/issues/new) with:

- Steps to reproduce
- Expected vs actual behavior
- Scriptoria version (`scriptoria --version`)
- OS and Python version

## License

By submitting a pull request, you agree that your contribution is licensed under the [MIT License](LICENSE) that covers this project.
