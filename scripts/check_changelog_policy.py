#!/usr/bin/env python3
"""Validate CHANGELOG format policy.

Checks:
- Release headings: ## [vX.Y.Z] - YYYY-MM-DD
- Required sections per release: Added, Changed, Fixed
- Top-level non-empty bullets end with issue/PR reference: (#123)
"""

from __future__ import annotations

import re
from pathlib import Path

CHANGELOG_PATH = Path("CHANGELOG.md")
RE_HEADING = re.compile(r"^## \[(v\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$")
RE_SECTION = re.compile(r"^### (Added|Changed|Fixed)$")
RE_REF = re.compile(r"\(#\d+\)\.?$")


class ValidationError(RuntimeError):
    """Raised when the changelog policy is violated."""


def _iter_release_blocks(lines: list[str]) -> list[tuple[str, list[str]]]:
    blocks: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in lines:
        heading = RE_HEADING.match(line)
        if heading:
            if current_title is not None:
                blocks.append((current_title, current_lines))
            current_title = line
            current_lines = []
            continue

        if current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        blocks.append((current_title, current_lines))

    return blocks


def _validate_release_block(title: str, block_lines: list[str]) -> list[str]:
    errors: list[str] = []
    sections_seen: set[str] = set()
    current_section: str | None = None

    for line in block_lines:
        section = RE_SECTION.match(line)
        if section:
            current_section = section.group(1)
            sections_seen.add(current_section)
            continue

        if current_section is None:
            continue

        if line.startswith("- "):
            item = line[2:].strip()
            if item.lower() == "none.":
                continue
            if not RE_REF.search(item):
                errors.append(f"{title}: bullet missing issue/PR reference -> '{line}'")

    missing = {"Added", "Changed", "Fixed"} - sections_seen
    for section_name in sorted(missing):
        errors.append(f"{title}: missing section '### {section_name}'")

    return errors


def main() -> int:
    if not CHANGELOG_PATH.exists():
        raise ValidationError("CHANGELOG.md not found")

    lines = CHANGELOG_PATH.read_text(encoding="utf-8").splitlines()
    release_blocks = _iter_release_blocks(lines)
    if not release_blocks:
        raise ValidationError("No release blocks found. Expected headings like '## [vX.Y.Z] - YYYY-MM-DD'.")

    errors: list[str] = []
    for title, block in release_blocks:
        errors.extend(_validate_release_block(title, block))

    if errors:
        msg = "\n".join(f"- {err}" for err in errors)
        raise ValidationError(f"CHANGELOG policy validation failed:\n{msg}")

    print("CHANGELOG policy validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
