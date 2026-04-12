"""Main export tab assembly — orchestrates sub-components into the full tab."""

from __future__ import annotations

import json
from urllib.parse import quote

from fasthtml.common import (
    H3,
    A,
    Button,
    Div,
    Form,
    Input,
    Label,
    Option,
    P,
    Select,
    Span,
    Textarea,
)

from studio_ui.components.export import render_export_jobs_panel

from .pages import _render_export_pages_subtab
from .pdf_inventory import render_pdf_inventory_panel
from .tab_script import _export_tab_script

_FIELD_CLASS = "app-field"
_LABEL_CLASS = "app-label"


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
        _export_tab_script(),
        id="studio-export-panel",
        cls="space-y-4",
        **{"data-export-subtab": active_subtab},
    )
