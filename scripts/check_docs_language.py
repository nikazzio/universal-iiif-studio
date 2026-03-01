#!/usr/bin/env python3
"""Fail when a markdown document mixes English and Italian significantly.

Policy:
- Most markdown files are expected to be English.
- `docs/DOCUMENTAZIONE.md` is expected to be Italian.
- A file fails if both language scores are significant, or if dominant language
  does not match the file expectation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DOC_FILES = [
    *sorted(Path("docs").glob("*.md")),
    Path("README.md"),
    Path("AGENTS.md"),
    Path("CHANGELOG.md"),
]

EXPECTED_LANGUAGE: dict[str, str] = {
    "docs/DOCUMENTAZIONE.md": "it",
}

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
}

IT_WORDS = {
    "e",
    "con",
    "per",
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
}


class ValidationError(RuntimeError):
    """Raised when language policy is violated."""


def _strip_code_blocks(text: str) -> str:
    return re.sub(r"```.*?```", " ", text, flags=re.DOTALL)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z]{2,}", text.lower())


def _score(tokens: list[str], lexicon: set[str]) -> int:
    return sum(1 for token in tokens if token in lexicon)


def _is_mixed(en_score: int, it_score: int) -> bool:
    # Significant counts for both dictionaries implies mixed-language prose.
    return en_score >= 6 and it_score >= 6


def main() -> int:
    """Validate language consistency in markdown files."""
    cli_paths = [Path(p) for p in sys.argv[1:]]
    targets = cli_paths if cli_paths else DOC_FILES
    failures: list[str] = []

    for path in targets:
        if not path.exists():
            continue

        text = path.read_text(encoding="utf-8")
        normalized = _strip_code_blocks(text)
        tokens = _tokenize(normalized)

        en_score = _score(tokens, EN_WORDS)
        it_score = _score(tokens, IT_WORDS)

        expected = EXPECTED_LANGUAGE.get(path.as_posix(), "en")

        if expected == "en":
            if _is_mixed(en_score, it_score):
                failures.append(f"{path}: mixed language detected (en_score={en_score}, it_score={it_score}).")
                continue
            if it_score >= 6 and it_score > en_score:
                failures.append(f"{path}: expected English but Italian appears dominant.")

        if expected == "it" and en_score >= 12 and en_score > int(it_score * 1.2):
            # Italian docs may naturally include some English technical words.
            failures.append(f"{path}: expected Italian but English appears dominant.")

    if failures:
        details = "\n".join(f"- {item}" for item in failures)
        raise ValidationError(f"Docs language check failed:\n{details}")

    print("Docs language check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
