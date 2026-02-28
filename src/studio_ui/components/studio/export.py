"""Studio Export tab component (single-item PDF workflow)."""

from __future__ import annotations

from urllib.parse import quote

from fasthtml.common import H3, A, Button, Div, Form, Img, Input, Label, Option, P, Script, Select, Span, Textarea

from studio_ui.components.export import render_export_jobs_panel

_FIELD_CLASS = (
    "w-full border border-slate-300 rounded px-2 py-1 text-sm bg-white text-slate-900 "
    "placeholder:text-slate-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 "
    "dark:placeholder:text-slate-500"
)
_LABEL_CLASS = "text-xs font-medium text-slate-700 dark:text-slate-300"


def _kind_chip(kind: str):
    value = (kind or "other").strip().lower()
    palette = {
        "native": "bg-emerald-100 text-emerald-700",
        "compiled": "bg-indigo-100 text-indigo-700",
        "studio-export": "bg-amber-100 text-amber-700",
        "other": "bg-slate-100 text-slate-700",
    }
    return Span(value, cls=f"{palette.get(value, palette['other'])} text-[10px] font-semibold px-2 py-1 rounded")


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
                        cls=(
                            "px-2 py-1 rounded bg-slate-700 hover:bg-slate-600 text-white text-[11px] "
                            "dark:bg-slate-600 dark:hover:bg-slate-500"
                        ),
                    ),
                    cls="flex items-center gap-2",
                ),
                cls=(
                    "flex items-center justify-between gap-2 border border-slate-200 dark:border-slate-700 "
                    "rounded p-2 bg-white dark:bg-slate-900"
                ),
            )
        )

    if not rows:
        rows = [
            Div(
                "Nessun PDF presente nella cartella item/pdf.",
                cls="text-xs text-slate-500 dark:text-slate-400 p-2 border border-dashed rounded dark:border-slate-700",
            )
        ]

    return Div(
        H3("PDF dell'item", cls="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-2"),
        Div(*rows, cls="space-y-2"),
        id="studio-export-pdf-list",
        **attrs,
    )


def _thumbnail_card(item: dict):
    page = int(item.get("page") or 0)
    thumb_url = str(item.get("thumb_url") or "")
    checked = bool(item.get("selected"))
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

    return Label(
        Input(type="checkbox", value=str(page), cls="studio-export-page-checkbox peer sr-only", checked=checked),
        Div(
            image,
            Div(
                Span(f"Pag. {page}", cls="text-xs font-medium text-slate-700 dark:text-slate-200"),
                cls="mt-1 flex items-center justify-between",
            ),
            cls=(
                "p-1 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 "
                "hover:border-indigo-300 dark:hover:border-indigo-400 transition-colors "
                "peer-checked:border-indigo-500 peer-checked:bg-indigo-50 "
                "dark:peer-checked:border-indigo-400 dark:peer-checked:bg-indigo-950/40"
            ),
        ),
        cls="cursor-pointer block",
    )


