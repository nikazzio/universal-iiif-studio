#!/usr/bin/env python3
"""Fail when markdown documentation is not predominantly English prose."""

from __future__ import annotations

import re
import sys
from pathlib import Path

DOC_FILES = [
    Path("README.md"),
    *sorted(Path("docs").rglob("*.md")),
    Path("tests/README.md"),
    Path("AGENTS.md"),
]

EN_WORDS = {
    "the",
    "and",
    "with",
    "for",
    "from",
    "this",
    "that",
    "must",
    "should",
    "run",
    "use",
    "settings",
    "download",
    "release",
    "workflow",
    "added",
    "changed",
    "fixed",
    "guide",
    "local",
    "viewer",
    "profile",
}

IT_WORDS = {
    "e",
    "con",
    "questo",
    "questa",
    "deve",
    "dovrebbe",
    "usa",
    "impostazioni",
    "scarica",
    "rilascio",
    "flusso",
    "aggiunto",
    "modificato",
    "corretto",
    "cartella",
    "pagina",
    "lavoro",
    "remota",
    "locale",
}


class ValidationError(RuntimeError):
    """Raised when language policy is violated."""


def _strip_code(text: str) -> str:
    without_fenced = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    without_inline = re.sub(r"`[^`]+`", " ", without_fenced)
    return without_inline


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z]{2,}", text.lower())


def _score(tokens: list[str], lexicon: set[str]) -> int:
    return sum(1 for token in tokens if token in lexicon)


def _is_mixed(en_score: int, it_score: int) -> bool:
    return en_score >= 6 and it_score >= 6


def main() -> int:
    """Validate that project docs are English-only prose."""
    cli_paths = [Path(p) for p in sys.argv[1:]]
    targets = cli_paths if cli_paths else DOC_FILES
    failures: list[str] = []

    for path in targets:
        if not path.exists():
            continue

        text = path.read_text(encoding="utf-8")
        normalized = _strip_code(text)
        tokens = _tokenize(normalized)

        en_score = _score(tokens, EN_WORDS)
        it_score = _score(tokens, IT_WORDS)

        if _is_mixed(en_score, it_score):
            failures.append(f"{path}: mixed language detected (en_score={en_score}, it_score={it_score}).")
            continue

        if it_score >= 6 and it_score > en_score:
            failures.append(f"{path}: expected English but Italian appears dominant.")

    if failures:
        details = "\n".join(f"- {item}" for item in failures)
        raise ValidationError(f"Docs language check failed:\n{details}")

    print("Docs language check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
