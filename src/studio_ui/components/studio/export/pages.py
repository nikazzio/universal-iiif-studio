"""Pages summary and subtab for the export tab."""

from __future__ import annotations

from urllib.parse import quote

from fasthtml.common import H3, Button, Div, Input, P, Span

from .pdf_inventory import _bytes_label
from .thumbnails import render_export_thumbnails_loading_shell, render_export_thumbnails_panel


def render_export_pages_summary(
    *,
    scan_summary: dict,
    thumb_total_pages: int,
    thumb_page: int,
    thumb_page_count: int,
    thumb_page_size: int,
    hx_swap_oob: str | None = None,
):
    """Render the aggregated image workspace summary block."""
    attrs = {"id": "studio-export-pages-summary"}
    if hx_swap_oob:
        attrs["hx_swap_oob"] = hx_swap_oob
    return Div(
        Span(
            (
                f"Pagine {thumb_total_pages} · File {int(scan_summary.get('files_count') or 0)} · "
                f"Locale {_bytes_label(int(scan_summary.get('bytes_total') or 0))} · "
                f"Media {_bytes_label(int(scan_summary.get('bytes_avg') or 0))} · "
                f"Max {_bytes_label(int(scan_summary.get('bytes_max') or 0))}"
            ),
            cls="text-xs font-mono text-slate-700 dark:text-slate-200",
        ),
        Span(
            f"Thumb page {thumb_page}/{thumb_page_count} · {thumb_page_size} per pagina",
            cls="text-[11px] text-slate-500 dark:text-slate-400",
        ),
        cls=(
            "flex flex-col gap-1 p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 "
            "bg-white/80 dark:bg-slate-900/80"
        ),
        **attrs,
    )


