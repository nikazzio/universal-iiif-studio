"""Per-page preferred-source preference helpers (highres / optimized / stitched)."""

from __future__ import annotations

import time
from contextlib import suppress
from typing import Any

from universal_iiif_core.logger import get_logger
from universal_iiif_core.services.storage.vault_manager import VaultManager

logger = get_logger(__name__)

_STUDIO_EXPORT_PAGE_SOURCE_PREF_KEY = "studio_export_page_sources"


def _normalize_page_source_pref(raw_pref: Any) -> dict[int, dict[str, str]]:
    if not isinstance(raw_pref, dict):
        return {}
    normalized: dict[int, dict[str, str]] = {}
    for raw_page, payload in raw_pref.items():
        try:
            page_num = int(raw_page)
        except (TypeError, ValueError):
            continue
        if page_num <= 0 or not isinstance(payload, dict):
            continue
        source = str(payload.get("source") or "").strip().lower()
        source_ts = str(payload.get("source_ts") or "").strip()
        if source not in {"highres", "optimized", "stitched"}:
            continue
        normalized[page_num] = {"source": source, "source_ts": source_ts}
    return normalized


def _load_page_source_pref(doc_id: str) -> dict[int, dict[str, str]]:
    raw_pref = VaultManager().get_manuscript_ui_pref(doc_id, _STUDIO_EXPORT_PAGE_SOURCE_PREF_KEY, {})
    return _normalize_page_source_pref(raw_pref)


def _save_page_source_pref(doc_id: str, page_source_map: dict[int, dict[str, str]]) -> None:
    payload = {
        str(int(page)): {
            "source": str((entry or {}).get("source") or ""),
            "source_ts": str((entry or {}).get("source_ts") or ""),
        }
        for page, entry in page_source_map.items()
        if int(page) > 0 and str((entry or {}).get("source") or "").strip() in {"highres", "optimized", "stitched"}
    }
    VaultManager().set_manuscript_ui_pref(doc_id, _STUDIO_EXPORT_PAGE_SOURCE_PREF_KEY, payload)


def _merge_page_source_pref(
    existing: dict[int, dict[str, str]],
    updates: dict[int, dict[str, str]],
) -> dict[int, dict[str, str]]:
    merged = {int(page): dict(payload or {}) for page, payload in (existing or {}).items() if int(page) > 0}
    for raw_page, payload in (updates or {}).items():
        try:
            page = int(raw_page)
        except (TypeError, ValueError):
            continue
        if page <= 0:
            continue
        source = str((payload or {}).get("source") or "").strip().lower()
        source_ts = str((payload or {}).get("source_ts") or "").strip()
        if source not in {"highres", "optimized", "stitched"}:
            continue
        merged[page] = {"source": source, "source_ts": source_ts}
    return merged


def _apply_single_preferred_source(
    *,
    preferred_source: str,
    preferred_feedback: dict[str, str],
    preferred_label: str,
    other_feedbacks: list[tuple[dict[str, str], str]],
) -> tuple[dict[str, str], list[dict[str, str]]]:
    from .download_feedback import _force_done_feedback, _set_idle_feedback

    preferred_state = str(preferred_feedback.get("state") or "").strip().lower()
    if preferred_state not in {"queued", "running"}:
        preferred_feedback = _force_done_feedback(preferred_feedback, label=preferred_label)
    updated_others: list[dict[str, str]] = []
    for payload, label in other_feedbacks:
        if str(payload.get("state") or "").strip().lower() == "done":
            payload = _set_idle_feedback(payload, label=label)
        updated_others.append(payload)
    return preferred_feedback, updated_others


def _apply_preferred_source_to_feedback(
    *,
    highres_feedback: dict[str, str],
    stitch_feedback: dict[str, str],
    optimize_feedback: dict[str, str],
    preferred_source: str,
) -> tuple[dict[str, str], dict[str, str], dict[str, str], bool]:
    if preferred_source == "highres":
        highres_feedback, others = _apply_single_preferred_source(
            preferred_source=preferred_source,
            preferred_feedback=highres_feedback,
            preferred_label="High-Res",
            other_feedbacks=[(stitch_feedback, "Strategia standard"), (optimize_feedback, "Ottimizza")],
        )
        stitch_feedback, optimize_feedback = others
        return highres_feedback, stitch_feedback, optimize_feedback, True
    if preferred_source == "stitched":
        stitch_feedback, others = _apply_single_preferred_source(
            preferred_source=preferred_source,
            preferred_feedback=stitch_feedback,
            preferred_label="Strategia standard",
            other_feedbacks=[(highres_feedback, "High-Res"), (optimize_feedback, "Ottimizza")],
        )
        highres_feedback, optimize_feedback = others
        return highres_feedback, stitch_feedback, optimize_feedback, True
    if preferred_source == "optimized":
        optimize_feedback, others = _apply_single_preferred_source(
            preferred_source=preferred_source,
            preferred_feedback=optimize_feedback,
            preferred_label="Ottimizzata",
            other_feedbacks=[(highres_feedback, "High-Res"), (stitch_feedback, "Strategia standard")],
        )
        highres_feedback, stitch_feedback = others
        return highres_feedback, stitch_feedback, optimize_feedback, True
    return highres_feedback, stitch_feedback, optimize_feedback, False


def _should_mark_highres_source_update(prev_state: str, current_state: str) -> bool:
    prev = str(prev_state or "").strip().lower()
    now = str(current_state or "").strip().lower()
    if prev == "completed":
        prev = "done"
    return now == "done" and prev != "done"


def _persist_optimized_page_source_pref(doc_id: str, meta: dict[str, Any]) -> None:
    optimize_ts = str(int(time.time() * 1000))
    optimized_source_updates: dict[int, dict[str, str]] = {}
    for delta in meta.get("page_deltas") or []:
        if not isinstance(delta, dict):
            continue
        try:
            page_num = int(delta.get("page") or 0)
        except (TypeError, ValueError):
            continue
        if page_num <= 0:
            continue
        if str(delta.get("status") or "").strip().lower() != "ok":
            continue
        optimized_source_updates[page_num] = {"source": "optimized", "source_ts": optimize_ts}
    if not optimized_source_updates:
        return
    with suppress(Exception):
        existing_source_pref = _load_page_source_pref(doc_id)
        merged_source_pref = _merge_page_source_pref(existing_source_pref, optimized_source_updates)
        if merged_source_pref != existing_source_pref:
            _save_page_source_pref(doc_id, merged_source_pref)
