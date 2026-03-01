"""Studio Export tab component (single-item PDF workflow)."""

from __future__ import annotations

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


def _thumbnail_card(item: dict):
    page = int(item.get("page") or 0)
    thumb_url = str(item.get("thumb_url") or "")
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

    return Button(
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
    cards = [_thumbnail_card(item) for item in thumbnails]
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

    description_rows_raw = export_defaults.get("description_rows", 3)
    try:
        description_rows = int(description_rows_raw)
    except (TypeError, ValueError):
        description_rows = 3
    description_rows = max(2, min(description_rows, 8))

    return Div(
        Div(
            H3("Export PDF", cls="text-base font-semibold text-slate-900 dark:text-slate-100"),
            P(
                "Crea PDF dell'item con modalita rapida o selettiva da thumbnails.",
                cls="text-xs text-slate-500 dark:text-slate-400",
            ),
            cls="mb-2",
        ),
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
        Div(
            Form(
                Input(type="hidden", name="doc_id", value=doc_id),
                Input(type="hidden", name="library", value=library),
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
                Div(
                    Div(
                        Label("Formato", for_="studio-export-format", cls=_LABEL_CLASS),
                        Select(
                            Option("PDF (solo immagini)", value="pdf_images", selected=default_format == "pdf_images"),
                            Option(
                                "PDF ricercabile", value="pdf_searchable", selected=default_format == "pdf_searchable"
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
                    cls="flex flex-wrap gap-4 mt-3",
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
            cls="bg-slate-50 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-700 rounded-2xl p-4",
        ),
        Div(
            render_pdf_inventory_panel(
                pdf_files,
                doc_id=doc_id,
                library=library,
                polling=has_active_jobs,
            ),
            cls="mt-4",
        ),
        Div(jobs_panel, cls="mt-4"),
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
                    const includeCoverHidden = panel.querySelector('#studio-export-include-cover-hidden');
                    const includeColophonHidden = panel.querySelector('#studio-export-include-colophon-hidden');
                    const thumbsSlot = panel.querySelector('#studio-export-thumbs-slot');

                    if (thumbPageHidden && thumbsSlot && thumbsSlot.dataset.thumbPage) {
                        thumbPageHidden.value = thumbsSlot.dataset.thumbPage;
                    }
                    if (pageSizeHidden && thumbsSlot && thumbsSlot.dataset.pageSize) {
                        pageSizeHidden.value = thumbsSlot.dataset.pageSize;
                    }

                    bindThumbCards(panel);
                    updateSelectedCount(panel);

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

                            const submitButtons = panel.querySelectorAll('button[data-export-submit="1"]');
                            submitButtons.forEach((btn) => {
                                btn.disabled = true;
                                btn.classList.add('opacity-60', 'cursor-not-allowed');
                            });
                        });
                    }
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
