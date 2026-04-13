#!/usr/bin/env python3
"""Validate key documentation invariants used by CI."""

from __future__ import annotations

from pathlib import Path


class ValidationError(RuntimeError):
    """Raised when documentation integrity checks fail."""


REQUIRED_FILES = [
    Path("README.md"),
    Path("package.json"),
    Path("docusaurus.config.js"),
    Path("sidebars.js"),
    Path("docs/index.md"),
    Path("docs/intro/getting-started.md"),
    Path("docs/guides/first-manuscript-workflow.md"),
    Path("docs/reference/cli.md"),
    Path("docs/explanation/architecture.md"),
    Path("docs/project/wiki-maintenance.md"),
    Path("docs/wiki/Home.md"),
]

REQUIRED_README_LINKS = [
    "(docs/index.md)",
    "(docs/intro/getting-started.md)",
    "(docs/explanation/architecture.md)",
    "(docs/reference/configuration.md)",
    "(docs/reference/cli.md)",
]

REQUIRED_DOC_LINK_MARKERS = [
    "(intro/getting-started.md)",
    "(guides/first-manuscript-workflow.md)",
    "(reference/cli.md)",
]


def _must_exist(path: Path, failures: list[str]) -> None:
    if not path.exists():
        failures.append(f"Missing required documentation file: {path}")


def main() -> int:
    """Run documentation integrity validation."""
    failures: list[str] = []

    for path in REQUIRED_FILES:
        _must_exist(path, failures)

    readme_text = Path("README.md").read_text(encoding="utf-8")
    for link in REQUIRED_README_LINKS:
        if link not in readme_text:
            failures.append(f"README.md is missing required documentation link: {link}")

    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    for marker in REQUIRED_DOC_LINK_MARKERS:
        if marker not in docs_index:
            failures.append(f"docs/index.md is missing required docs link: {marker}")

    if failures:
        details = "\n".join(f"- {item}" for item in failures)
        raise ValidationError(f"Documentation integrity check failed:\n{details}")

    print("Documentation integrity check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
