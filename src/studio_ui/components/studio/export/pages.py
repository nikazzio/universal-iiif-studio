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
    files_count = int(scan_summary.get("files_count") or 0)
    bytes_total = int(scan_summary.get("bytes_total") or 0)
    bytes_avg = int(scan_summary.get("bytes_avg") or 0)
    bytes_max = int(scan_summary.get("bytes_max") or 0)
    return Div(
        Span(
            f"{thumb_total_pages} pagine · {files_count} file scaricati · {_bytes_label(bytes_total)} totali",
            cls="text-xs font-mono text-slate-700 dark:text-slate-200",
        ),
        Span(
            (
                f"Media {_bytes_label(bytes_avg)}/file · "
                f"Max {_bytes_label(bytes_max)}/file · "
                f"Miniature: pag. {thumb_page} di {thumb_page_count}, {thumb_page_size}/pag."
            ),
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
        else Span(
            "Nessuna ottimizzazione eseguita.",
            cls="text-[11px] text-slate-400 dark:text-slate-500 px-1",
        )
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
                Span(
                    "0 selezionate",
                    cls="studio-export-selected-count text-xs font-mono text-slate-600 dark:text-slate-300",
                ),
                cls="flex flex-wrap items-center gap-2",
            ),
            # Row 2: Range selection
            Div(
                Span("Range:", cls="text-[11px] text-slate-500 dark:text-slate-400"),
                Input(
                    type="text",
                    id="studio-export-pages-range",
                    placeholder="es. 1-10, 12, 20-25",
                    maxlength="100",
                    cls="app-field text-xs w-36",
                ),
                Button(
                    "Seleziona range",
                    type="button",
                    id="studio-export-pages-apply-range",
                    cls="app-btn app-btn-neutral text-xs",
                ),
                cls="flex flex-wrap items-center gap-1.5",
            ),
            # Row 3: Optimize + feedback
            Div(
                Button(
                    Div(
                        Span("⚙ Ottimizza"),
                        Span(
                            "…",
                            id="studio-export-optimize-indicator",
                            cls="htmx-indicator text-xs",
                        ),
                        cls="flex items-center gap-1",
                    ),
                    type="button",
                    id="studio-export-optimize-btn",
                    hx_post=optimize_url,
                    hx_vals='{"optimize_scope":"selected"}',
                    hx_include=("#studio-export-selected-pages,#studio-export-thumb-page,#studio-export-page-size"),
                    hx_indicator="#studio-export-optimize-indicator",
                    hx_target="#studio-export-panel",
                    hx_swap="outerHTML",
                    hx_disabled_elt="this",
                    cls="app-btn app-btn-neutral text-xs",
                    title="Comprimi i file delle pagine selezionate",
                ),
                optimize_feedback_el,
                cls="flex flex-wrap items-center gap-2",
            ),
            # Legenda pulsanti card
            Div(
                P(
                    Span("⬇ Scarica", cls="font-semibold"),
                    " — riscarica con la strategia progressiva del volume (es. 3000 → 1740 → max, con stitching)",
                    cls="text-[11px] font-mono text-slate-500 dark:text-slate-400",
                ),
                P(
                    Span("⬇ Hi", cls="font-semibold"),
                    " — fetch diretto alla risoluzione massima dichiarata dalla biblioteca, senza fallback",
                    cls="text-[11px] font-mono text-slate-500 dark:text-slate-400",
                ),
                P(
                    Span("⚙ Opt", cls="font-semibold"),
                    " — comprimi il file già scaricato in locale senza perdita di qualità visiva",
                    cls="text-[11px] font-mono text-slate-500 dark:text-slate-400",
                ),
                cls="space-y-0.5",
            ),
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
                "0 selezionate",
                id="studio-export-selected-count",
                cls="studio-export-selected-count text-xs font-mono text-slate-600 dark:text-slate-300",
            ),
            open_output_btn,
            cls=(
                "flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-xl "
                "border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80"
            ),
        ),
        cls="space-y-3",
    )
