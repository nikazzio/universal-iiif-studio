"""Download feedback computation helpers (highres / stitch / optimize)."""

from __future__ import annotations

import time
from contextlib import suppress
from typing import Any

from universal_iiif_core.logger import get_logger
from universal_iiif_core.services.storage.vault_manager import VaultManager

from .page_job_prefs import (
    _STUDIO_EXPORT_HIGHRES_PREF_KEY,
    _STUDIO_EXPORT_STITCH_PREF_KEY,
    _load_page_job_pref,
    _save_page_job_pref,
)
from .page_source_prefs import (
    _apply_preferred_source_to_feedback,
    _load_page_source_pref,
    _merge_page_source_pref,
    _save_page_source_pref,
    _should_mark_highres_source_update,
)

logger = get_logger(__name__)

_ACTIVE_DOWNLOAD_STATES = {"queued", "running", "cancelling", "pausing"}


def _normalize_feedback_map(raw_map: dict[int, dict[str, str]] | None) -> dict[int, dict[str, str]]:
    normalized: dict[int, dict[str, str]] = {}
    for raw_page, payload in (raw_map or {}).items():
        try:
            page = int(raw_page)
        except (TypeError, ValueError):
            continue
        if page <= 0:
            continue
        normalized[page] = dict(payload or {})
    return normalized


def _set_idle_feedback(feedback: dict[str, str], *, label: str, tone: str = "info") -> dict[str, str]:
    feedback["state"] = "idle"
    feedback["progress_percent"] = "0"
    feedback["tone"] = tone
    feedback["label"] = label
    return feedback


def _force_done_feedback(feedback: dict[str, str], *, label: str) -> dict[str, str]:
    out = dict(feedback or {})
    out["state"] = "done"
    out["progress_percent"] = "100"
    out["tone"] = str(out.get("tone") or "success")
    out["label"] = label
    return out


def _download_feedback_row(
    *,
    status: str,
    current: int,
    total: int,
    source_ts: str = "",
    idle_label: str,
    queued_label: str,
    running_label: str,
    done_label: str,
    error_label: str,
    interrupted_label: str,
) -> dict[str, str]:
    status_key = str(status or "").strip().lower()
    source_value = str(source_ts or "").strip()
    percent = 0
    if total > 0:
        percent = int(max(0, min(100, (max(0, int(current)) / max(1, int(total))) * 100)))
    if status_key == "queued":
        return {"state": "queued", "tone": "info", "label": queued_label, "progress_percent": "0"}
    if status_key in {"running", "cancelling", "pausing"}:
        return {
            "state": "running",
            "tone": "warning",
            "label": running_label,
            "progress_percent": str(percent),
        }
    if status_key == "completed":
        return {
            "state": "done",
            "tone": "success",
            "label": done_label,
            "progress_percent": "100",
            "source_ts": source_value,
        }
    if status_key in {"error", "failed"}:
        return {
            "state": "error",
            "tone": "danger",
            "label": error_label,
            "progress_percent": "100",
            "source_ts": source_value,
        }
    if status_key in {"cancelled", "paused"}:
        return {
            "state": "error",
            "tone": "warning",
            "label": interrupted_label,
            "progress_percent": "100",
            "source_ts": source_value,
        }
    return {"state": "idle", "tone": "info", "label": idle_label, "progress_percent": "0"}


def _resolve_page_download_feedback(
    doc_id: str,
    library: str,
    *,
    pref_key: str,
    success_source: str,
    idle_label: str,
    queued_label: str,
    running_label: str,
    done_label: str,
    error_label: str,
    interrupted_label: str,
) -> tuple[dict[int, dict[str, str]], bool]:
    pref = _load_page_job_pref(doc_id, pref_key)
    if not pref:
        return {}, False

    existing_source_pref = _load_page_source_pref(doc_id)
    vm = VaultManager()
    updated_pref: dict[int, dict[str, Any]] = {}
    source_updates: dict[int, dict[str, str]] = {}
    feedback_by_page: dict[int, dict[str, str]] = {}
    has_active = False

    for page_num, entry in pref.items():
        job_id = str(entry.get("job_id") or "").strip()
        if not job_id:
            continue
        job = vm.get_download_job(job_id) or {}
        job_doc_id = str(job.get("doc_id") or "").strip()
        job_library = str(job.get("library") or "").strip()
        if job and (job_doc_id != doc_id or job_library != library):
            continue

        status = str(job.get("status") or entry.get("state") or "").strip().lower()
        current = int(job.get("current") or 0)
        total = int(job.get("total") or 0)
        source_ts = str(job.get("finished_at") or job.get("updated_at") or entry.get("source_ts") or "").strip()
        feedback = _download_feedback_row(
            status=status,
            current=current,
            total=total,
            source_ts=source_ts,
            idle_label=idle_label,
            queued_label=queued_label,
            running_label=running_label,
            done_label=done_label,
            error_label=error_label,
            interrupted_label=interrupted_label,
        )
        feedback["job_id"] = job_id
        feedback_by_page[page_num] = feedback

        state = str(feedback.get("state") or "").strip().lower()
        if state == "done" and (
            _should_mark_highres_source_update(str(entry.get("state") or ""), state)
            or (page_num not in existing_source_pref and bool(job))
        ):
            source_updates[page_num] = {"source": success_source, "source_ts": str(int(time.time() * 1000))}
        if status in _ACTIVE_DOWNLOAD_STATES or state in {"queued", "running"}:
            has_active = True
            updated_pref[page_num] = {"job_id": job_id, "state": status or state, "source_ts": source_ts}
        else:
            updated_pref[page_num] = {"job_id": job_id, "state": state, "source_ts": source_ts}

    if updated_pref != pref:
        with suppress(Exception):
            _save_page_job_pref(doc_id, pref_key, updated_pref)
    if source_updates:
        with suppress(Exception):
            merged_source_pref = _merge_page_source_pref(existing_source_pref, source_updates)
            if merged_source_pref != existing_source_pref:
                _save_page_source_pref(doc_id, merged_source_pref)
    return feedback_by_page, has_active


