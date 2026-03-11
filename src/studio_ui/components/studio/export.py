"""Studio Export tab component (single-item PDF workflow)."""

from __future__ import annotations

import json
from urllib.parse import quote

from fasthtml.common import H3, A, Button, Div, Form, Img, Input, Label, Option, P, Script, Select, Span, Textarea

from studio_ui.components.export import render_export_jobs_panel

_FIELD_CLASS = "app-field"
_LABEL_CLASS = "app-label"


def _bytes_label(size_bytes: int) -> str:
    size = int(size_bytes or 0)
    if size <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    current = float(size)
    for unit in units:
        if current < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(current)} {unit}"
            return f"{current:.1f} {unit}"
        current /= 1024.0
    return f"{size} B"


def render_pdf_inventory_panel(pdf_files: list[dict], *, doc_id: str, library: str, polling: bool = True) -> Div:
    """Render item-level PDF inventory for one manuscript."""
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    attrs = {}
    if polling:
        attrs = {
            "hx_get": f"/api/studio/export/pdf_list?doc_id={encoded_doc}&library={encoded_lib}",
            "hx_trigger": "load, every 12s",
            "hx_swap": "outerHTML",
        }

    rows = []
    for item in pdf_files:
        href = str(item.get("download_url") or "#")
        name = str(item.get("name") or "-")
        kind = str(item.get("kind") or "other")
        size_text = _bytes_label(int(item.get("size_bytes") or 0))

        rows.append(
            Div(
                Div(
                    Span(name, cls="text-xs font-mono text-slate-700 dark:text-slate-200"),
                    Span(kind, cls="text-[11px] text-slate-500 dark:text-slate-400"),
                    cls="grid gap-0.5 min-w-0",
                ),
                Div(
                    Span(size_text, cls="text-xs text-slate-500 dark:text-slate-400"),
                    A(
                        "Apri",
                        href=href,
                        target="_blank",
                        cls="app-btn app-btn-neutral",
                    ),
                    cls="flex items-center gap-2",
                ),
                cls=(
                    "flex items-center justify-between gap-2 border border-slate-200 dark:border-slate-700 "
                    "rounded-xl p-2.5 bg-white dark:bg-slate-900"
                ),
            )
        )

    if not rows:
        rows = [
            Div(
                "Nessun PDF presente nella cartella item/pdf.",
                cls=(
                    "text-xs text-slate-500 dark:text-slate-400 p-2.5 border border-dashed rounded-xl "
                    "dark:border-slate-700"
                ),
            )
        ]

    return Div(
        Div(*rows, cls="space-y-2"),
        id="studio-export-pdf-list",
        **attrs,
    )


def _dims_label(width: int | None, height: int | None, *, fallback: str = "n/a") -> str:
    if not width or not height:
        return fallback
    return f"{int(width)}x{int(height)}"


def _thumb_progress_state(feedback: dict | None) -> tuple[str, int, bool]:
    data = feedback or {}
    state = str(data.get("state") or "idle").strip().lower()
    percent = int(data.get("progress_percent") or (100 if state == "done" else 0))
    percent = max(0, min(percent, 100))
    if state in {"queued", "running"} and percent <= 0:
        percent = 24
    is_busy = state in {"queued", "running"}
    progress_cls = {
        "running": "studio-thumb-progress-active",
        "queued": "studio-thumb-progress-active",
        "done": "studio-thumb-progress-done",
        "error": "studio-thumb-progress-error",
    }.get(state, "studio-thumb-progress-idle")
    return progress_cls, percent, is_busy


def _thumbnail_card_id(page: int) -> str:
    return f"studio-thumb-card-{int(page)}"


def _thumb_live_url(*, doc_id: str, library: str, thumb_page: int, page_size: int) -> str:
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    return (
        f"/api/studio/export/thumbs/live?doc_id={encoded_doc}&library={encoded_lib}"
        f"&thumb_page={thumb_page}&page_size={page_size}"
    )


def render_export_thumbnail_card(
    *,
    item: dict,
    doc_id: str,
    library: str,
    thumb_page: int,
    page_size: int,
    hx_swap_oob: str | None = None,
):
    """Render one export thumbnail card with per-page action controls."""
    page = int(item.get("page") or 0)
    thumb_url = str(item.get("thumb_url") or "")
    local_dims = _dims_label(item.get("local_width"), item.get("local_height"))
    iiif_dims = _dims_label(item.get("iiif_declared_width"), item.get("iiif_declared_height"))
    verified_dims = _dims_label(item.get("verified_direct_width"), item.get("verified_direct_height"))
    local_bytes = int(item.get("local_bytes") or 0)
    highres_feedback = item.get("highres_feedback") or item.get("action_feedback") or {}
    stitch_feedback = item.get("stitch_feedback") or {}
    optimize_feedback = item.get("optimize_feedback") or {}
    hi_progress_cls, hi_progress_percent, hi_busy = _thumb_progress_state(highres_feedback)
    stitch_progress_cls, stitch_progress_percent, stitch_busy = _thumb_progress_state(stitch_feedback)
    opt_progress_cls, opt_progress_percent, opt_busy = _thumb_progress_state(optimize_feedback)
    is_busy = hi_busy or stitch_busy or opt_busy
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    image = (
        Img(
            src=thumb_url,
            loading="lazy",
            decoding="async",
            fetchpriority="low",
            cls=(
                "w-full h-44 object-contain rounded-lg border border-slate-200 dark:border-slate-700 "
                "bg-slate-100 dark:bg-slate-800 p-1"
            ),
        )
        if thumb_url
        else Div(
            "No thumb",
            cls=(
                "w-full h-44 rounded border border-dashed border-slate-300 dark:border-slate-700 "
                "text-xs text-slate-500 dark:text-slate-400 flex items-center justify-center"
            ),
        )
    )

    select_btn = Button(
        Div(
            image,
            Div(
                Span(f"Pag. {page}", cls="text-xs font-semibold text-slate-700 dark:text-slate-200"),
                Span(_bytes_label(local_bytes), cls="text-[11px] text-slate-500 dark:text-slate-400 font-mono"),
                cls="mt-1 flex items-center justify-between gap-2",
            ),
            cls=(
                "studio-export-page-inner p-1.5 rounded-xl border border-slate-200 dark:border-slate-700 "
                "bg-white dark:bg-slate-900 hover:border-slate-400 dark:hover:border-slate-500 transition-colors"
            ),
        ),
        type="button",
        cls=("studio-export-page-card cursor-pointer block rounded border border-transparent focus:outline-none"),
        data_page=str(page),
        aria_pressed="false",
    )
    highres_url = (
        f"/api/studio/export/page_highres?doc_id={encoded_doc}&library={encoded_lib}"
        f"&page={page}&thumb_page={thumb_page}&page_size={page_size}"
    )
    stitch_url = (
        f"/api/studio/export/page_stitch?doc_id={encoded_doc}&library={encoded_lib}"
        f"&page={page}&thumb_page={thumb_page}&page_size={page_size}"
    )
    optimize_url = (
        f"/api/studio/export/page_optimize?doc_id={encoded_doc}&library={encoded_lib}"
        f"&page={page}&thumb_page={thumb_page}&page_size={page_size}"
    )
    card_id = _thumbnail_card_id(page)
    card_attrs = {"id": card_id}
    if hx_swap_oob:
        card_attrs["hx_swap_oob"] = hx_swap_oob
    return Div(
        select_btn,
        Div(
            Div(
                Div(
                    Span(f"Locale {local_dims}", cls="text-[11px] text-slate-500 dark:text-slate-400"),
                    *(
                        [
                            Span(
                                "",
                                cls="inline-block h-2 w-2 rounded-full bg-emerald-500",
                                title=f"Dimensione verificata via download diretto: {verified_dims}",
                                aria_label=f"Dimensione verificata via download diretto: {verified_dims}",
                            )
                        ]
                        if verified_dims != "n/a"
                        else []
                    ),
                    cls="flex items-center gap-1.5",
                ),
                Span(f"Remote {iiif_dims}", cls="text-[11px] text-slate-500 dark:text-slate-400"),
                cls="grid gap-0.5",
            ),
            Div(
                Button(
                    Div(
                        Span("⬇ Hi", cls="text-[12px] font-semibold"),
                        Span(
                            "",
                            id=f"studio-thumb-progress-hi-{page}",
                            cls=f"studio-thumb-progress {hi_progress_cls}",
                            style=f"--progress:{hi_progress_percent}%;",
                            aria_hidden="true",
                        ),
                        cls="flex items-center justify-between gap-2",
                    ),
                    type="button",
                    hx_post=highres_url,
                    hx_include="#studio-export-thumb-page,#studio-export-page-size",
                    hx_indicator=f"#studio-thumb-progress-hi-{page}",
                    hx_target=f"#{card_id}",
                    hx_swap="outerHTML",
                    disabled=is_busy,
                    cls="app-btn app-btn-neutral studio-thumb-highres-btn",
                    data_page=str(page),
                    title="Riscarica la pagina con fetch diretto max, senza fallback stitching",
                ),
                Button(
                    Div(
                        Span("🧩 Std", cls="text-[12px] font-semibold"),
                        Span(
                            "",
                            id=f"studio-thumb-progress-stitch-{page}",
                            cls=f"studio-thumb-progress {stitch_progress_cls}",
                            style=f"--progress:{stitch_progress_percent}%;",
                            aria_hidden="true",
                        ),
                        cls="flex items-center justify-between gap-2",
                    ),
                    type="button",
                    hx_post=stitch_url,
                    hx_include="#studio-export-thumb-page,#studio-export-page-size",
                    hx_indicator=f"#studio-thumb-progress-stitch-{page}",
                    hx_target=f"#{card_id}",
                    hx_swap="outerHTML",
                    disabled=is_busy,
                    cls="app-btn app-btn-neutral studio-thumb-stitch-btn",
                    data_page=str(page),
                    title=(
                        "Riscarica la pagina usando la strategia standard del volume "
                        "(es. 3000 -> 1740 -> max, con fallback stitch se serve)"
                    ),
                ),
                Button(
                    Div(
                        Span("⚙ Opt", cls="text-[12px] font-semibold"),
                        Span(
                            "",
                            id=f"studio-thumb-progress-opt-{page}",
                            cls=f"studio-thumb-progress {opt_progress_cls}",
                            style=f"--progress:{opt_progress_percent}%;",
                            aria_hidden="true",
                        ),
                        cls="flex items-center justify-between gap-2",
                    ),
                    type="button",
                    hx_post=optimize_url,
                    hx_include="#studio-export-thumb-page,#studio-export-page-size",
                    hx_indicator=f"#studio-thumb-progress-opt-{page}",
                    hx_target=f"#{card_id}",
                    hx_swap="outerHTML",
                    disabled=is_busy,
                    cls="app-btn app-btn-neutral studio-thumb-opt-btn",
                    data_page=str(page),
                    title="Ottimizza solo questa pagina",
                ),
                cls="studio-thumb-action",
            ),
            cls="studio-thumb-meta",
        ),
        cls="studio-thumb-card studio-thumb-shell",
        **card_attrs,
    )


