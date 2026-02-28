"""Shared title selection and truncation utilities for Studio UI."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from universal_iiif_core.library_catalog import is_generic_catalog_text

DEFAULT_TITLE_MAX_LEN = 70
DEFAULT_TITLE_SUFFIX = "[...]"


def _compact_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _looks_like_signature(text: str) -> bool:
    value = (text or "").strip()
    if not value:
        return False
    compact = _compact_text(value)
    if not compact:
        return False
    if re.fullmatch(r"[a-z]{1,8}[0-9]{1,8}[a-z0-9]*", compact):
        return True
    has_digits = any(ch.isdigit() for ch in value)
    words = len(value.split())
    return has_digits and words <= 3 and len(value) <= 24


def _title_score(value: str, source: str, shelfmark: str, doc_id: str) -> int:
    text = (value or "").strip()
    if not text:
        return -999
    if is_generic_catalog_text(text):
        return -999

    score = len(text)
    words = len(text.split())
    score += words * 6

    if source in {"catalog_title", "display_title", "title"}:
        score += 28
    elif source == "reference_text":
        score += 22
    elif source == "shelfmark":
        score += 4
    elif source == "id":
        score += 1

    compact = _compact_text(text)
    if compact and compact == _compact_text(shelfmark):
        score -= 40
    if compact and compact == _compact_text(doc_id):
        score -= 35
    if _looks_like_signature(text):
        score -= 20
    return score


def resolve_preferred_title(row: Mapping[str, Any] | None, fallback_doc_id: str = "") -> str:
    """Resolve the best human title using the same heuristics as Library cards."""
    payload = dict(row or {})
    shelfmark = str(payload.get("shelfmark") or "").strip()
    doc_id = str(payload.get("id") or fallback_doc_id or "").strip()

    candidates: list[tuple[str, str]] = [
        ("catalog_title", str(payload.get("catalog_title") or "").strip()),
        ("display_title", str(payload.get("display_title") or "").strip()),
        ("title", str(payload.get("title") or "").strip()),
        ("reference_text", str(payload.get("reference_text") or "").strip()),
        ("shelfmark", shelfmark),
        ("id", doc_id),
    ]
    scored = sorted(
        (
            (candidate, _title_score(candidate, source, shelfmark, doc_id))
            for source, candidate in candidates
            if candidate
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    if scored and scored[0][1] > -500:
        return scored[0][0]
    return doc_id or shelfmark or "-"


def truncate_title(
    text: str,
    max_len: int = DEFAULT_TITLE_MAX_LEN,
    suffix: str = DEFAULT_TITLE_SUFFIX,
) -> str:
    """Truncate a title with an explicit suffix."""
    value = (text or "").strip()
    if not value or len(value) <= max_len:
        return value

    effective_max = max(1, max_len - len(suffix))
    cut = value[:effective_max].rstrip()
    if " " in cut:
        split_at = cut.rfind(" ")
        if split_at >= int(effective_max * 0.6):
            cut = cut[:split_at].rstrip()
    return f"{cut}{suffix}"


__all__ = [
    "DEFAULT_TITLE_MAX_LEN",
    "DEFAULT_TITLE_SUFFIX",
    "resolve_preferred_title",
    "truncate_title",
]
