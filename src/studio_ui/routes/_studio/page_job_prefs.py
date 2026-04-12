"""Per-page download-job preference helpers (highres / stitch)."""

from __future__ import annotations

import json
from typing import Any

from universal_iiif_core.logger import get_logger
from universal_iiif_core.services.storage.vault_manager import VaultManager

logger = get_logger(__name__)

_STUDIO_EXPORT_HIGHRES_PREF_KEY = "studio_export_highres_jobs"
_STUDIO_EXPORT_STITCH_PREF_KEY = "studio_export_stitch_jobs"


def _load_last_optimization_meta(doc_id: str) -> dict[str, Any]:
    row = VaultManager().get_manuscript(doc_id) or {}
    raw = str(row.get("local_optimization_meta_json") or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _page_delta_map(meta: dict[str, Any]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for item in meta.get("page_deltas") or []:
        if not isinstance(item, dict):
            continue
        try:
            page = int(item.get("page") or 0)
        except (TypeError, ValueError):
            continue
        if page <= 0:
            continue
        out[page] = item
    return out


def _normalize_page_job_pref(raw_pref: Any) -> dict[int, dict[str, Any]]:
    if not isinstance(raw_pref, dict):
        return {}
    normalized: dict[int, dict[str, Any]] = {}
    for raw_page, payload in raw_pref.items():
        try:
            page_num = int(raw_page)
        except (TypeError, ValueError):
            continue
        if page_num <= 0:
            continue
        if isinstance(payload, dict):
            job_id = str(payload.get("job_id") or "").strip()
            state = str(payload.get("state") or "").strip().lower()
            source_ts = str(payload.get("source_ts") or "").strip()
        else:
            job_id = str(payload or "").strip()
            state = ""
            source_ts = ""
        if not job_id:
            continue
        normalized[page_num] = {"job_id": job_id, "state": state, "source_ts": source_ts}
    return normalized


def _load_page_job_pref(doc_id: str, pref_key: str) -> dict[int, dict[str, Any]]:
    raw_pref = VaultManager().get_manuscript_ui_pref(doc_id, pref_key, {})
    return _normalize_page_job_pref(raw_pref)


def _save_page_job_pref(doc_id: str, pref_key: str, page_jobs: dict[int, dict[str, Any]]) -> None:
    payload = {
        str(int(page)): {
            "job_id": str((entry or {}).get("job_id") or ""),
            "state": str((entry or {}).get("state") or ""),
            "source_ts": str((entry or {}).get("source_ts") or ""),
        }
        for page, entry in page_jobs.items()
        if int(page) > 0 and str((entry or {}).get("job_id") or "").strip()
    }
    VaultManager().set_manuscript_ui_pref(doc_id, pref_key, payload)


def _load_highres_pref(doc_id: str) -> dict[int, dict[str, Any]]:
    return _load_page_job_pref(doc_id, _STUDIO_EXPORT_HIGHRES_PREF_KEY)


def _save_highres_pref(doc_id: str, page_jobs: dict[int, dict[str, Any]]) -> None:
    _save_page_job_pref(doc_id, _STUDIO_EXPORT_HIGHRES_PREF_KEY, page_jobs)


def _load_stitch_pref(doc_id: str) -> dict[int, dict[str, Any]]:
    return _load_page_job_pref(doc_id, _STUDIO_EXPORT_STITCH_PREF_KEY)


def _save_stitch_pref(doc_id: str, page_jobs: dict[int, dict[str, Any]]) -> None:
    _save_page_job_pref(doc_id, _STUDIO_EXPORT_STITCH_PREF_KEY, page_jobs)
