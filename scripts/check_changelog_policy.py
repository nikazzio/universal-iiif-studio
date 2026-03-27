#!/usr/bin/env python3
"""Validate CHANGELOG format policy.

Checks:
- Release headings: ## [vX.Y.Z] - YYYY-MM-DD or ## vX.Y.Z (YYYY-MM-DD)
- At least one subsection per release block
- Top-level non-empty bullets end with issue/PR reference or generated commit link
"""

from __future__ import annotations

import re
from pathlib import Path

CHANGELOG_PATH = Path("CHANGELOG.md")
INSERTION_FLAG = "<!-- version list -->"
RE_HEADING = re.compile(r"^(## \[(v\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})|## v\d+\.\d+\.\d+ \(\d{4}-\d{2}-\d{2}\))$")
RE_SECTION = re.compile(r"^### (?P<section>[A-Za-z][A-Za-z /-]*)$")
RE_ISSUE_REF = re.compile(r"(\(#\d+\)|\[#\d+\]\()")
RE_COMMIT_LINK = re.compile(r"\(\[`[0-9a-f]{7,}`\]\(https?://[^)]+\)\)\.?$")


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


def _collapse_bullets(block_lines: list[str]) -> list[tuple[str, str]]:
    """Collapse multi-line bullets into (first_line, full_text) pairs.

    python-semantic-release places commit links on indented continuation
    lines.  We join them so the reference check sees the complete bullet.
    """
    bullets: list[tuple[str, str]] = []
    current_first: str | None = None
    current_parts: list[str] = []

    for line in block_lines:
        if line.startswith("- "):
            if current_first is not None:
                bullets.append((current_first, " ".join(current_parts)))
            current_first = line
            current_parts = [line[2:].strip()]
        elif current_first is not None and line.startswith("  "):
            current_parts.append(line.strip())
        else:
            if current_first is not None:
                bullets.append((current_first, " ".join(current_parts)))
                current_first = None
                current_parts = []

    if current_first is not None:
        bullets.append((current_first, " ".join(current_parts)))

    return bullets


def _validate_release_block(title: str, block_lines: list[str]) -> list[str]:
    errors: list[str] = []
    sections_seen: set[str] = set()
    current_section: str | None = None
    section_lines: list[str] = []

    def _check_section_bullets() -> None:
        for first_line, full_text in _collapse_bullets(section_lines):
            if full_text.lower() == "none.":
                continue
            if not RE_ISSUE_REF.search(full_text) and not RE_COMMIT_LINK.search(full_text):
                errors.append(f"{title}: bullet missing issue/PR reference -> '{first_line}'")

    for line in block_lines:
        section = RE_SECTION.match(line)
        if section:
            _check_section_bullets()
            current_section = section.group("section")
            sections_seen.add(current_section)
            section_lines = []
            continue

        if current_section is None:
            continue

        section_lines.append(line)

    _check_section_bullets()

    if not sections_seen and not any(line.startswith("**Detailed Changes**:") for line in block_lines):
        errors.append(f"{title}: missing at least one '### <section>' subsection")

    return errors


def main() -> int:
    """Validate changelog policy requirements."""
    if not CHANGELOG_PATH.exists():
        raise ValidationError("CHANGELOG.md not found")

    lines = CHANGELOG_PATH.read_text(encoding="utf-8").splitlines()
    if INSERTION_FLAG not in lines:
        raise ValidationError(
            "CHANGELOG.md missing semantic-release insertion flag '<!-- version list -->'.",
        )
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
