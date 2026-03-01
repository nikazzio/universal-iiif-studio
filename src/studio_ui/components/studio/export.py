"""Studio Export tab component (single-item PDF workflow)."""

from __future__ import annotations

import json
from urllib.parse import quote

from fasthtml.common import H3, A, Button, Div, Form, Img, Input, Label, Option, P, Script, Select, Span, Textarea

from studio_ui.components.export import render_export_jobs_panel

_FIELD_CLASS = "app-field"
_LABEL_CLASS = "app-label"


def _kind_chip(kind: str):
    value = (kind or "other").strip().lower()
    palette = {
        "native": "app-chip app-chip-success",
        "compiled": "app-chip app-chip-primary",
        "studio-export": "app-chip app-chip-accent",
        "other": "app-chip app-chip-neutral",
    }
    return Span(value, cls=f"{palette.get(value, palette['other'])} text-[10px] font-semibold")


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
            "hx_trigger": "load, every 5s",
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
                    _kind_chip(kind),
                    cls="flex items-center gap-2 min-w-0",
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
        H3("PDF dell'item", cls="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-2"),
        Div(*rows, cls="space-y-2"),
        id="studio-export-pdf-list",
        **attrs,
    )


def _dims_label(width: int | None, height: int | None, *, fallback: str = "n/a") -> str:
    if not width or not height:
        return fallback
    return f"{int(width)}x{int(height)}"