def _resolve_highres_page_feedback(doc_id: str, library: str) -> tuple[dict[int, dict[str, str]], bool]:
    return _resolve_page_download_feedback(
        doc_id,
        library,
        pref_key=_STUDIO_EXPORT_HIGHRES_PREF_KEY,
        success_source="highres",
        idle_label="High-Res",
        queued_label="High-Res in coda",
        running_label="High-Res in corso",
        done_label="High-Res completato",
        error_label="Errore High-Res",
        interrupted_label="High-Res interrotto",
    )


def _resolve_stitch_page_feedback(doc_id: str, library: str) -> tuple[dict[int, dict[str, str]], bool]:
    return _resolve_page_download_feedback(
        doc_id,
        library,
        pref_key=_STUDIO_EXPORT_STITCH_PREF_KEY,
        success_source="stitched",
        idle_label="Strategia standard",
        queued_label="Strategia standard in coda",
        running_label="Strategia standard in corso",
        done_label="Strategia standard completata",
        error_label="Errore strategia standard",
        interrupted_label="Strategia standard interrotta",
    )


def _merge_page_feedback(
    base: dict[int, dict[str, str]],
    override: dict[int, dict[str, str]] | None = None,
) -> dict[int, dict[str, str]]:
    merged: dict[int, dict[str, str]] = {}
    for page, payload in (base or {}).items():
        try:
            page_num = int(page)
        except (TypeError, ValueError):
            continue
        if page_num <= 0:
            continue
        merged[page_num] = dict(payload or {})
    for page, payload in (override or {}).items():
        try:
            page_num = int(page)
        except (TypeError, ValueError):
            continue
        if page_num <= 0:
            continue
        next_payload = dict(payload or {})
        if not next_payload:
            continue
        merged[page_num] = {**merged.get(page_num, {}), **next_payload}
    return merged


def _optimize_feedback_from_deltas(
    page_delta_by_num: dict[int, dict[str, Any]],
    *,
    optimized_at: str = "",
) -> dict[int, dict[str, str]]:
    optimize_ts = str(optimized_at or "").strip()
    feedback_by_page: dict[int, dict[str, str]] = {}
    for page_num, payload in (page_delta_by_num or {}).items():
        try:
            page = int(page_num)
        except (TypeError, ValueError):
            continue
        if page <= 0:
            continue
        status = str((payload or {}).get("status") or "").strip().lower()
        if status == "ok":
            feedback_by_page[page] = {
                "state": "done",
                "tone": "success",
                "label": "Ottimizzata",
                "progress_percent": "100",
                "source_ts": optimize_ts,
            }
            continue
        if status == "error":
            feedback_by_page[page] = {
                "state": "error",
                "tone": "danger",
                "label": "Errore ottimizzazione",
                "progress_percent": "100",
                "source_ts": optimize_ts,
            }
    return feedback_by_page


def _resolve_current_image_feedback(
    highres_feedback_by_num: dict[int, dict[str, str]],
    stitch_feedback_by_num: dict[int, dict[str, str]],
    optimize_feedback_by_num: dict[int, dict[str, str]],
    preferred_source_by_page: dict[int, dict[str, str]] | None = None,
) -> tuple[dict[int, dict[str, str]], dict[int, dict[str, str]], dict[int, dict[str, str]]]:
    resolved_highres = _normalize_feedback_map(highres_feedback_by_num)
    resolved_stitch = _normalize_feedback_map(stitch_feedback_by_num)
    resolved_opt = _normalize_feedback_map(optimize_feedback_by_num)
    preferred = _normalize_feedback_map(preferred_source_by_page)
    pages = (
        set(resolved_highres.keys()) | set(resolved_stitch.keys()) | set(resolved_opt.keys()) | set(preferred.keys())
    )
    done_priority = {"highres": 0, "stitched": 1, "optimized": 2}
    labels = {"highres": "High-Res", "stitched": "Strategia standard", "optimized": "Ottimizza"}
    for page in pages:
        hi = resolved_highres.get(page) or {}
        stitch = resolved_stitch.get(page) or {}
        opt = resolved_opt.get(page) or {}
        preferred_source = str((preferred.get(page) or {}).get("source") or "").strip().lower()
        hi, stitch, opt, consumed = _apply_preferred_source_to_feedback(
            highres_feedback=hi,
            stitch_feedback=stitch,
            optimize_feedback=opt,
            preferred_source=preferred_source,
        )
        resolved_highres[page] = hi
        resolved_stitch[page] = stitch
        resolved_opt[page] = opt
        if consumed:
            continue
        all_feedback = {
            "highres": hi,
            "stitched": stitch,
            "optimized": opt,
        }
        done_sources = [
            source
            for source, payload in all_feedback.items()
            if str(payload.get("state") or "").strip().lower() == "done"
        ]
        if not done_sources:
            continue
        preferred_done = max(
            done_sources,
            key=lambda source: (
                str(all_feedback[source].get("source_ts") or ""),
                -done_priority[source],
            ),
        )
        for source, payload in all_feedback.items():
            if source == preferred_done:
                continue
            if str(payload.get("state") or "").strip().lower() == "done":
                all_feedback[source] = _set_idle_feedback(payload, label=labels[source])
        resolved_highres[page] = all_feedback["highres"]
        resolved_stitch[page] = all_feedback["stitched"]
        resolved_opt[page] = all_feedback["optimized"]

    return resolved_highres, resolved_stitch, resolved_opt
