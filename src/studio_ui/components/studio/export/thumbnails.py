"""Thumbnail cards, panels, and poller for the export tab."""

from __future__ import annotations

from urllib.parse import quote

from fasthtml.common import Button, Div, Img, Option, Select, Span

from .pdf_inventory import _bytes_label


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
                        Span("⬇ Hi", cls="studio-thumb-action-label text-[11px] font-semibold"),
                        Span(
                            "",
                            id=f"studio-thumb-progress-hi-{page}",
                            cls=f"studio-thumb-progress {hi_progress_cls}",
                            style=f"--progress:{hi_progress_percent}%;",
                            aria_hidden="true",
                        ),
                        cls="studio-thumb-action-inner",
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
                        Span("🧩 Std", cls="studio-thumb-action-label text-[11px] font-semibold"),
                        Span(
                            "",
                            id=f"studio-thumb-progress-stitch-{page}",
                            cls=f"studio-thumb-progress {stitch_progress_cls}",
                            style=f"--progress:{stitch_progress_percent}%;",
                            aria_hidden="true",
                        ),
                        cls="studio-thumb-action-inner",
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
                        Span("⚙ Opt", cls="studio-thumb-action-label text-[11px] font-semibold"),
                        Span(
                            "",
                            id=f"studio-thumb-progress-opt-{page}",
                            cls=f"studio-thumb-progress {opt_progress_cls}",
                            style=f"--progress:{opt_progress_percent}%;",
                            aria_hidden="true",
                        ),
                        cls="studio-thumb-action-inner",
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
            "hx_indicator": "#studio-export-thumbs-loading",
        }
    )
    next_attrs = (
        {}
        if is_last
        else {
            "hx_get": _thumb_page_url(doc_id=doc_id, library=library, thumb_page=next_page, page_size=page_size),
            "hx_target": "#studio-export-thumbs-slot",
            "hx_swap": "outerHTML",
            "hx_indicator": "#studio-export-thumbs-loading",
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
            Span(
                "",
                id="studio-export-thumbs-loading",
                cls=(
                    "htmx-indicator inline-block h-4 w-4 border-2 "
                    "border-slate-300 border-t-cyan-500 rounded-full animate-spin"
                ),
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
                    hx_indicator="#studio-export-thumbs-loading",
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