def _thumbnail_card(*, item: dict, doc_id: str, library: str, thumb_page: int, page_size: int):
    page = int(item.get("page") or 0)
    thumb_url = str(item.get("thumb_url") or "")
    local_dims = _dims_label(item.get("local_width"), item.get("local_height"))
    remote_dims = _dims_label(item.get("remote_width"), item.get("remote_height"))
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    image = (
        Img(
            src=thumb_url,
            cls=(
                "w-full h-28 object-cover rounded border border-slate-200 dark:border-slate-700 "
                "bg-slate-100 dark:bg-slate-800"
            ),
        )
        if thumb_url
        else Div(
            "No thumb",
            cls=(
                "w-full h-28 rounded border border-dashed border-slate-300 dark:border-slate-700 "
                "text-xs text-slate-500 dark:text-slate-400 flex items-center justify-center"
            ),
        )
    )

    select_btn = Button(
        Div(
            image,
            Div(
                Span(f"Pag. {page}", cls="text-xs font-medium text-slate-700 dark:text-slate-200"),
                cls="mt-1 flex items-center justify-between",
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
    return Div(
        select_btn,
        Div(
            Span(f"Locale: {local_dims}", cls="text-[11px] text-slate-600 dark:text-slate-300"),
            Span(f"Online max: {remote_dims}", cls="text-[11px] text-slate-500 dark:text-slate-400"),
            Button(
                "High-Res",
                type="button",
                hx_post=highres_url,
                hx_target="#studio-export-panel",
                hx_swap="outerHTML",
                cls="app-btn app-btn-neutral text-[11px] px-2 py-1",
            ),
            cls="mt-1.5 flex items-center justify-between gap-2",
        ),
        cls="space-y-1",
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
) -> Div:
    """Render one paginated thumbnails slice for export selection."""
    cards = [
        _thumbnail_card(item=item, doc_id=doc_id, library=library, thumb_page=thumb_page, page_size=page_size)
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
        Div(*cards, cls="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2"),
        id="studio-export-thumbs-slot",
        **{
            "data-thumb-page": str(thumb_page),
            "data-thumb-pages": str(thumb_page_count),
            "data-page-size": str(page_size),
            "data-thumbs-endpoint": _thumb_base_url(doc_id=doc_id, library=library),
        },
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
    export_defaults: dict,
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

    jobs_count = len(jobs)

    return Div(
        Div(
            render_pdf_inventory_panel(
                pdf_files,
                doc_id=doc_id,
                library=library,
                polling=has_active_jobs,
            ),
            cls="mb-4",
        ),
        Div(
            Div(
                H3("Export PDF", cls="text-base font-semibold text-slate-900 dark:text-slate-100"),
                P(
                    "Seleziona un profilo, imposta il formato e genera il PDF dalle pagine necessarie.",
                    cls="text-xs text-slate-500 dark:text-slate-400",
                ),
                cls="mb-2",
            ),
            Div(
                Button(
                    "Crea PDF",
                    type="button",
                    id="studio-export-subtab-btn-build",
                    data_subtab="build",
                    cls="app-btn app-btn-primary",
                ),
                Button(
                    f"Job ({jobs_count})",
                    type="button",
                    id="studio-export-subtab-btn-jobs",
                    data_subtab="jobs",
                    cls="app-btn app-btn-neutral",
                ),
                cls="flex items-center gap-2 mb-3",
            ),
            Div(
                Div(
                    Button(
                        "Crea PDF rapido (tutte le pagine)",
                        type="submit",
                        form="studio-export-form",
                        data_export_submit="1",
                        onclick="document.getElementById('studio-export-selection-mode').value='all';",
                        cls="app-btn app-btn-primary",
                    ),
                    cls="mb-3",
                ),
                Form(
                    Input(type="hidden", name="doc_id", value=doc_id),
                    Input(type="hidden", name="library", value=library),
                    Input(
                        type="hidden",
                        id="studio-export-profiles-json",
                        value=json.dumps(profile_catalog, separators=(",", ":")),
                    ),
                    Input(type="hidden", name="thumb_page", id="studio-export-thumb-page", value=str(thumb_page)),
                    Input(type="hidden", name="page_size", id="studio-export-page-size", value=str(thumb_page_size)),
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
                            Label("Profilo PDF", for_="studio-export-profile", cls=_LABEL_CLASS),
                            Div(
                                Select(
                                    *[
                                        Option(label, value=key, selected=key == default_profile_name)
                                        for key, label in profile_options
                                    ],
                                    id="studio-export-profile",
                                    name="pdf_profile",
                                    cls=_FIELD_CLASS,
                                ),
                                A(
                                    "Gestisci profili",
                                    href="/settings?tab=pdf",
                                    cls="app-btn app-btn-neutral whitespace-nowrap",
                                ),
                                cls="flex items-center gap-2",
                            ),
                            P(
                                "I profili custom si creano e modificano nelle Impostazioni PDF Export.",
                                cls="text-xs text-slate-500 dark:text-slate-400",
                            ),
                            cls="space-y-1",
                        ),
                        Div(
                            Label("Formato", for_="studio-export-format", cls=_LABEL_CLASS),
                            Select(
                                Option(
                                    "PDF (solo immagini)", value="pdf_images", selected=default_format == "pdf_images"
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
                                Option("High-Res", value="High-Res", selected=default_compression == "High-Res"),
                                Option("Standard", value="Standard", selected=default_compression == "Standard"),
                                Option("Light", value="Light", selected=default_compression == "Light"),
                                id="studio-export-compression",
                                name="compression",
                                cls=_FIELD_CLASS,
                            ),
                            cls="space-y-1",
                        ),
                        cls="grid grid-cols-1 md:grid-cols-3 gap-3",
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
                        cls="flex flex-wrap gap-4 mt-3",
                    ),
                    Div(
                        Div(
                            Label("Sorgente immagini", for_="studio-export-source-mode", cls=_LABEL_CLASS),
                            Select(
                                Option(
                                    "Locale bilanciata",
                                    value="local_balanced",
                                    selected=default_image_source_mode == "local_balanced",
                                ),
                                Option(
                                    "Locale high-res",
                                    value="local_highres",
                                    selected=default_image_source_mode == "local_highres",
                                ),
                                Option(
                                    "Remoto high-res temporaneo",
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
                        cls="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3",
                    ),
                    hx_post="/api/studio/export/start",
                    hx_trigger="submit",
                    hx_target="#studio-export-panel",
                    hx_swap="outerHTML",
                    id="studio-export-form",
                    cls="space-y-3",
                ),
                Div(
                    Label("Range rapido", for_="studio-export-range", cls=_LABEL_CLASS),
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
                        cls="flex items-center gap-2",
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
                            id="studio-export-selected-count",
                            cls="text-xs text-slate-500 dark:text-slate-400",
                        ),
                        cls="flex items-center gap-2 mt-2",
                    ),
                    cls="mt-4 space-y-2",
                ),
                render_export_thumbnails_panel(
                    doc_id=doc_id,
                    library=library,
                    thumbnails=thumbnails,
                    thumb_page=thumb_page,
                    thumb_page_count=thumb_page_count,
                    total_pages=thumb_total_pages,
                    page_size=thumb_page_size,
                    page_size_options=thumb_page_size_options,
                ),
                Div(
                    Button(
                        "Crea PDF selezionato",
                        type="submit",
                        form="studio-export-form",
                        data_export_submit="1",
                        onclick="document.getElementById('studio-export-selection-mode').value='custom';",
                        cls="app-btn app-btn-accent",
                    ),
                    cls="flex flex-wrap items-center gap-2 mt-4",
                ),
                id="studio-export-subtab-build",
                cls="space-y-2",
            ),
            Div(
                jobs_panel,
                id="studio-export-subtab-jobs",
                cls="hidden mt-3",
            ),
            cls="bg-slate-50 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-700 rounded-2xl p-4",
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
                    const count = panel.querySelector('#studio-export-selected-count');
                    if (!hidden || !count) return;
                    const selected = parseSelection(hidden.value);
                    count.textContent = `${selected.size} pagine selezionate`;
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

                function bindThumbCards(panel) {
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
                            updateThumbVisual(card, current.has(page));
                            updateSelectedCount(panel);
                        });
                    });
                }

                function initStudioExport() {
                    const panel = document.getElementById('studio-export-panel');
                    if (!panel) return;

                    const form = panel.querySelector('#studio-export-form');
                    const thumbPageHidden = panel.querySelector('#studio-export-thumb-page');
                    const pageSizeHidden = panel.querySelector('#studio-export-page-size');
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
                    const profileSelect = panel.querySelector('#studio-export-profile');
                    const profileCatalogRaw = panel.querySelector('#studio-export-profiles-json');
                    const compressionField = panel.querySelector('#studio-export-compression');
                    const sourceModeField = panel.querySelector('#studio-export-source-mode');
                    const maxEdgeField = panel.querySelector('#studio-export-max-edge');
                    const jpegQualityField = panel.querySelector('#studio-export-jpeg-quality');
                    const parallelField = panel.querySelector('#studio-export-parallel');
                    const subtabBuildBtn = panel.querySelector('#studio-export-subtab-btn-build');
                    const subtabJobsBtn = panel.querySelector('#studio-export-subtab-btn-jobs');
                    const subtabBuild = panel.querySelector('#studio-export-subtab-build');
                    const subtabJobs = panel.querySelector('#studio-export-subtab-jobs');

                    if (thumbPageHidden && thumbsSlot && thumbsSlot.dataset.thumbPage) {
                        thumbPageHidden.value = thumbsSlot.dataset.thumbPage;
                    }
                    if (pageSizeHidden && thumbsSlot && thumbsSlot.dataset.pageSize) {
                        pageSizeHidden.value = thumbsSlot.dataset.pageSize;
                    }

                    function activateSubtab(name) {
                        const selected = (name === 'jobs') ? 'jobs' : 'build';
                        panel.dataset.exportSubtab = selected;
                        if (subtabBuild) subtabBuild.classList.toggle('hidden', selected !== 'build');
                        if (subtabJobs) subtabJobs.classList.toggle('hidden', selected !== 'jobs');
                        if (subtabBuildBtn) {
                            subtabBuildBtn.classList.toggle('app-btn-primary', selected === 'build');
                            subtabBuildBtn.classList.toggle('app-btn-neutral', selected !== 'build');
                        }
                        if (subtabJobsBtn) {
                            subtabJobsBtn.classList.toggle('app-btn-primary', selected === 'jobs');
                            subtabJobsBtn.classList.toggle('app-btn-neutral', selected !== 'jobs');
                        }
                    }
                    if (subtabBuildBtn && subtabBuildBtn.dataset.bound !== '1') {
                        subtabBuildBtn.dataset.bound = '1';
                        subtabBuildBtn.addEventListener('click', () => activateSubtab('build'));
                    }
                    if (subtabJobsBtn && subtabJobsBtn.dataset.bound !== '1') {
                        subtabJobsBtn.dataset.bound = '1';
                        subtabJobsBtn.addEventListener('click', () => activateSubtab('jobs'));
                    }

                    bindThumbCards(panel);
                    updateSelectedCount(panel);

                    let profileCatalog = {};
                    if (profileCatalogRaw && profileCatalogRaw.value) {
                        try { profileCatalog = JSON.parse(profileCatalogRaw.value); } catch (_) { profileCatalog = {}; }
                    }
                    function applyProfileToControls(profileKey) {
                        const p = profileCatalog && profileCatalog[profileKey];
                        if (!p) return;
                        if (compressionField && p.compression) compressionField.value = p.compression;
                        if (sourceModeField && p.image_source_mode) sourceModeField.value = p.image_source_mode;
                        if (maxEdgeField && p.image_max_long_edge_px !== undefined) {
                            maxEdgeField.value = String(p.image_max_long_edge_px);
                        }
                        if (jpegQualityField && p.jpeg_quality !== undefined) {
                            jpegQualityField.value = String(p.jpeg_quality);
                        }
                        if (parallelField && p.max_parallel_page_fetch !== undefined) {
                            parallelField.value = String(p.max_parallel_page_fetch);
                        }
                        if (includeCoverCheckbox && p.include_cover !== undefined) {
                            includeCoverCheckbox.checked = !!p.include_cover;
                        }
                        if (includeColophonCheckbox && p.include_colophon !== undefined) {
                            includeColophonCheckbox.checked = !!p.include_colophon;
                        }
                        if (forceRemoteCheckbox && p.force_remote_refetch !== undefined) {
                            forceRemoteCheckbox.checked = !!p.force_remote_refetch;
                        }
                        if (cleanupTempCheckbox && p.cleanup_temp_after_export !== undefined) {
                            cleanupTempCheckbox.checked = !!p.cleanup_temp_after_export;
                        }
                    }
                    if (profileSelect && profileSelect.dataset.bound !== '1') {
                        profileSelect.dataset.bound = '1';
                        profileSelect.addEventListener('change', () => {
                            applyProfileToControls(profileSelect.value);
                        });
                    }

                    if (allBtn && hidden && allBtn.dataset.bound !== '1') {
                        allBtn.dataset.bound = '1';
                        allBtn.addEventListener('click', () => {
                            const available = parseSelection(availableInput ? availableInput.value : '');
                            hidden.value = serializeSelection(available);
                            applySelectionToVisible(panel);
                            updateSelectedCount(panel);
                        });
                    }

                    if (clearBtn && hidden && clearBtn.dataset.bound !== '1') {
                        clearBtn.dataset.bound = '1';
                        clearBtn.addEventListener('click', () => {
                            hidden.value = '';
                            applySelectionToVisible(panel);
                            updateSelectedCount(panel);
                        });
                    }

                    if (rangeBtn && hidden && rangeBtn.dataset.bound !== '1') {
                        rangeBtn.dataset.bound = '1';
                        rangeBtn.addEventListener('click', () => {
                            const available = parseSelection(availableInput ? availableInput.value : '');
                            const wanted = parseSelection(rangeInput ? rangeInput.value : '');
                            const filtered = new Set();
                            wanted.forEach((value) => {
                                if (available.has(value)) filtered.add(value);
                            });
                            hidden.value = serializeSelection(filtered);
                            applySelectionToVisible(panel);
                            updateSelectedCount(panel);
                        });
                    }

                    if (form && form.dataset.bound !== '1') {
                        form.dataset.bound = '1';
                        form.addEventListener('submit', () => {
                            if (includeCoverHidden && includeCoverCheckbox) {
                                includeCoverHidden.value = includeCoverCheckbox.checked ? '1' : '0';
                            }
                            if (includeColophonHidden && includeColophonCheckbox) {
                                includeColophonHidden.value = includeColophonCheckbox.checked ? '1' : '0';
                            }
                            if (forceRemoteHidden && forceRemoteCheckbox) {
                                forceRemoteHidden.value = forceRemoteCheckbox.checked ? '1' : '0';
                            }
                            if (cleanupTempHidden && cleanupTempCheckbox) {
                                cleanupTempHidden.value = cleanupTempCheckbox.checked ? '1' : '0';
                            }

                            const submitButtons = panel.querySelectorAll('button[data-export-submit="1"]');
                            submitButtons.forEach((btn) => {
                                btn.disabled = true;
                                btn.classList.add('opacity-60', 'cursor-not-allowed');
                            });
                        });
                    }
                    activateSubtab(panel.dataset.exportSubtab || 'build');
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
                            targetId === 'tab-content-export' ||
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
                }
                // Important: when Export tab is lazy-loaded, DOMContentLoaded already fired.
                // Run immediately so first thumbnails page is selectable without extra swaps.
                initStudioExport();
            })();
            """
        ),
        id="studio-export-panel",
        cls="space-y-4",
    )