def render_export_thumbs_poller(
    *,
    doc_id: str,
    library: str,
    thumb_page: int,
    page_size: int,
    has_active_page_actions: bool,
    hx_swap_oob: str | None = None,
) -> Div:
    """Render the hidden live poller used for per-card export updates."""
    attrs: dict[str, str] = {"id": "studio-export-live-state-poller", "cls": "hidden"}
    if has_active_page_actions:
        attrs.update(
            {
                "hx_get": _thumb_live_url(doc_id=doc_id, library=library, thumb_page=thumb_page, page_size=page_size),
                "hx_trigger": "load, every 2s",
                "hx_swap": "none",
            }
        )
    if hx_swap_oob:
        attrs["hx_swap_oob"] = hx_swap_oob
    return Div("", **attrs)


def render_export_thumbnails_loading_shell(
    *,
    doc_id: str,
    library: str,
    thumb_page: int,
    thumb_page_count: int,
    total_pages: int,
    page_size: int,
) -> Div:
    """Render a lightweight placeholder while the visible thumbnails page is generated."""
    return Div(
        Div(
            Span(
                f"Miniature: pagina {thumb_page}/{thumb_page_count} · {total_pages} pagine totali",
                cls="text-xs text-slate-500 dark:text-slate-400",
            ),
            Span(
                "Caricamento iniziale",
                cls="text-[11px] font-medium text-slate-500 dark:text-slate-400",
            ),
            cls="flex items-center justify-between mb-2",
        ),
        Div(
            Div(
                Div("", cls="h-4 w-24 rounded bg-slate-200/80 dark:bg-slate-700/70 animate-pulse"),
                Div("", cls="h-44 rounded-lg bg-slate-200/70 dark:bg-slate-800/70 animate-pulse"),
                Div("", cls="h-8 rounded-lg bg-slate-200/60 dark:bg-slate-800/60 animate-pulse"),
                cls="space-y-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-3",
            ),
            Div(
                "Sto preparando le miniature della pagina visibile. Le thumb vengono create on-demand "
                "alla prima apertura e poi riusate dalla cache finché il file sorgente non cambia.",
                cls="text-xs text-slate-500 dark:text-slate-400",
            ),
            cls="space-y-3",
        ),
        id="studio-export-thumbs-slot",
        hx_get=_thumb_page_url(doc_id=doc_id, library=library, thumb_page=thumb_page, page_size=page_size),
        hx_trigger="load",
        hx_swap="outerHTML",
        **{
            "data-thumb-page": str(thumb_page),
            "data-thumb-pages": str(thumb_page_count),
            "data-page-size": str(page_size),
            "data-thumbs-endpoint": _thumb_base_url(doc_id=doc_id, library=library),
        },
    )


def _thumb_page_url(*, doc_id: str, library: str, thumb_page: int, page_size: int) -> str:
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    return (
        f"/api/studio/export/thumbs?doc_id={encoded_doc}&library={encoded_lib}"
        f"&thumb_page={thumb_page}&page_size={page_size}"
    )


def _thumb_base_url(*, doc_id: str, library: str) -> str:
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    return f"/api/studio/export/thumbs?doc_id={encoded_doc}&library={encoded_lib}"