def render_studio_export_tab(
    *,
    doc_id: str,
    library: str,
    thumbnails: list[dict],
    pdf_files: list[dict],
    jobs: list[dict],
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

    thumb_cards = [_thumbnail_card(item) for item in thumbnails]
    if not thumb_cards:
        thumb_cards = [Div("Nessuna pagina disponibile in scans/.", cls="text-sm text-slate-500")]

    return Div(
        Form(
            Input(type="hidden", name="doc_id", value=doc_id),
            Input(type="hidden", name="library", value=library),
            Input(type="hidden", name="selection_mode", id="studio-export-selection-mode", value="all"),
            Input(type="hidden", name="selected_pages", id="studio-export-selected-pages", value=""),
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
                H3("Export PDF", cls="text-base font-semibold text-slate-800 dark:text-slate-100"),
                P(
                    "Crea PDF dell'item con modalita rapida o selettiva da thumbnails.",
                    cls="text-xs text-slate-500 dark:text-slate-400",
                ),
                cls="mb-3",
            ),
            Div(
                Div(
                    Label("Formato", for_="studio-export-format", cls=_LABEL_CLASS),
                    Select(
                        Option("PDF (solo immagini)", value="pdf_images", selected=default_format == "pdf_images"),
                        Option("PDF ricercabile", value="pdf_searchable", selected=default_format == "pdf_searchable"),
                        Option("PDF testo a fronte", value="pdf_facing", selected=default_format == "pdf_facing"),
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
                        cls=(
                            "px-3 py-1 rounded bg-slate-700 hover:bg-slate-600 text-white text-xs "
                            "dark:bg-slate-600 dark:hover:bg-slate-500"
                        ),
                    ),
                    cls="flex items-center gap-2",
                ),
                Div(
                    Button(
                        "Seleziona tutte",
                        type="button",
                        id="studio-export-select-all",
                        cls="px-2 py-1 rounded bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs",
                    ),
                    Button(
                        "Deseleziona",
                        type="button",
                        id="studio-export-clear",
                        cls="px-2 py-1 rounded bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs",
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
            Div(*thumb_cards, cls="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 mt-3"),
            Div(
                Button(
                    "Crea PDF rapido (tutte le pagine)",
                    type="submit",
                    onclick="document.getElementById('studio-export-selection-mode').value='all';",
                    cls="px-4 py-2 rounded bg-indigo-700 hover:bg-indigo-600 text-white text-sm font-semibold",
                ),
                Button(
                    "Crea PDF selezionato",
                    type="submit",
                    onclick="document.getElementById('studio-export-selection-mode').value='custom';",
                    cls="px-4 py-2 rounded bg-emerald-700 hover:bg-emerald-600 text-white text-sm font-semibold",
                ),
                cls="flex flex-wrap items-center gap-2 mt-4",
            ),
            hx_post="/api/studio/export/start",
            hx_target="#studio-export-panel",
            hx_swap="outerHTML",
            id="studio-export-form",
            cls="bg-slate-50 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-700 rounded-xl p-4",
        ),
        Div(render_pdf_inventory_panel(pdf_files, doc_id=doc_id, library=library, polling=True), cls="mt-4"),
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

                function initStudioExport(root) {
                    const panel = root.querySelector('#studio-export-panel');
                    if (!panel || panel.dataset.bound === '1') return;
                    panel.dataset.bound = '1';

                    const form = panel.querySelector('#studio-export-form');
                    const boxes = Array.from(panel.querySelectorAll('.studio-export-page-checkbox'));
                    const hidden = panel.querySelector('#studio-export-selected-pages');
                    const count = panel.querySelector('#studio-export-selected-count');
                    const rangeInput = panel.querySelector('#studio-export-range');
                    const rangeBtn = panel.querySelector('#studio-export-apply-range');
                    const allBtn = panel.querySelector('#studio-export-select-all');
                    const clearBtn = panel.querySelector('#studio-export-clear');
                    const includeCoverCheckbox = panel.querySelector('#studio-export-include-cover-checkbox');
                    const includeColophonCheckbox = panel.querySelector('#studio-export-include-colophon-checkbox');
                    const includeCoverHidden = panel.querySelector('#studio-export-include-cover-hidden');
                    const includeColophonHidden = panel.querySelector('#studio-export-include-colophon-hidden');

                    const sync = () => {
                        const selected = boxes
                            .filter((box) => box.checked)
                            .map((box) => parseInt(box.value, 10))
                            .filter((n) => !Number.isNaN(n))
                            .sort((a, b) => a - b);
                        hidden.value = selected.join(',');
                        if (count) count.textContent = `${selected.length} pagine selezionate`;
                    };

                    boxes.forEach((box) => box.addEventListener('change', sync));

                    if (allBtn) {
                        allBtn.addEventListener('click', () => {
                            boxes.forEach((box) => { box.checked = true; });
                            sync();
                        });
                    }

                    if (clearBtn) {
                        clearBtn.addEventListener('click', () => {
                            boxes.forEach((box) => { box.checked = false; });
                            sync();
                        });
                    }

                    if (rangeBtn) {
                        rangeBtn.addEventListener('click', () => {
                            const wanted = parseSelection(rangeInput ? rangeInput.value : '');
                            boxes.forEach((box) => {
                                const page = parseInt(box.value, 10);
                                box.checked = wanted.has(page);
                            });
                            sync();
                        });
                    }

                    if (form) {
                        form.addEventListener('submit', () => {
                            sync();
                            if (includeCoverHidden && includeCoverCheckbox) {
                                includeCoverHidden.value = includeCoverCheckbox.checked ? '1' : '0';
                            }
                            if (includeColophonHidden && includeColophonCheckbox) {
                                includeColophonHidden.value = includeColophonCheckbox.checked ? '1' : '0';
                            }
                        });
                    }

                    sync();
                }

                document.addEventListener('DOMContentLoaded', () => initStudioExport(document));
                document.body.addEventListener('htmx:afterSwap', (event) => {
                    initStudioExport(event.detail?.target || document);
                });
            })();
            """
        ),
        id="studio-export-panel",
        cls="space-y-4",
    )