def _render_export_pages_subtab(
    *,
    doc_id: str,
    library: str,
    scan_summary: dict,
    optimization_meta: dict,
    optimize_feedback: dict,
    thumbnails: list[dict],
    thumb_page: int,
    thumb_page_count: int,
    thumb_total_pages: int,
    thumb_page_size: int,
    thumb_page_size_options: list[int],
    has_active_page_actions: bool = False,
    defer_thumbs_load: bool = False,
):
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    feedback = optimize_feedback or optimization_meta or {}
    optimized_pages = int(feedback.get("optimized_pages") or 0)
    saved_bytes = int(feedback.get("bytes_saved") or 0)
    errors = int(feedback.get("errors") or 0)
    savings_percent = float(feedback.get("savings_percent") or 0.0)
    skipped_pages = int(feedback.get("skipped_pages") or 0)
    scope = str(feedback.get("scope") or "all").strip().lower()
    optimize_url = (
        f"/api/studio/export/optimize_scans?doc_id={encoded_doc}&library={encoded_lib}"
        f"&thumb_page={thumb_page}&page_size={thumb_page_size}"
    )
    open_output_btn = Button(
        "Crea PDF con selezione",
        type="button",
        id="studio-export-open-build",
        cls="app-btn app-btn-accent",
    )

    has_optimize_feedback = optimized_pages > 0 or saved_bytes > 0 or errors > 0
    optimize_feedback_el = (
        Div(
            Span(
                (
                    f"Ultimo: ({'sel.' if scope == 'selected' else 'tutte'}) "
                    f"{optimized_pages} pag., "
                    f"−{_bytes_label(saved_bytes)} ({savings_percent:.1f}%)"
                    + (f", {errors} err." if errors else "")
                    + (f", {skipped_pages} skip." if skipped_pages > 0 else "")
                ),
                cls="text-[11px] text-slate-600 dark:text-slate-300",
            ),
            cls="px-1",
        )
        if has_optimize_feedback
        else None
    )

    return Div(
        Div(
            H3("Workspace Immagini", cls="text-sm font-semibold text-slate-900 dark:text-slate-100"),
            P(
                "Gestisci miniature, scaricamento e ottimizzazione locale.",
                cls="text-xs text-slate-500 dark:text-slate-400",
            ),
            render_export_pages_summary(
                scan_summary=scan_summary,
                thumb_total_pages=thumb_total_pages,
                thumb_page=thumb_page,
                thumb_page_count=thumb_page_count,
                thumb_page_size=thumb_page_size,
            ),
            cls="space-y-2",
        ),
        Div(
            # Row 1: Selection controls
            Div(
                Button(
                    "☑ Tutte",
                    type="button",
                    id="studio-export-pages-select-all",
                    cls="app-btn app-btn-neutral text-xs",
                ),
                Button(
                    "☐ Nessuna",
                    type="button",
                    id="studio-export-pages-clear",
                    cls="app-btn app-btn-neutral text-xs",
                ),
                Div(
                    Input(
                        type="text",
                        id="studio-export-pages-range",
                        placeholder="es. 1-10,12,20-25",
                        cls="app-field text-xs w-36",
                    ),
                    Button(
                        "Applica",
                        type="button",
                        id="studio-export-pages-apply-range",
                        cls="app-btn app-btn-accent text-xs",
                    ),
                    cls="flex items-center gap-1.5",
                ),
                Span(
                    "0 pagine selezionate",
                    cls="studio-export-selected-count text-xs text-slate-500 dark:text-slate-400",
                ),
                cls="flex flex-wrap items-center gap-2",
            ),
            # Row 2: Bulk actions
            Div(
                Span("Azioni:", cls="text-[11px] font-semibold text-slate-600 dark:text-slate-300"),
                Button(
                    Div(
                        Span("⚙ Ottimizza sel."),
                        Span(
                            "…",
                            id="studio-export-optimize-selected-indicator",
                            cls="htmx-indicator text-xs",
                        ),
                        cls="flex items-center gap-1",
                    ),
                    type="button",
                    id="studio-export-optimize-selected-btn",
                    hx_post=optimize_url,
                    hx_vals='{"optimize_scope":"selected"}',
                    hx_include="#studio-export-selected-pages,#studio-export-thumb-page,#studio-export-page-size",
                    hx_indicator="#studio-export-optimize-selected-indicator",
                    hx_target="#studio-export-panel",
                    hx_swap="outerHTML",
                    hx_disabled_elt="this",
                    cls="app-btn app-btn-neutral text-xs",
                ),
                Button(
                    Div(
                        Span("⚙ Ottimizza tutte"),
                        Span(
                            "…",
                            id="studio-export-optimize-all-indicator",
                            cls="htmx-indicator text-xs",
                        ),
                        cls="flex items-center gap-1",
                    ),
                    type="button",
                    id="studio-export-optimize-btn",
                    hx_post=optimize_url,
                    hx_vals='{"optimize_scope":"all"}',
                    hx_include="#studio-export-selected-pages,#studio-export-thumb-page,#studio-export-page-size",
                    hx_indicator="#studio-export-optimize-all-indicator",
                    hx_target="#studio-export-panel",
                    hx_swap="outerHTML",
                    hx_disabled_elt="this",
                    cls="app-btn app-btn-neutral text-xs",
                ),
                cls="flex flex-wrap items-center gap-2",
            ),
            *([] if optimize_feedback_el is None else [optimize_feedback_el]),
            cls=(
                "space-y-2 p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 "
                "bg-white/80 dark:bg-slate-900/80"
            ),
        ),
        Div(
            render_export_thumbnails_loading_shell(
                doc_id=doc_id,
                library=library,
                thumb_page=thumb_page,
                thumb_page_count=thumb_page_count,
                total_pages=thumb_total_pages,
                page_size=thumb_page_size,
            )
            if defer_thumbs_load
            else render_export_thumbnails_panel(
                doc_id=doc_id,
                library=library,
                thumbnails=thumbnails,
                thumb_page=thumb_page,
                thumb_page_count=thumb_page_count,
                total_pages=thumb_total_pages,
                page_size=thumb_page_size,
                page_size_options=thumb_page_size_options,
                has_active_page_actions=has_active_page_actions,
            ),
        ),
        Div(
            Span(
                "0 pagine selezionate",
                id="studio-export-selected-count",
                cls="studio-export-selected-count text-xs text-slate-500 dark:text-slate-400",
            ),
            open_output_btn,
            cls=(
                "flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-xl "
                "border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80"
            ),
        ),
        cls="space-y-3",
    )
