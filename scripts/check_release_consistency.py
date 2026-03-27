#!/usr/bin/env python3
"""Validate semantic-release configuration and version consistency."""

from __future__ import annotations

import re
from pathlib import Path

PYPROJECT_PATH = Path("pyproject.toml")
RUNTIME_VERSION_PATH = Path("src/universal_iiif_core/__init__.py")
CHANGELOG_PATH = Path("CHANGELOG.md")
RELEASE_WORKFLOW_PATH = Path(".github/workflows/release.yml")
INSERTION_FLAG = "<!-- version list -->"

RE_PROJECT_BLOCK = re.compile(r"(?ms)^\[project\]\n(?P<body>.*?)(?:^\[|\Z)")
RE_SEMREL_BLOCK = re.compile(r"(?ms)^\[tool\.semantic_release\]\n(?P<body>.*?)(?:^\[|\Z)")
RE_PROJECT_VERSION = re.compile(r'(?m)^version\s*=\s*"(?P<version>[^"]+)"\s*$')
RE_RUNTIME_VERSION = re.compile(r'(?m)^__version__\s*=\s*"(?P<version>[^"]+)"\s*$')


class ValidationError(RuntimeError):
    """Raised when release automation configuration is inconsistent."""


def _extract_project_version(pyproject_text: str) -> str:
    match = RE_PROJECT_BLOCK.search(pyproject_text)
    if not match:
        raise ValidationError("Missing [project] section in pyproject.toml.")
    version_match = RE_PROJECT_VERSION.search(match.group("body"))
    if not version_match:
        raise ValidationError("Missing project.version in pyproject.toml.")
    return version_match.group("version")


def _extract_runtime_version(init_text: str) -> str:
    match = RE_RUNTIME_VERSION.search(init_text)
    if not match:
        raise ValidationError("Missing __version__ declaration in src/universal_iiif_core/__init__.py.")
    return match.group("version")


def _validate_semantic_release_config(pyproject_text: str) -> list[str]:
    errors: list[str] = []
    block = RE_SEMREL_BLOCK.search(pyproject_text)
    if not block:
        return ["Missing [tool.semantic_release] section in pyproject.toml."]

    content = block.group("body")
    if 'version_toml = ["pyproject.toml:project.version"]' not in content:
        errors.append("semantic-release must manage pyproject.toml via version_toml.")
    if 'version_variables = ["src/universal_iiif_core/__init__.py:__version__"]' not in content:
        errors.append("semantic-release must manage src/universal_iiif_core/__init__.py via version_variables.")
    if "[tool.semantic_release.changelog]" not in pyproject_text:
        errors.append("Missing [tool.semantic_release.changelog] configuration.")
    if f'insertion_flag = "{INSERTION_FLAG}"' not in pyproject_text:
        errors.append("semantic-release changelog insertion_flag is not configured.")
    if "[tool.semantic_release.changelog.default_templates]" not in pyproject_text:
        errors.append("Missing [tool.semantic_release.changelog.default_templates] configuration.")
    if 'changelog_file = "CHANGELOG.md"' not in pyproject_text:
        errors.append("semantic-release changelog_file must point to CHANGELOG.md.")
    return errors


def _validate_release_workflow(workflow_text: str) -> list[str]:
    errors: list[str] = []
    if "python-semantic-release>=10.5.3,<11" not in workflow_text:
        errors.append("Release workflow must pin python-semantic-release to a bounded 10.x range.")
    if "semantic-release version --push" not in workflow_text:
        errors.append("Release workflow is missing the semantic-release version step.")
    if "semantic-release publish" not in workflow_text:
        errors.append("Release workflow is missing the semantic-release publish step.")
    return errors


def main() -> int:
    """Validate version sync and semantic-release wiring."""
    if not PYPROJECT_PATH.exists():
        raise ValidationError("pyproject.toml not found")
    if not RUNTIME_VERSION_PATH.exists():
        raise ValidationError("src/universal_iiif_core/__init__.py not found")
    if not CHANGELOG_PATH.exists():
        raise ValidationError("CHANGELOG.md not found")
    if not RELEASE_WORKFLOW_PATH.exists():
        raise ValidationError(".github/workflows/release.yml not found")

    pyproject_text = PYPROJECT_PATH.read_text(encoding="utf-8")
    runtime_text = RUNTIME_VERSION_PATH.read_text(encoding="utf-8")
    changelog_text = CHANGELOG_PATH.read_text(encoding="utf-8")
    workflow_text = RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8")

    errors = _validate_semantic_release_config(pyproject_text)
    errors.extend(_validate_release_workflow(workflow_text))
    if INSERTION_FLAG not in changelog_text:
        errors.append("CHANGELOG.md is missing the semantic-release insertion flag.")

    project_version = _extract_project_version(pyproject_text)
    runtime_version = _extract_runtime_version(runtime_text)
    if project_version != runtime_version:
        errors.append(
            f"Version mismatch: pyproject.toml has {project_version} but __init__.py has {runtime_version}.",
        )

    if errors:
        msg = "\n".join(f"- {err}" for err in errors)
        raise ValidationError(f"Release consistency validation failed:\n{msg}")

    print("Release consistency validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
