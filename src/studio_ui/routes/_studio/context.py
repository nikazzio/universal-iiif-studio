"""Studio context helpers: tab normalisation, recent-hub, title resolution."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote, unquote

from fasthtml.common import H2, A, Div, P, Request, Script, Span

from studio_ui.common.title_utils import resolve_preferred_title, truncate_title
from studio_ui.components.layout import base_layout
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.logger import get_logger
from universal_iiif_core.services.storage.vault_manager import VaultManager

logger = get_logger(__name__)

_STUDIO_ALLOWED_TABS = ("transcription", "snippets", "history", "visual", "info", "images", "output", "jobs")


def _studio_panel_refresh_script(doc_id: str, library: str, page_idx: int, tab: str = "transcription") -> Script:
    """Trigger a targeted refresh of the right Studio panel."""
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    encoded_tab = quote(_normalize_studio_tab(tab), safe="")
    hx_url = f"/studio/partial/tabs?doc_id={encoded_doc}&library={encoded_lib}&page={page_idx}&tab={encoded_tab}"
    return Script(
        "(function(){"
        "setTimeout(function(){"
        "try{ htmx.ajax('GET', '" + hx_url + "', {target:'#studio-right-panel', swap:'innerHTML'}); }"
        "catch(e){ console.error('refresh-err', e); }"
        "}, 50);"
        "})();"
    )


def _normalized_studio_context(doc_id: str, library: str) -> tuple[str, str]:
    """Normalize doc and library query params from URL-encoded values."""
    return unquote(doc_id) if doc_id else "", unquote(library) if library else ""


def _normalize_studio_tab(raw_tab: str | None) -> str:
    value = str(raw_tab or "").strip().lower()
    if value == "export":
        return "images"
    return value if value in _STUDIO_ALLOWED_TABS else "transcription"


def _safe_positive_int(raw: int | str | None, default: int = 1) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return max(1, int(default))
    return max(1, value)


def _studio_recent_limit() -> int:
    raw = get_config_manager().get_setting("ui.studio_recent_max_items", 8)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 8
    return max(1, min(value, 20))


def _save_studio_context_best_effort(doc_id: str, library: str, page: int, tab: str) -> None:
    try:
        VaultManager().save_studio_context(
            doc_id=doc_id,
            library=library,
            page=int(page),
            tab=_normalize_studio_tab(tab),
            max_recent=_studio_recent_limit(),
        )
    except Exception:
        logger.debug("Studio context persistence skipped for %s/%s", library, doc_id, exc_info=True)


def _studio_open_url(doc_id: str, library: str, page: int, tab: str) -> str:
    return (
        f"/studio?doc_id={quote(doc_id, safe='')}"
        f"&library={quote(library, safe='')}"
        f"&page={int(page)}"
        f"&tab={quote(_normalize_studio_tab(tab), safe='')}"
    )


def _resolve_recent_title(context: dict[str, Any], row: dict[str, Any]) -> str:
    doc_id = str(context.get("doc_id") or "")
    fallback = str(row.get("display_title") or row.get("title") or row.get("catalog_title") or doc_id).strip()
    return resolve_preferred_title(row, fallback_doc_id=doc_id).strip() or fallback or doc_id


def _render_studio_recent_hub(*, request: Request, vault: VaultManager):
    limit = _studio_recent_limit()
    last_context = vault.get_studio_last_context() or {}
    contexts = vault.list_studio_recent_contexts(limit=limit)
    items = []
    for context in contexts:
        doc_id = str(context.get("doc_id") or "").strip()
        library = str(context.get("library") or "").strip()
        if not doc_id or not library:
            continue
        row = vault.get_manuscript(doc_id) or {}
        if row and str(row.get("library") or "").strip() not in {"", library}:
            continue
        title = _resolve_recent_title(context, row)
        page = _safe_positive_int(context.get("page"), 1)
        tab = _normalize_studio_tab(str(context.get("tab") or "transcription"))
        updated_at = str(context.get("updated_at") or "").strip() or "n/d"
        items.append(
            Div(
                Div(
                    Span(title, cls="text-sm font-semibold text-slate-900 dark:text-slate-100"),
                    Span(f"{library} · pagina {page} · tab {tab}", cls="text-xs text-slate-500 dark:text-slate-400"),
                    Span(f"Aggiornato: {updated_at}", cls="text-[11px] text-slate-400 dark:text-slate-500"),
                    cls="flex flex-col gap-1 min-w-0",
                ),
                A(
                    "Apri Studio",
                    href=_studio_open_url(doc_id, library, page, tab),
                    cls="app-btn app-btn-primary text-xs whitespace-nowrap",
                ),
                cls=(
                    "flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between "
                    "border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-3"
                ),
            )
        )

    has_last = bool(last_context.get("doc_id")) and bool(last_context.get("library"))
    last_url = (
        _studio_open_url(
            str(last_context.get("doc_id") or ""),
            str(last_context.get("library") or ""),
            _safe_positive_int(last_context.get("page"), 1),
            _normalize_studio_tab(str(last_context.get("tab") or "transcription")),
        )
        if has_last
        else "/library"
    )
    content = Div(
        Div(
            H2("Riprendi lavoro", cls="text-2xl font-black tracking-tight text-slate-900 dark:text-slate-100"),
            P(
                "Riapri velocemente gli ultimi documenti Studio con pagina e tab persistiti lato server.",
                cls="text-sm text-slate-600 dark:text-slate-400",
            ),
            cls="flex flex-col gap-2",
        ),
        Div(
            A(
                "Riprendi ultimo",
                href=last_url,
                cls="app-btn app-btn-primary",
            ),
            A("Apri Libreria", href="/library", cls="app-btn app-btn-secondary"),
            cls="flex flex-wrap gap-2",
        ),
        (
            Div(*items, cls="grid grid-cols-1 gap-3")
            if items
            else Div(
                P("Nessun contesto recente disponibile.", cls="text-sm text-slate-500 dark:text-slate-400"),
                A("Vai in Libreria", href="/library", cls="app-btn app-btn-secondary w-fit"),
                cls=(
                    "rounded-lg border border-dashed border-slate-300 dark:border-slate-600 "
                    "bg-white dark:bg-slate-900/50 p-4 flex flex-col gap-2"
                ),
            )
        ),
        cls="p-6 flex flex-col gap-4",
    )
    if request.headers.get("HX-Request") == "true":
        return content
    return base_layout("Studio", content, active_page="studio")


def _resolve_studio_title(doc_id: str, meta: dict, ms_row: dict) -> tuple[str, str]:
    """Return `(full_title, truncated_title)` for Studio header/info usage."""
    fallback_title = str(meta.get("title") or meta.get("label") or doc_id).strip()
    full_title = resolve_preferred_title(ms_row, fallback_doc_id=doc_id).strip()
    if not full_title or full_title == doc_id:
        full_title = fallback_title or doc_id
    return full_title, truncate_title(full_title, max_len=70, suffix="[...]")