def render_export_thumbnails_panel(
    *,
    doc_id: str,
    library: str,
    thumbnails: list[dict],
    thumb_page: int,
    thumb_page_count: int,
    total_pages: int,
    page_size: int,
    page_size_options: list[int],
    has_active_page_actions: bool = False,
) -> Div:
    """Render one paginated thumbnails slice for export selection."""
    cards = [
        render_export_thumbnail_card(
            item=item,
            doc_id=doc_id,
            library=library,
            thumb_page=thumb_page,
            page_size=page_size,
        )
        for item in thumbnails
    ]
    if not cards:
        cards = [Div("Nessuna pagina disponibile in scans/.", cls="text-sm text-slate-500 dark:text-slate-400")]

    prev_page = max(1, int(thumb_page) - 1)
    next_page = min(int(thumb_page_count), int(thumb_page) + 1)
    is_first = int(thumb_page) <= 1
    is_last = int(thumb_page) >= int(thumb_page_count)

    prev_attrs = (
        {}
        if is_first
        else {
            "hx_get": _thumb_page_url(doc_id=doc_id, library=library, thumb_page=prev_page, page_size=page_size),
            "hx_target": "#studio-export-thumbs-slot",
            "hx_swap": "outerHTML",
        }
    )
    next_attrs = (
        {}
        if is_last
        else {
            "hx_get": _thumb_page_url(doc_id=doc_id, library=library, thumb_page=next_page, page_size=page_size),
            "hx_target": "#studio-export-thumbs-slot",
            "hx_swap": "outerHTML",
        }
    )

    poller = render_export_thumbs_poller(
        doc_id=doc_id,
        library=library,
        thumb_page=thumb_page,
        page_size=page_size,
        has_active_page_actions=has_active_page_actions,
    )

    return Div(
        Div(
            Span(
                f"Miniature: pagina {thumb_page}/{thumb_page_count} · {total_pages} pagine totali",
                cls="text-xs text-slate-500 dark:text-slate-400",
            ),
            Div(
                Select(
                    *[
                        Option(
                            f"{size} / pagina",
                            value=str(size),
                            selected=int(size) == int(page_size),
                        )
                        for size in page_size_options
                    ],
                    id="studio-export-thumb-size-select",
                    name="page_size",
                    hx_get=f"{_thumb_base_url(doc_id=doc_id, library=library)}&thumb_page=1",
                    hx_trigger="change",
                    hx_target="#studio-export-thumbs-slot",
                    hx_swap="outerHTML",
                    cls="app-field w-32 text-xs",
                ),
                Button(
                    "◀",
                    type="button",
                    disabled=is_first,
                    cls="app-btn app-btn-neutral disabled:opacity-40",
                    **prev_attrs,
                ),
                Button(
                    "▶",
                    type="button",
                    disabled=is_last,
                    cls="app-btn app-btn-neutral disabled:opacity-40",
                    **next_attrs,
                ),
                cls="flex items-center gap-2",
            ),
            cls="flex items-center justify-between mb-2",
        ),
        Div(*cards, cls="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-3"),
        poller,
        id="studio-export-thumbs-slot",
        **{
            "data-thumb-page": str(thumb_page),
            "data-thumb-pages": str(thumb_page_count),
            "data-page-size": str(page_size),
            "data-thumbs-endpoint": _thumb_base_url(doc_id=doc_id, library=library),
        },
    )


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
    before_bytes = int(feedback.get("bytes_before") or 0)
    after_bytes = int(feedback.get("bytes_after") or 0)
    savings_percent = float(feedback.get("savings_percent") or 0.0)
    optimized_at = str(feedback.get("optimized_at") or "")
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

    return Div(
        Div(
            H3("Workspace Immagini", cls="text-sm font-semibold text-slate-900 dark:text-slate-100"),
            P(
                (
                    "Gestisci miniature, high-res e ottimizzazione locale. "
                    "Le miniature della pagina visibile vengono create on-demand al primo accesso."
                ),
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
            Div(
                H3("Ottimizzazione Scans Locali", cls="text-sm font-semibold text-slate-900 dark:text-slate-100"),
                P(
                    "Riduci il peso dei file locali. Usa selezione o tutto l'item.",
                    cls="text-xs text-slate-500 dark:text-slate-400",
                ),
                cls="space-y-1",
            ),
            Div(
                Button(
                    Div(
                        Span("Ottimizza selezione"),
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
                    cls="app-btn app-btn-neutral",
                ),
                Button(
                    Div(
                        Span("Ottimizza tutte"),
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
                    cls="app-btn app-btn-neutral",
                ),
                cls="flex flex-wrap items-center gap-2",
            ),
            (
                Div(
                    Span(
                        (
                            f"Ultimo run: ({'selezione' if scope == 'selected' else 'globale'}) "
                            f"{optimized_pages} pagine ottimizzate, "
                            f"risparmio {_bytes_label(saved_bytes)} ({savings_percent:.2f}%), errori {errors}."
                            + (f" Skippate {skipped_pages}." if skipped_pages > 0 else "")
                        ),
                        cls="text-xs text-slate-700 dark:text-slate-200",
                    ),
                    Span(
                        f"Prima {_bytes_label(before_bytes)} · Dopo {_bytes_label(after_bytes)}"
                        + (f" · {optimized_at}" if optimized_at else ""),
                        cls="text-[11px] text-slate-500 dark:text-slate-400",
                    ),
                    cls=(
                        "flex flex-col gap-1 p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 "
                        "bg-white dark:bg-slate-900"
                    ),
                )
                if optimized_pages > 0 or saved_bytes > 0 or errors > 0
                else Div(
                    "Nessuna ottimizzazione registrata per questo item.",
                    cls="text-xs text-slate-500 dark:text-slate-400",
                ),
            ),
            cls=("space-y-2 p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"),
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


def render_studio_export_tab(
    *,
    doc_id: str,
    library: str,
    thumbnails: list[dict],
    thumb_page: int,
    thumb_page_count: int,
    thumb_total_pages: int,
    thumb_page_size: int,
    thumb_page_size_options: list[int],
    available_pages: list[int],
    selected_pages_raw: str,
    pdf_files: list[dict],
    jobs: list[dict],
    has_active_jobs: bool,
    has_active_page_actions: bool,
    export_defaults: dict,
    selected_subtab: str = "pages",
    selected_build_subtab: str = "generate",
    scan_summary: dict | None = None,
    optimization_meta: dict | None = None,
    optimize_feedback: dict | None = None,
    defer_thumbs_load: bool = False,
) -> Div:
    """Render the Studio Export tab content."""
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")

    jobs_panel = render_export_jobs_panel(
        jobs,
        polling=True,
        hx_url=f"/api/studio/export/jobs?doc_id={encoded_doc}&library={encoded_lib}",
        panel_id="studio-export-jobs",
        has_active_jobs=has_active_jobs,
        poll_interval_seconds=12,
    )

    default_format = str(export_defaults.get("format") or "pdf_images")
    if default_format not in {"pdf_images", "pdf_searchable", "pdf_facing"}:
        default_format = "pdf_images"

    default_compression = str(export_defaults.get("compression") or "Standard")
    if default_compression not in {"High-Res", "Standard", "Light"}:
        default_compression = "Standard"

    default_include_cover = bool(export_defaults.get("include_cover", True))
    default_include_colophon = bool(export_defaults.get("include_colophon", True))
    default_curator = str(export_defaults.get("curator") or "")
    default_description = str(export_defaults.get("description") or "")
    default_logo_path = str(export_defaults.get("logo_path") or "")
    default_profile_name = str(export_defaults.get("profile_name") or "balanced")
    profile_catalog = export_defaults.get("profile_catalog") or {}
    profile_options: list[tuple[str, str]] = []
    if isinstance(profile_catalog, dict):
        for profile_key, payload in sorted(profile_catalog.items()):
            if isinstance(payload, dict):
                label = str(payload.get("label") or profile_key)
                profile_options.append((str(profile_key), label))
    if not profile_options:
        profile_options = [("balanced", "Balanced")]

    default_image_source_mode = str(export_defaults.get("image_source_mode") or "local_balanced")
    default_image_max_edge = int(export_defaults.get("image_max_long_edge_px") or 0)
    default_jpeg_quality = int(export_defaults.get("jpeg_quality") or 82)
    default_force_remote_refetch = bool(export_defaults.get("force_remote_refetch", False))
    default_cleanup_temp = bool(export_defaults.get("cleanup_temp_after_export", True))
    default_parallel_fetch = int(export_defaults.get("max_parallel_page_fetch") or 2)

    description_rows_raw = export_defaults.get("description_rows", 3)
    try:
        description_rows = int(description_rows_raw)
    except (TypeError, ValueError):
        description_rows = 3
    description_rows = max(2, min(description_rows, 8))

    active_subtab = selected_subtab if selected_subtab in {"build", "pages", "jobs"} else "pages"
    active_build_subtab = selected_build_subtab if selected_build_subtab in {"generate", "files"} else "generate"
    scan_summary = scan_summary or {}
    optimization_meta = optimization_meta or {}
    optimize_feedback = optimize_feedback or {}
    available_total = len(available_pages)

    return Div(
        Div(
            Input(type="hidden", name="thumb_page", id="studio-export-thumb-page", value=str(thumb_page)),
            Input(type="hidden", name="page_size", id="studio-export-page-size", value=str(thumb_page_size)),
            Input(type="hidden", name="subtab", id="studio-export-subtab-state", value=active_subtab),
            Input(type="hidden", name="build_subtab", id="studio-export-build-subtab-state", value=active_build_subtab),
            Input(type="hidden", name="selection_mode", id="studio-export-selection-mode", value="all"),
            Input(
                type="hidden",
                name="selected_pages",
                id="studio-export-selected-pages",
                value=selected_pages_raw,
            ),
            Input(
                type="hidden",
                id="studio-export-available-pages",
                value=",".join(str(page) for page in available_pages),
            ),
            cls="hidden",
        ),
        Div(
            Div(
                (
                    _render_export_pages_subtab(
                        doc_id=doc_id,
                        library=library,
                        scan_summary=scan_summary,
                        optimization_meta=optimization_meta,
                        optimize_feedback=optimize_feedback,
                        thumbnails=thumbnails,
                        thumb_page=thumb_page,
                        thumb_page_count=thumb_page_count,
                        thumb_total_pages=thumb_total_pages,
                        thumb_page_size=thumb_page_size,
                        thumb_page_size_options=thumb_page_size_options,
                        has_active_page_actions=has_active_page_actions,
                        defer_thumbs_load=defer_thumbs_load,
                    )
                    if active_subtab == "pages"
                    else ""
                ),
                id="studio-export-subtab-pages",
                cls="space-y-2" if active_subtab == "pages" else "hidden space-y-2",
            ),
            (
                Div(
                    Div(
                        H3("Output PDF", cls="text-sm font-semibold text-slate-900 dark:text-slate-100"),
                        P(
                            "Generazione PDF con selezione pagine, template e parametri.",
                            cls="text-xs text-slate-500 dark:text-slate-400",
                        ),
                        cls="space-y-1",
                    ),
                    Div(
                        Button(
                            "Generazione",
                            type="button",
                            id="studio-export-build-tab-generate",
                            cls="app-btn app-btn-accent"
                            if active_build_subtab == "generate"
                            else "app-btn app-btn-neutral",
                            aria_pressed="true" if active_build_subtab == "generate" else "false",
                        ),
                        Button(
                            "PDF generati",
                            type="button",
                            id="studio-export-build-tab-files",
                            cls="app-btn app-btn-accent"
                            if active_build_subtab == "files"
                            else "app-btn app-btn-neutral",
                            aria_pressed="true" if active_build_subtab == "files" else "false",
                        ),
                        cls="flex flex-wrap items-center gap-2",
                    ),
                    Form(
                        Input(type="hidden", name="doc_id", value=doc_id),
                        Input(type="hidden", name="library", value=library),
                        Input(
                            type="hidden",
                            id="studio-export-profiles-json",
                            value=json.dumps(profile_catalog, separators=(",", ":")),
                        ),
                        Input(
                            type="hidden",
                            name="include_cover",
                            id="studio-export-include-cover-hidden",
                            value="1" if default_include_cover else "0",
                        ),
                        Input(
                            type="hidden",
                            name="include_colophon",
                            id="studio-export-include-colophon-hidden",
                            value="1" if default_include_colophon else "0",
                        ),
                        Input(
                            type="hidden",
                            name="force_remote_refetch",
                            id="studio-export-force-remote-hidden",
                            value="1" if default_force_remote_refetch else "0",
                        ),
                        Input(
                            type="hidden",
                            name="cleanup_temp_after_export",
                            id="studio-export-cleanup-temp-hidden",
                            value="1" if default_cleanup_temp else "0",
                        ),
                        Div(
                            Div(
                                H3(
                                    "Selezione Pagine",
                                    cls="text-sm font-semibold text-slate-900 dark:text-slate-100",
                                ),
                                P(
                                    "Seleziona le pagine da includere nel PDF.",
                                    cls="text-xs text-slate-500 dark:text-slate-400",
                                ),
                                cls="space-y-1",
                            ),
                            Div(
                                Button(
                                    "Seleziona pagine singolarmente",
                                    type="button",
                                    id="studio-export-open-pages-custom",
                                    cls="app-btn app-btn-neutral",
                                ),
                                Div(
                                    Button(
                                        "Tutte",
                                        type="button",
                                        id="studio-export-scope-all",
                                        cls="app-btn app-btn-neutral",
                                        aria_pressed="true",
                                    ),
                                    Button(
                                        "Custom",
                                        type="button",
                                        id="studio-export-scope-custom",
                                        cls="app-btn app-btn-neutral",
                                        aria_pressed="false",
                                    ),
                                    cls="flex items-center gap-2",
                                ),
                                cls="flex flex-wrap items-center justify-between gap-2",
                            ),
                            Div(
                                Label("Range manuale pagine", for_="studio-export-range", cls=_LABEL_CLASS),
                                Div(
                                    Input(
                                        type="text",
                                        id="studio-export-range",
                                        placeholder="es. 1-10,12,20-25",
                                        cls=f"flex-1 {_FIELD_CLASS}",
                                    ),
                                    Button(
                                        "Applica",
                                        type="button",
                                        id="studio-export-apply-range",
                                        cls="app-btn app-btn-accent",
                                    ),
                                    cls="flex flex-wrap items-center gap-2",
                                ),
                                Div(
                                    Button(
                                        "Seleziona tutte",
                                        type="button",
                                        id="studio-export-select-all",
                                        cls="app-btn app-btn-neutral",
                                    ),
                                    Button(
                                        "Deseleziona",
                                        type="button",
                                        id="studio-export-clear",
                                        cls="app-btn app-btn-neutral",
                                    ),
                                    Span(
                                        "0 pagine selezionate",
                                        cls="studio-export-selected-count text-xs text-slate-600 dark:text-slate-300",
                                    ),
                                    Span(
                                        f"{available_total} pagine disponibili",
                                        cls="text-[11px] text-slate-500 dark:text-slate-400",
                                    ),
                                    cls="flex flex-wrap items-center gap-2 mt-2",
                                ),
                                cls="space-y-2",
                            ),
                            cls=("space-y-2 pb-3 border-b border-slate-200 dark:border-slate-700"),
                        ),
                        Div(
                            H3(
                                "Template e Parametri Export",
                                cls="text-sm font-semibold text-slate-900 dark:text-slate-100",
                            ),
                            P(
                                "Profilo, formato PDF, sorgente immagini e metadati copertina.",
                                cls="text-xs text-slate-500 dark:text-slate-400",
                            ),
                            cls="space-y-1",
                        ),
                        Div(
                            Span("Profilo PDF", cls=f"{_LABEL_CLASS} shrink-0"),
                            Select(
                                *[
                                    Option(label, value=key, selected=key == default_profile_name)
                                    for key, label in profile_options
                                ],
                                id="studio-export-profile",
                                name="pdf_profile",
                                cls=f"{_FIELD_CLASS} flex-1 min-w-0",
                            ),
                            A(
                                "Gestisci profili",
                                href="/settings?tab=pdf",
                                cls="app-btn app-btn-neutral whitespace-nowrap",
                            ),
                            cls="flex flex-col md:flex-row md:items-center gap-2",
                        ),
                        Div(
                            Button(
                                "Personalizza override per questo job",
                                type="button",
                                id="studio-export-overrides-toggle",
                                cls="app-btn app-btn-neutral",
                                aria_expanded="false",
                            ),
                            P(
                                "Apri override solo quando devi uscire dal template standard.",
                                cls="text-xs text-slate-500 dark:text-slate-400",
                            ),
                            cls="space-y-1",
                        ),
                        Div(
                            Div(
                                Div(
                                    Label("Formato", for_="studio-export-format", cls=_LABEL_CLASS),
                                    Select(
                                        Option(
                                            "PDF (solo immagini)",
                                            value="pdf_images",
                                            selected=default_format == "pdf_images",
                                        ),
                                        Option(
                                            "PDF ricercabile",
                                            value="pdf_searchable",
                                            selected=default_format == "pdf_searchable",
                                        ),
                                        Option(
                                            "PDF testo a fronte",
                                            value="pdf_facing",
                                            selected=default_format == "pdf_facing",
                                        ),
                                        id="studio-export-format",
                                        name="export_format",
                                        cls=_FIELD_CLASS,
                                    ),
                                    cls="space-y-1",
                                ),
                                Div(
                                    Label("Compressione", for_="studio-export-compression", cls=_LABEL_CLASS),
                                    Select(
                                        Option(
                                            "High-Res", value="High-Res", selected=default_compression == "High-Res"
                                        ),
                                        Option(
                                            "Standard", value="Standard", selected=default_compression == "Standard"
                                        ),
                                        Option("Light", value="Light", selected=default_compression == "Light"),
                                        id="studio-export-compression",
                                        name="compression",
                                        cls=_FIELD_CLASS,
                                    ),
                                    cls="space-y-1",
                                ),
                                cls="grid grid-cols-1 md:grid-cols-2 gap-3",
                            ),
                            Div(
                                Label(
                                    Input(
                                        type="checkbox",
                                        id="studio-export-include-cover-checkbox",
                                        value="1",
                                        checked=default_include_cover,
                                        cls="app-check",
                                    ),
                                    Span("Includi copertina", cls="text-sm text-slate-700 dark:text-slate-300"),
                                    cls="flex items-center gap-2",
                                ),
                                Label(
                                    Input(
                                        type="checkbox",
                                        id="studio-export-include-colophon-checkbox",
                                        value="1",
                                        checked=default_include_colophon,
                                        cls="app-check",
                                    ),
                                    Span("Includi colophon", cls="text-sm text-slate-700 dark:text-slate-300"),
                                    cls="flex items-center gap-2",
                                ),
                                Label(
                                    Input(
                                        type="checkbox",
                                        id="studio-export-force-remote-checkbox",
                                        value="1",
                                        checked=default_force_remote_refetch,
                                        cls="app-check",
                                    ),
                                    Span("Forza refetch remoto", cls="text-sm text-slate-700 dark:text-slate-300"),
                                    cls="flex items-center gap-2",
                                ),
                                Label(
                                    Input(
                                        type="checkbox",
                                        id="studio-export-cleanup-temp-checkbox",
                                        value="1",
                                        checked=default_cleanup_temp,
                                        cls="app-check",
                                    ),
                                    Span("Cleanup temp high-res", cls="text-sm text-slate-700 dark:text-slate-300"),
                                    cls="flex items-center gap-2",
                                ),
                                cls="flex flex-wrap gap-4",
                            ),
                            Div(
                                Div(
                                    Label("Sorgente immagini", for_="studio-export-source-mode", cls=_LABEL_CLASS),
                                    Select(
                                        Option(
                                            "PDF da Locale (bilanciato)",
                                            value="local_balanced",
                                            selected=default_image_source_mode == "local_balanced",
                                        ),
                                        Option(
                                            "PDF da Locale (high-res)",
                                            value="local_highres",
                                            selected=default_image_source_mode == "local_highres",
                                        ),
                                        Option(
                                            "PDF da Remoto temporaneo",
                                            value="remote_highres_temp",
                                            selected=default_image_source_mode == "remote_highres_temp",
                                        ),
                                        id="studio-export-source-mode",
                                        name="image_source_mode",
                                        cls=_FIELD_CLASS,
                                    ),
                                    cls="space-y-1",
                                ),
                                Div(
                                    Label("Max long edge (px)", for_="studio-export-max-edge", cls=_LABEL_CLASS),
                                    Input(
                                        type="number",
                                        id="studio-export-max-edge",
                                        name="image_max_long_edge_px",
                                        value=str(default_image_max_edge),
                                        min="0",
                                        step="1",
                                        cls=_FIELD_CLASS,
                                    ),
                                    cls="space-y-1",
                                ),
                                Div(
                                    Label("JPEG quality", for_="studio-export-jpeg-quality", cls=_LABEL_CLASS),
                                    Input(
                                        type="number",
                                        id="studio-export-jpeg-quality",
                                        name="image_jpeg_quality",
                                        value=str(default_jpeg_quality),
                                        min="40",
                                        max="100",
                                        step="1",
                                        cls=_FIELD_CLASS,
                                    ),
                                    cls="space-y-1",
                                ),
                                Div(
                                    Label("Parallel fetch", for_="studio-export-parallel", cls=_LABEL_CLASS),
                                    Input(
                                        type="number",
                                        id="studio-export-parallel",
                                        name="max_parallel_page_fetch",
                                        value=str(default_parallel_fetch),
                                        min="1",
                                        max="8",
                                        step="1",
                                        cls=_FIELD_CLASS,
                                    ),
                                    cls="space-y-1",
                                ),
                                cls="grid grid-cols-1 md:grid-cols-2 gap-3",
                            ),
                            Div(
                                Div(
                                    Label("Curatore", for_="studio-export-curator", cls=_LABEL_CLASS),
                                    Input(
                                        type="text",
                                        id="studio-export-curator",
                                        name="cover_curator",
                                        value=default_curator,
                                        placeholder="es. Team Digital Humanities",
                                        cls=_FIELD_CLASS,
                                    ),
                                    cls="space-y-1",
                                ),
                                Div(
                                    Label("Logo copertina (path)", for_="studio-export-logo", cls=_LABEL_CLASS),
                                    Input(
                                        type="text",
                                        id="studio-export-logo",
                                        name="cover_logo_path",
                                        value=default_logo_path,
                                        placeholder="es. assets/logo.png",
                                        cls=_FIELD_CLASS,
                                    ),
                                    cls="space-y-1",
                                ),
                                Div(
                                    Label("Descrizione", for_="studio-export-description", cls=_LABEL_CLASS),
                                    Textarea(
                                        default_description,
                                        id="studio-export-description",
                                        name="cover_description",
                                        rows=description_rows,
                                        cls=_FIELD_CLASS,
                                    ),
                                    cls="space-y-1 md:col-span-2",
                                ),
                                cls="grid grid-cols-1 md:grid-cols-2 gap-3",
                            ),
                            id="studio-export-overrides-panel",
                            cls=("hidden space-y-3 mt-1 pt-3 border-t border-slate-200 dark:border-slate-700"),
                        ),
                        Div(
                            Div(
                                Span(
                                    "Default: tutte le pagine. In modalità custom usa range o selezione singola.",
                                    cls="text-xs text-slate-500 dark:text-slate-400",
                                ),
                                Span(
                                    "0 pagine selezionate",
                                    cls="studio-export-selected-count text-xs text-slate-600 dark:text-slate-300",
                                ),
                                cls="space-y-1",
                            ),
                            Button(
                                "Crea PDF",
                                type="submit",
                                form="studio-export-form",
                                data_export_submit="1",
                                cls="app-btn app-btn-accent",
                            ),
                            cls=(
                                "studio-export-actionbar flex flex-wrap items-center justify-between gap-3 "
                                "pt-3 border-t border-slate-200 dark:border-slate-700"
                            ),
                        ),
                        hx_post="/api/studio/export/start",
                        hx_trigger="submit",
                        hx_include=(
                            "#studio-export-thumb-page,#studio-export-page-size,#studio-export-subtab-state,"
                            "#studio-export-selection-mode,#studio-export-selected-pages,"
                            "#studio-export-build-subtab-state"
                        ),
                        hx_target="#studio-export-panel",
                        hx_swap="outerHTML",
                        id="studio-export-form",
                        cls=(
                            "studio-export-build-generate-block space-y-4"
                            + (" hidden" if active_build_subtab != "generate" else "")
                        ),
                    ),
                    Div(
                        H3("PDF Generati", cls="text-sm font-semibold text-slate-900 dark:text-slate-100"),
                        P(
                            "Elenco di controllo file presenti in item/pdf.",
                            cls="text-xs text-slate-500 dark:text-slate-400",
                        ),
                        render_pdf_inventory_panel(
                            pdf_files,
                            doc_id=doc_id,
                            library=library,
                            polling=has_active_jobs,
                        ),
                        cls="studio-export-build-files-block space-y-2"
                        + ("" if active_build_subtab == "files" else " hidden"),
                    ),
                    id="studio-export-subtab-build",
                    cls="space-y-3",
                )
                if active_subtab == "build"
                else Div("", id="studio-export-subtab-build", cls="hidden")
            ),
            (
                Div(
                    Div(
                        H3("Job", cls="text-sm font-semibold text-slate-900 dark:text-slate-100"),
                        P(
                            "Coda job generale (export e processi futuri).",
                            cls="text-xs text-slate-500 dark:text-slate-400",
                        ),
                        cls="space-y-1",
                    ),
                    jobs_panel,
                    id="studio-export-subtab-jobs",
                    cls="space-y-3",
                )
                if active_subtab == "jobs"
                else Div("", id="studio-export-subtab-jobs", cls="hidden")
            ),
            cls=(
                "space-y-3 rounded-2xl border border-slate-200 dark:border-slate-700 "
                "bg-slate-50 dark:bg-slate-900/70 p-3"
            ),
        ),
        Script(
            """
            (function() {
                function parseSelection(text) {
                    const out = new Set();
                    const raw = (text || '').trim();
                    if (!raw) return out;
                    raw.split(',').forEach((token) => {
                        const part = token.trim();
                        if (!part) return;
                        if (!part.includes('-')) {
                            const n = parseInt(part, 10);
                            if (!Number.isNaN(n) && n > 0) out.add(n);
                            return;
                        }
                        const [a, b] = part.split('-', 2).map(v => parseInt(v.trim(), 10));
                        if (Number.isNaN(a) || Number.isNaN(b) || a <= 0 || b <= 0) return;
                        const start = Math.min(a, b);
                        const end = Math.max(a, b);
                        for (let i = start; i <= end; i += 1) out.add(i);
                    });
                    return out;
                }

                function serializeSelection(setObj) {
                    return Array.from(setObj).sort((a, b) => a - b).join(',');
                }

                function updateThumbVisual(card, isSelected) {
                    if (!card) return;
                    card.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
                    if (isSelected) {
                        card.classList.add(
                            'studio-export-page-card-selected'
                        );
                    } else {
                        card.classList.remove(
                            'studio-export-page-card-selected'
                        );
                    }
                }

                function updateSelectedCount(panel) {
                    const hidden = panel.querySelector('#studio-export-selected-pages');
                    if (!hidden) return;
                    const selected = parseSelection(hidden.value);
                    const counters = panel.querySelectorAll('.studio-export-selected-count');
                    counters.forEach((node) => {
                        node.textContent = `${selected.size} pagine selezionate`;
                    });
                }

                function availablePages(panel) {
                    const availableInput = panel.querySelector('#studio-export-available-pages');
                    return parseSelection(availableInput ? availableInput.value : '');
                }

                function syncSelectionStore(panel) {
                    const hidden = panel.querySelector('#studio-export-selected-pages');
                    const selectionModeHidden = panel.querySelector('#studio-export-selection-mode');
                    if (!hidden) return;
                    const selected = parseSelection(hidden.value);
                    const available = availablePages(panel);
                    if (selectionModeHidden) {
                        selectionModeHidden.value = (
                            selected.size > 0 && available.size > 0 && selected.size < available.size
                        )
                            ? 'custom'
                            : 'all';
                    }
                    panel.dataset.exportScope = (selectionModeHidden && selectionModeHidden.value) || 'all';
                    updateSelectedCount(panel);
                }

                function applySelectionToVisible(panel) {
                    const hidden = panel.querySelector('#studio-export-selected-pages');
                    if (!hidden) return;
                    const selected = parseSelection(hidden.value);
                    const cards = panel.querySelectorAll('.studio-export-page-card');
                    cards.forEach((card) => {
                        const page = parseInt(card.dataset.page || '', 10);
                        updateThumbVisual(card, !Number.isNaN(page) && selected.has(page));
                    });
                }

                function bindThumbCards(panel, onSelectionChange) {
                    const hidden = panel.querySelector('#studio-export-selected-pages');
                    if (!hidden) return;

                    const cards = panel.querySelectorAll('.studio-export-page-card');
                    cards.forEach((card) => {
                        const pageNum = parseInt(card.dataset.page || '', 10);
                        const selected = parseSelection(hidden.value);
                        updateThumbVisual(card, !Number.isNaN(pageNum) && selected.has(pageNum));

                        if (card.dataset.bound === '1') return;
                        card.dataset.bound = '1';
                        card.addEventListener('click', () => {
                            const page = parseInt(card.dataset.page || '', 10);
                            if (Number.isNaN(page)) return;

                            const current = parseSelection(hidden.value);
                            if (current.has(page)) current.delete(page);
                            else current.add(page);
                            hidden.value = serializeSelection(current);
                            if (onSelectionChange) onSelectionChange(current);
                            updateThumbVisual(card, current.has(page));
                            syncSelectionStore(panel);
                        });
                    });
                }

                function initStudioExport() {
                    const panel = document.getElementById('studio-export-panel');
                    if (!panel) return;

                    const form = panel.querySelector('#studio-export-form');
                    const thumbPageHidden = panel.querySelector('#studio-export-thumb-page');
                    const pageSizeHidden = panel.querySelector('#studio-export-page-size');
                    const subtabStateHidden = panel.querySelector('#studio-export-subtab-state');
                    const selectionModeHidden = panel.querySelector('#studio-export-selection-mode');
                    const hidden = panel.querySelector('#studio-export-selected-pages');
                    const availableInput = panel.querySelector('#studio-export-available-pages');
                    const rangeInput = panel.querySelector('#studio-export-range');
                    const rangeBtn = panel.querySelector('#studio-export-apply-range');
                    const allBtn = panel.querySelector('#studio-export-select-all');
                    const clearBtn = panel.querySelector('#studio-export-clear');
                    const includeCoverCheckbox = panel.querySelector('#studio-export-include-cover-checkbox');
                    const includeColophonCheckbox = panel.querySelector('#studio-export-include-colophon-checkbox');
                    const forceRemoteCheckbox = panel.querySelector('#studio-export-force-remote-checkbox');
                    const cleanupTempCheckbox = panel.querySelector('#studio-export-cleanup-temp-checkbox');
                    const includeCoverHidden = panel.querySelector('#studio-export-include-cover-hidden');
                    const includeColophonHidden = panel.querySelector('#studio-export-include-colophon-hidden');
                    const forceRemoteHidden = panel.querySelector('#studio-export-force-remote-hidden');
                    const cleanupTempHidden = panel.querySelector('#studio-export-cleanup-temp-hidden');
                    const thumbsSlot = panel.querySelector('#studio-export-thumbs-slot');
                    const overridesToggleBtn = panel.querySelector('#studio-export-overrides-toggle');
                    const overridesPanel = panel.querySelector('#studio-export-overrides-panel');
                    const profileSelect = panel.querySelector('#studio-export-profile');
                    const profileCatalogRaw = panel.querySelector('#studio-export-profiles-json');
                    const compressionField = panel.querySelector('#studio-export-compression');
                    const sourceModeField = panel.querySelector('#studio-export-source-mode');
                    const maxEdgeField = panel.querySelector('#studio-export-max-edge');
                    const jpegQualityField = panel.querySelector('#studio-export-jpeg-quality');
                    const parallelField = panel.querySelector('#studio-export-parallel');
                    const scopeAllBtn = panel.querySelector('#studio-export-scope-all');
                    const scopeCustomBtn = panel.querySelector('#studio-export-scope-custom');
                    const subtabBuild = panel.querySelector('#studio-export-subtab-build');
                    const subtabPages = panel.querySelector('#studio-export-subtab-pages');
                    const subtabJobs = panel.querySelector('#studio-export-subtab-jobs');
                    const optimizeBtn = panel.querySelector('#studio-export-optimize-btn');
                    const optimizeSelectedBtn = panel.querySelector('#studio-export-optimize-selected-btn');
                    const openBuildBtn = panel.querySelector('#studio-export-open-build');
                    const openPagesBtn = panel.querySelector('#studio-export-open-pages-custom');
                    const buildSubtabHidden = panel.querySelector('#studio-export-build-subtab-state');
                    const buildTabGenerateBtn = panel.querySelector('#studio-export-build-tab-generate');
                    const buildTabFilesBtn = panel.querySelector('#studio-export-build-tab-files');

                    if (thumbPageHidden && thumbsSlot && thumbsSlot.dataset.thumbPage) {
                        thumbPageHidden.value = thumbsSlot.dataset.thumbPage;
                    }
                    if (pageSizeHidden && thumbsSlot && thumbsSlot.dataset.pageSize) {
                        pageSizeHidden.value = thumbsSlot.dataset.pageSize;
                    }

                    function setOverridesVisible(visible) {
                        const expanded = !!visible;
                        if (overridesPanel) {
                            overridesPanel.classList.toggle('hidden', !expanded);
                        }
                        if (overridesToggleBtn) {
                            overridesToggleBtn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
                            overridesToggleBtn.textContent = expanded
                                ? 'Nascondi override per questo job'
                                : 'Personalizza override per questo job';
                        }
                    }

                    function setSelectionScope(mode) {
                        const selected = (mode === 'custom') ? 'custom' : 'all';
                        panel.dataset.exportScope = selected;
                        if (selectionModeHidden) {
                            selectionModeHidden.value = selected;
                        }
                        if (hidden && selected === 'all') {
                            const available = availablePages(panel);
                            hidden.value = serializeSelection(available);
                        }
                        if (scopeAllBtn) {
                            scopeAllBtn.classList.toggle('app-btn-accent', selected === 'all');
                            scopeAllBtn.classList.toggle('app-btn-neutral', selected !== 'all');
                            scopeAllBtn.setAttribute('aria-pressed', selected === 'all' ? 'true' : 'false');
                        }
                        if (scopeCustomBtn) {
                            scopeCustomBtn.classList.toggle('app-btn-accent', selected === 'custom');
                            scopeCustomBtn.classList.toggle('app-btn-neutral', selected !== 'custom');
                            scopeCustomBtn.setAttribute('aria-pressed', selected === 'custom' ? 'true' : 'false');
                        }
                        applySelectionToVisible(panel);
                        syncSelectionStore(panel);
                    }

                    function activateSubtab(name) {
                        const selected = (name === 'build' || name === 'jobs') ? name : 'pages';
                        panel.dataset.exportSubtab = selected;
                        if (subtabStateHidden) {
                            subtabStateHidden.value = selected;
                        }
                        if (subtabPages) subtabPages.classList.toggle('hidden', selected !== 'pages');
                        if (subtabBuild) subtabBuild.classList.toggle('hidden', selected !== 'build');
                        if (subtabJobs) subtabJobs.classList.toggle('hidden', selected !== 'jobs');
                    }

                    function activateBuildSubtab(name) {
                        const selected = name === 'files' ? 'files' : 'generate';
                        if (buildSubtabHidden) {
                            buildSubtabHidden.value = selected;
                        }
                        const generateBlocks = panel.querySelectorAll('.studio-export-build-generate-block');
                        generateBlocks.forEach((node) => {
                            node.classList.toggle('hidden', selected !== 'generate');
                        });
                        const filesBlocks = panel.querySelectorAll('.studio-export-build-files-block');
                        filesBlocks.forEach((node) => {
                            node.classList.toggle('hidden', selected !== 'files');
                        });
                        if (buildTabGenerateBtn) {
                            buildTabGenerateBtn.classList.toggle('app-btn-accent', selected === 'generate');
                            buildTabGenerateBtn.classList.toggle('app-btn-neutral', selected !== 'generate');
                            buildTabGenerateBtn.setAttribute(
                                'aria-pressed',
                                selected === 'generate' ? 'true' : 'false'
                            );
                        }
                        if (buildTabFilesBtn) {
                            buildTabFilesBtn.classList.toggle('app-btn-accent', selected === 'files');
                            buildTabFilesBtn.classList.toggle('app-btn-neutral', selected !== 'files');
                            buildTabFilesBtn.setAttribute('aria-pressed', selected === 'files' ? 'true' : 'false');
                        }
                    }
                    if (scopeAllBtn && scopeAllBtn.dataset.bound !== '1') {
                        scopeAllBtn.dataset.bound = '1';
                        scopeAllBtn.addEventListener('click', () => setSelectionScope('all'));
                    }
                    if (scopeCustomBtn && scopeCustomBtn.dataset.bound !== '1') {
                        scopeCustomBtn.dataset.bound = '1';
                        scopeCustomBtn.addEventListener('click', () => setSelectionScope('custom'));
                    }
                    if (openBuildBtn && openBuildBtn.dataset.bound !== '1') {
                        openBuildBtn.dataset.bound = '1';
                        openBuildBtn.addEventListener('click', () => {
                            setSelectionScope('custom');
                            activateSubtab('build');
                            if (window.switchTab) {
                                const state = hidden ? hidden.value : '';
                                const thumbPage = thumbPageHidden ? thumbPageHidden.value : '';
                                const pageSize = pageSizeHidden ? pageSizeHidden.value : '';
                                window.switchTab('output', {
                                    reloadExport: true,
                                    exportParams: {
                                        subtab: 'build',
                                        build_subtab: 'generate',
                                        selected_pages: state,
                                        thumb_page: thumbPage,
                                        page_size: pageSize,
                                    },
                                });
                            }
                        });
                    }
                    if (openPagesBtn && openPagesBtn.dataset.bound !== '1') {
                        openPagesBtn.dataset.bound = '1';
                        openPagesBtn.addEventListener('click', () => {
                            activateSubtab('pages');
                            if (window.switchTab) {
                                const state = hidden ? hidden.value : '';
                                const thumbPage = thumbPageHidden ? thumbPageHidden.value : '';
                                const pageSize = pageSizeHidden ? pageSizeHidden.value : '';
                                window.switchTab('images', {
                                    reloadExport: true,
                                    exportParams: {
                                        subtab: 'pages',
                                        selected_pages: state,
                                        thumb_page: thumbPage,
                                        page_size: pageSize,
                                    },
                                });
                                return;
                            }
                            const tabButton = document.getElementById('studio-export-tab-pages');
                            if (tabButton) tabButton.click();
                        });
                    }
                    if (buildTabGenerateBtn && buildTabGenerateBtn.dataset.bound !== '1') {
                        buildTabGenerateBtn.dataset.bound = '1';
                        buildTabGenerateBtn.addEventListener('click', () => activateBuildSubtab('generate'));
                    }
                    if (buildTabFilesBtn && buildTabFilesBtn.dataset.bound !== '1') {
                        buildTabFilesBtn.dataset.bound = '1';
                        buildTabFilesBtn.addEventListener('click', () => activateBuildSubtab('files'));
                    }

                    const profileCatalog = (() => {
                        if (!profileCatalogRaw) return {};
                        try {
                            return JSON.parse(profileCatalogRaw.value || '{}');
                        } catch (_e) {
                            return {};
                        }
                    })();

                    function applyProfile(profileKey) {
                        const key = String(profileKey || '').trim();
                        if (!key) return;
                        const cfg = profileCatalog[key];
                        if (!cfg || typeof cfg !== 'object') return;
                        const parseProfileBool = (value, fallback) => {
                            if (value === undefined || value === null) return fallback;
                            if (typeof value === 'boolean') return value;
                            if (typeof value === 'number') return value !== 0;
                            const raw = String(value).trim().toLowerCase();
                            if (['1', 'true', 'on', 'yes'].includes(raw)) return true;
                            if (['0', 'false', 'off', 'no'].includes(raw)) return false;
                            return fallback;
                        };
                        const syncToggle = (checkbox, hiddenInput, nextVal) => {
                            if (!checkbox || !hiddenInput) return;
                            checkbox.checked = !!nextVal;
                            hiddenInput.value = nextVal ? '1' : '0';
                        };
                        if (compressionField && typeof cfg.compression === 'string' && cfg.compression) {
                            compressionField.value = cfg.compression;
                        }
                        if (sourceModeField && typeof cfg.image_source_mode === 'string' && cfg.image_source_mode) {
                            sourceModeField.value = cfg.image_source_mode;
                        }
                        if (
                            maxEdgeField &&
                            cfg.image_max_long_edge_px !== undefined &&
                            cfg.image_max_long_edge_px !== null
                        ) {
                            const val = parseInt(String(cfg.image_max_long_edge_px), 10);
                            if (!Number.isNaN(val)) maxEdgeField.value = String(val);
                        }
                        if (jpegQualityField && cfg.jpeg_quality !== undefined && cfg.jpeg_quality !== null) {
                            const val = parseInt(String(cfg.jpeg_quality), 10);
                            if (!Number.isNaN(val)) jpegQualityField.value = String(val);
                        }
                        if (
                            parallelField &&
                            cfg.max_parallel_page_fetch !== undefined &&
                            cfg.max_parallel_page_fetch !== null
                        ) {
                            const val = parseInt(String(cfg.max_parallel_page_fetch), 10);
                            if (!Number.isNaN(val)) parallelField.value = String(val);
                        }
                        syncToggle(
                            includeCoverCheckbox,
                            includeCoverHidden,
                            parseProfileBool(
                                cfg.include_cover,
                                includeCoverCheckbox ? includeCoverCheckbox.checked : true
                            )
                        );
                        syncToggle(
                            includeColophonCheckbox,
                            includeColophonHidden,
                            parseProfileBool(
                                cfg.include_colophon,
                                includeColophonCheckbox ? includeColophonCheckbox.checked : true
                            )
                        );
                        syncToggle(
                            forceRemoteCheckbox,
                            forceRemoteHidden,
                            parseProfileBool(
                                cfg.force_remote_refetch,
                                forceRemoteCheckbox ? forceRemoteCheckbox.checked : false
                            )
                        );
                        syncToggle(
                            cleanupTempCheckbox,
                            cleanupTempHidden,
                            parseProfileBool(
                                cfg.cleanup_temp_after_export,
                                cleanupTempCheckbox ? cleanupTempCheckbox.checked : true
                            )
                        );
                    }

                    if (profileSelect && profileSelect.dataset.bound !== '1') {
                        profileSelect.dataset.bound = '1';
                        profileSelect.addEventListener('change', () => {
                            applyProfile(profileSelect.value);
                        });
                    }

                    if (overridesToggleBtn && overridesToggleBtn.dataset.bound !== '1') {
                        overridesToggleBtn.dataset.bound = '1';
                        overridesToggleBtn.addEventListener('click', () => {
                            const hidden = overridesPanel
                                ? overridesPanel.classList.contains('hidden')
                                : true;
                            setOverridesVisible(hidden);
                        });
                    }

                    if (rangeBtn && rangeBtn.dataset.bound !== '1') {
                        rangeBtn.dataset.bound = '1';
                        rangeBtn.addEventListener('click', () => {
                            if (!hidden || !rangeInput) return;
                            const parsed = parseSelection(rangeInput.value || '');
                            hidden.value = serializeSelection(parsed);
                            setSelectionScope('custom');
                            applySelectionToVisible(panel);
                            syncSelectionStore(panel);
                        });
                    }

                    if (allBtn && allBtn.dataset.bound !== '1') {
                        allBtn.dataset.bound = '1';
                        allBtn.addEventListener('click', () => {
                            if (!hidden) return;
                            hidden.value = serializeSelection(availablePages(panel));
                            setSelectionScope('all');
                            applySelectionToVisible(panel);
                            syncSelectionStore(panel);
                        });
                    }

                    if (clearBtn && clearBtn.dataset.bound !== '1') {
                        clearBtn.dataset.bound = '1';
                        clearBtn.addEventListener('click', () => {
                            if (!hidden) return;
                            hidden.value = '';
                            setSelectionScope('custom');
                            applySelectionToVisible(panel);
                            syncSelectionStore(panel);
                        });
                    }

                    if (optimizeBtn && optimizeBtn.dataset.bound !== '1') {
                        optimizeBtn.dataset.bound = '1';
                        optimizeBtn.addEventListener('click', () => {
                            if (subtabStateHidden) subtabStateHidden.value = 'pages';
                        });
                    }
                    if (optimizeSelectedBtn && optimizeSelectedBtn.dataset.bound !== '1') {
                        optimizeSelectedBtn.dataset.bound = '1';
                        optimizeSelectedBtn.addEventListener('click', () => {
                            if (subtabStateHidden) subtabStateHidden.value = 'pages';
                            setSelectionScope('custom');
                        });
                    }

                    bindThumbCards(panel, () => {
                        setSelectionScope('custom');
                    });
                    applySelectionToVisible(panel);
                    syncSelectionStore(panel);

                    if (includeCoverCheckbox && includeCoverHidden && includeCoverCheckbox.dataset.bound !== '1') {
                        includeCoverCheckbox.dataset.bound = '1';
                        includeCoverCheckbox.addEventListener('change', () => {
                            includeCoverHidden.value = includeCoverCheckbox.checked ? '1' : '0';
                        });
                    }
                    if (
                        includeColophonCheckbox &&
                        includeColophonHidden &&
                        includeColophonCheckbox.dataset.bound !== '1'
                    ) {
                        includeColophonCheckbox.dataset.bound = '1';
                        includeColophonCheckbox.addEventListener('change', () => {
                            includeColophonHidden.value = includeColophonCheckbox.checked ? '1' : '0';
                        });
                    }
                    if (forceRemoteCheckbox && forceRemoteHidden && forceRemoteCheckbox.dataset.bound !== '1') {
                        forceRemoteCheckbox.dataset.bound = '1';
                        forceRemoteCheckbox.addEventListener('change', () => {
                            forceRemoteHidden.value = forceRemoteCheckbox.checked ? '1' : '0';
                        });
                    }
                    if (cleanupTempCheckbox && cleanupTempHidden && cleanupTempCheckbox.dataset.bound !== '1') {
                        cleanupTempCheckbox.dataset.bound = '1';
                        cleanupTempCheckbox.addEventListener('change', () => {
                            cleanupTempHidden.value = cleanupTempCheckbox.checked ? '1' : '0';
                        });
                    }

                    if (form && form.dataset.bound !== '1') {
                        form.dataset.bound = '1';
                        form.addEventListener('submit', () => {
                            if (subtabStateHidden) {
                                subtabStateHidden.value = panel.dataset.exportSubtab || 'build';
                            }
                            if (thumbPageHidden && thumbsSlot && thumbsSlot.dataset.thumbPage) {
                                thumbPageHidden.value = thumbsSlot.dataset.thumbPage;
                            }
                            if (pageSizeHidden && thumbsSlot && thumbsSlot.dataset.pageSize) {
                                pageSizeHidden.value = thumbsSlot.dataset.pageSize;
                            }

                            const submitButtons = panel.querySelectorAll('button[data-export-submit="1"]');
                            submitButtons.forEach((btn) => {
                                btn.disabled = true;
                                btn.classList.add('opacity-60', 'cursor-not-allowed');
                            });
                        });
                    }
                    setOverridesVisible(false);
                    activateSubtab(panel.dataset.exportSubtab || 'pages');
                    activateBuildSubtab(buildSubtabHidden ? buildSubtabHidden.value : 'generate');
                    let initialScope = panel.dataset.exportScope ||
                        (selectionModeHidden ? selectionModeHidden.value : 'all');
                    if (hidden && availableInput) {
                        const selected = parseSelection(hidden.value || '');
                        const available = parseSelection(availableInput.value || '');
                        if (selected.size > 0 && available.size > 0 && selected.size < available.size) {
                            initialScope = 'custom';
                        }
                    }
                    setSelectionScope(initialScope);
                }

                if (!window.__studioExportListenersBound) {
                    window.__studioExportListenersBound = true;
                    document.addEventListener('DOMContentLoaded', initStudioExport);
                    document.body.addEventListener('htmx:afterSwap', (event) => {
                        const target = event && event.detail ? event.detail.target : null;
                        if (!target) {
                            initStudioExport();
                            return;
                        }
                        const targetId = target.id || '';
                        if (
                            targetId === 'tab-content-images' ||
                            targetId === 'tab-content-output' ||
                            targetId === 'tab-content-jobs' ||
                            targetId === 'studio-export-thumbs-slot' ||
                            targetId === 'studio-export-panel'
                        ) {
                            initStudioExport();
                            return;
                        }
                        if (typeof target.closest === 'function' && target.closest('#studio-export-panel')) {
                            initStudioExport();
                        }
                    });
                    document.body.addEventListener('htmx:configRequest', (event) => {
                        const detail = event && event.detail ? event.detail : null;
                        const sourceEl = detail && detail.elt ? detail.elt : null;
                        if (!sourceEl) return;
                        const pollId = sourceEl.id || '';
                        if (!pollId) return;
                        if (
                            pollId !== 'studio-export-live-state-poller' &&
                            pollId !== 'studio-export-jobs' &&
                            pollId !== 'studio-export-pdf-list'
                        ) {
                            return;
                        }
                        const activeTab = String(document.body && document.body.dataset
                            ? (document.body.dataset.studioActiveTab || '')
                            : '').trim().toLowerCase();
                        const wrongTab = (
                            (pollId === 'studio-export-live-state-poller' && activeTab !== 'images') ||
                            (pollId === 'studio-export-pdf-list' && activeTab !== 'output') ||
                            (pollId === 'studio-export-jobs' && activeTab !== 'jobs')
                        );
                        if (document.hidden === true || wrongTab) {
                            event.preventDefault();
                        }
                    });
                }
                // Important: when Export tab is lazy-loaded, DOMContentLoaded already fired.
                // Run immediately so first thumbnails page is selectable without extra swaps.
                initStudioExport();
            })();
            """
        ),
        id="studio-export-panel",
        cls="space-y-4",
        **{"data-export-subtab": active_subtab},
    )
