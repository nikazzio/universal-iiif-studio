"""Studio Info and Visual Tabs Components."""

import json

from fasthtml.common import H3, H4, A, Button, Div, Img, Input, Label, P, Script, Span

from studio_ui.config import get_setting


def info_row(label, value):
    """Render a single info row."""
    val = value[0] if isinstance(value, list) and value else value
    if val in (None, ""):
        val = "N/D"
    display_value = str(val) if isinstance(val, (int, float, str)) else val
    return Div(
        Div(label, cls="text-[10px] font-bold text-gray-400 uppercase tracking-widest"),
        Div(display_value, cls="text-sm font-medium text-gray-800 dark:text-gray-200 break-words"),
    )


def _flatten_text(value):
    """Flatten various metadata value formats into a simple string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        if "@value" in value:
            return _flatten_text(value["@value"])
        if "value" in value:
            return _flatten_text(value["value"])
        parts = [_flatten_text(v) for v in value.values()]
        parts = [p for p in parts if p]
        return "; ".join(parts)
    if isinstance(value, list):
        parts = [_flatten_text(v) for v in value]
        parts = [p for p in parts if p]
        return "; ".join(parts)
    return str(value)


def _ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _resolve_url(item):
    if item is None:
        return None
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("@id") or item.get("id") or item.get("href")
    return None


def _thumbnail_url(descriptor):
    if descriptor is None:
        return None
    if isinstance(descriptor, list):
        return _thumbnail_url(descriptor[0])
    if isinstance(descriptor, dict):
        return descriptor.get("@id") or descriptor.get("id")
    if isinstance(descriptor, str):
        return descriptor
    return None


def _canvases_from_manifest(manifest_json):
    if not manifest_json:
        return []
    sequences = manifest_json.get("sequences") or []
    if sequences:
        canvases = sequences[0].get("canvases") or []
        if canvases:
            return canvases
    return manifest_json.get("items") or []


def _select_canvas(canvases, page_idx):
    if not canvases:
        return {}
    idx = max(0, min(page_idx - 1, len(canvases) - 1))
    return canvases[idx]


def _image_resources(canvas):
    resources = []
    if not canvas:
        return resources
    for image in canvas.get("images", []):
        resource = image.get("resource") or image.get("body")
        if resource:
            resources.append(resource)
    for page in canvas.get("items", []):
        for annotation in page.get("items", []):
            body = annotation.get("body") or annotation.get("resource")
            if isinstance(body, list):
                for item in body:
                    if isinstance(item, dict):
                        resources.append(item)
            elif isinstance(body, dict):
                resources.append(body)
    return resources


def _render_metadata_grid(entries, title, max_rows=8):
    rows = []
    for entry in _ensure_list(entries)[:max_rows]:
        label = _flatten_text(entry.get("label") or entry.get("property")) or "Metadata"
        value = _flatten_text(entry.get("value") or entry.get("content"))
        if value:
            rows.append(info_row(label, value))
    if not rows:
        return None
        return Div(
            H4(title, cls="text-xs font-bold uppercase tracking-[0.3em] text-slate-400"),
            Div(*rows, cls="grid gap-3 sm:grid-cols-2"),
            cls=(
                "space-y-2 bg-slate-50 dark:bg-slate-900/40 p-4 rounded-2xl border "
                "border-dashed border-slate-200 dark:border-slate-700",
            ),
        )


def _render_see_also(entries, title):
    items = []
    for entry in _ensure_list(entries):
        if isinstance(entry, str):
            url = _resolve_url(entry)
            label = entry
        else:
            url = _resolve_url(entry)
            label = _flatten_text(entry.get("label")) or url
        if url:
            items.append(
                A(
                    label,
                    href=url,
                    target="_blank",
                    rel="noreferrer",
                    cls="text-xs font-semibold uppercase tracking-[0.3em] text-indigo-600 dark:text-indigo-300",
                )
            )
    if not items:
        return None
    return Div(
        H4(title, cls="text-xs font-bold uppercase tracking-[0.3em] text-slate-400"),
        Div(*items, cls="flex flex-wrap gap-2"),
        cls="space-y-2",
    )


def _render_providers(entries):
    providers = _ensure_list(entries)
    if not providers:
        return None
    rows = []
    for provider in providers:
        name = _flatten_text(provider.get("label") or provider.get("name"))
        homepage = _resolve_url(provider.get("homepage"))
        if not name and not homepage:
            continue
        link = (
            A(
                "Sito",
                href=homepage,
                target="_blank",
                rel="noreferrer",
                cls="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-500",
            )
            if homepage
            else None
        )
        rows.append(
            Div(
                Span(name or "Provider", cls="text-sm font-semibold text-slate-700 dark:text-slate-200"),
                link or Span("Indirizzo non disponibile", cls="text-xs text-slate-500"),
                cls="flex items-center justify-between gap-2",
            )
        )
    if not rows:
        return None
    return Div(
        H4("Provider IIIF", cls="text-xs font-bold uppercase tracking-[0.3em] text-slate-400"),
        Div(*rows, cls="space-y-2"),
        cls="space-y-3",
    )


def info_tab_content(meta, total_pages, manifest_json, page_idx, doc_id, library):
    """Render the Info tab content."""
    manifest = manifest_json or {}
    title = (
        _flatten_text(meta.get("full_display_title"))
        or _flatten_text(manifest.get("label"))
        or meta.get("title")
        or doc_id
    )
    description = _flatten_text(manifest.get("description")) or meta.get("description") or ""
    attribution = _flatten_text(manifest.get("attribution") or meta.get("attribution") or library)
    manifest_id = _resolve_url(manifest.get("@id") or manifest.get("id"))
    manifest_link = meta.get("manifest_url") or manifest_id
    rights_label = _flatten_text(manifest.get("rights") or manifest.get("license"))
    viewing_direction = manifest.get("viewingDirection") or manifest.get("viewingdirection")
    viewing_hint = manifest.get("viewingHint")
    canvases = _canvases_from_manifest(manifest)
    canvas_count = len(canvases)
    canvas = _select_canvas(canvases, page_idx)
    canvas_label = _flatten_text(canvas.get("label"))
    canvas_id = _resolve_url(canvas.get("@id") or canvas.get("id"))
    canvas_metadata_section = _render_metadata_grid(canvas.get("metadata"), "Metadati della pagina")
    canvas_see_also = _render_see_also(canvas.get("seeAlso"), "Vedi anche (pagina)")
    manifest_metadata_section = _render_metadata_grid(manifest.get("metadata"), "Metadati principali")
    manifest_see_also = _render_see_also(manifest.get("seeAlso"), "Vedi anche (manifesto)")
    providers_section = _render_providers(manifest.get("provider") or manifest.get("providers"))
    resource = _image_resources(canvas)[0] if _image_resources(canvas) else None
    resource_format = _flatten_text(resource.get("format")) if resource else ""
    resource_dims = ""
    if resource and resource.get("width") and resource.get("height"):
        resource_dims = f"{resource['width']} × {resource['height']} px"
    service = None
    if resource:
        svc = resource.get("service")
        if isinstance(svc, list):
            svc = svc[0]
        if isinstance(svc, dict):
            service = _resolve_url(svc)
        elif isinstance(svc, str):
            service = svc
    # ensure we compute a concrete URL string (or None) and use it for A(...)
    resource_url = _resolve_url(resource) if resource else None
    thumbnail_url = _thumbnail_url(canvas.get("thumbnail")) or _thumbnail_url(manifest.get("thumbnail"))
    canvas_preview = (
        Div(
            Img(src=thumbnail_url, alt=canvas_label or title, cls="w-full h-52 object-cover rounded-xl"),
            cls="mt-4 overflow-hidden rounded-2xl border border-gray-200 dark:border-gray-700",
        )
        if thumbnail_url
        else None
    )
    document_rows = [
        info_row("Titolo", title),
        info_row("Biblioteca", library),
        info_row("Biblioteca (attribuzione)", attribution),
        info_row("ID Documento", doc_id),
        info_row("ID Manifesto", manifest_id),
        info_row(
            "Manifesto ufficiale",
            A("Apri manifest", href=manifest_link, target="_blank", rel="noreferrer") if manifest_link else "N/D",
        ),
        info_row("Diritti", rights_label),
        info_row("Pagine rilevate", str(total_pages)),
        info_row("Canvases IIIF", f"{canvas_count}") if canvas_count else info_row("Canvases IIIF", "N/D"),
        info_row("Data download", meta.get("download_date")),
        info_row("Viewing direction", viewing_direction),
        info_row("Viewing hint", viewing_hint),
    ]
    page_rows = [
        info_row("Etichetta pagina", canvas_label),
        info_row("Canvas ID", canvas_id),
        info_row("Dimensioni canvas", f"{canvas.get('width', 'N/D')} × {canvas.get('height', 'N/D')} px"),
        info_row("Formato immagine", resource_format),
        info_row("Dimensioni immagine", resource_dims),
        info_row(
            "Immagine IIIF",
            A("Apri risorsa", href=resource_url, target="_blank", rel="noreferrer") if resource_url else "N/D",
        ),
        info_row(
            "Servizio IIIF",
            A("Endpoint", href=service, target="_blank", rel="noreferrer") if service else "N/D",
        ),
    ]
    return [
        Div(
            Div(
                H3("Documento in esame", cls="text-lg font-black text-slate-900 dark:text-white"),
                P(description, cls="text-sm text-slate-600 dark:text-slate-300") if description else None,
                Div(*document_rows, cls="grid gap-4 sm:grid-cols-2"),
                providers_section or Div(),
                manifest_metadata_section or Div(),
                manifest_see_also or Div(),
                canvas_preview and Div(canvas_preview, cls="mt-2"),
                cls="space-y-4",
            ),
            Div(
                H3(
                    f"Pagina {page_idx} di {canvas_count or total_pages}",
                    cls="text-lg font-black text-slate-900 dark:text-white",
                ),
                Div(*page_rows, cls="grid gap-4 sm:grid-cols-2"),
                canvas_metadata_section or Div(),
                canvas_see_also or Div(),
                canvas_preview and Div(canvas_preview, cls="block lg:hidden"),
                cls="space-y-4",
            ),
            cls=(
                "space-y-6 p-6 bg-white dark:bg-gray-900 rounded-2xl border "
                "border-gray-100 dark:border-gray-800 shadow-lg",
            ),
        )
    ]


DEFAULT_VISUAL_STATE = {
    "brightness": 1.0,
    "contrast": 1.0,
    "saturation": 1.0,
    "hue": 0,
    "invert": False,
    "grayscale": False,
}

DEFAULT_VISUAL_PRESETS = {
    "default": {**DEFAULT_VISUAL_STATE},
    "night": {
        "brightness": 0.9,
        "contrast": 1.3,
        "saturation": 0.9,
        "hue": 0,
        "invert": False,
        "grayscale": False,
    },
    "contrast": {
        "brightness": 1.05,
        "contrast": 1.5,
        "saturation": 1.2,
        "hue": 0,
        "invert": False,
        "grayscale": False,
    },
}


def _visual_control_row(label_text, control_id, min_val, max_val, step, value):
    return Div(
        Label(label_text, for_=control_id, cls="text-xs uppercase font-semibold tracking-wider text-slate-400"),
        Div(
            Input(
                type="range",
                id=control_id,
                min=str(min_val),
                max=str(max_val),
                step=str(step),
                value=str(value),
                cls="w-full h-2 rounded-full bg-slate-200 accent-indigo-500 cursor-pointer",
                **{"data-visual-control": control_id.replace("visual-", "")},
            ),
            Span(f"{value:.2f}", id=f"{control_id}-value", cls="text-xs font-mono text-slate-500 ml-2"),
            cls="flex items-center gap-3 mt-1",
        ),
        cls="space-y-1",
    )


def visual_tab_content():
    """Render the Visual Filters tab content."""
    visual_cfg = get_setting("viewer.visual_filters", {}) or {}
    defaults = {**DEFAULT_VISUAL_STATE, **visual_cfg.get("defaults", {})}
    presets = visual_cfg.get("presets", DEFAULT_VISUAL_PRESETS)
    default_state_json = json.dumps(defaults, ensure_ascii=False)
    presets_json = json.dumps(presets, ensure_ascii=False)

    visual_script = """
        (function(){
            const selectors = [
                '#mirador-viewer canvas',
                '#mirador-viewer img',
                '#mirador-viewer .mirador-viewport canvas',
                '#mirador-viewer .mirador-viewport img',
                '#mirador-viewer .mirador-viewer-window .mirador-window-center canvas',
                '#mirador-viewer .mirador-viewer-window .mirador-window-center img',
            ].join(',');
            const styleId = 'studio-visual-filter-style';
            const defaultState = __DEFAULT_STATE__;
            const presets = __PRESETS__;
            const state = { ...defaultState };

            const ensureStyle = () => {
                let el = document.getElementById(styleId);
                if (!el) {
                    el = document.createElement('style');
                    el.id = styleId;
                    document.head.appendChild(el);
                }
                return el;
            };

            const buildFilter = () => {
                const parts = [
                    `brightness(${state.brightness})`,
                    `contrast(${state.contrast})`,
                    `saturate(${state.saturation})`,
                    `hue-rotate(${state.hue}deg)`
                ];
                if (state.grayscale) parts.push('grayscale(1)');
                if (state.invert) parts.push('invert(1)');
                return parts.join(' ');
            };

            const applyFilters = () => {
                const styleEl = ensureStyle();
                styleEl.textContent = `${selectors} { filter: ${buildFilter()}; transition: filter 0.2s ease; }`;
                updateDisplayValues();
                updateToggleState();
            };

            const updateDisplayValues = () => {
                document.querySelectorAll('[data-visual-control]').forEach(input => {
                    const display = document.getElementById(`${input.id}-value`);
                    if (display) {
                        const key = input.dataset.visualControl;
                        display.textContent = parseFloat(state[key]).toFixed(2);
                    }
                });
            };

            const updateToggleState = () => {
                document.querySelectorAll('[data-visual-toggle]').forEach(btn => {
                    const key = btn.dataset.visualToggle;
                    btn.setAttribute('aria-pressed', state[key]);
                    btn.classList.toggle('bg-indigo-600', state[key]);
                    btn.classList.toggle('text-white', state[key]);
                    btn.classList.toggle('border-slate-300', !state[key]);
                });
            };

            const handleSlider = (event) => {
                const key = event.target.dataset.visualControl;
                state[key] = parseFloat(event.target.value);
                applyFilters();
            };

            const handleToggle = (event) => {
                const key = event.target.dataset.visualToggle;
                state[key] = !state[key];
                applyFilters();
            };

            const applyPreset = (preset) => {
                const values = presets[preset];
                if (!values) return;
                Object.assign(state, values);
                applyFilters();
                document.querySelectorAll('[data-visual-control]').forEach(input => {
                    const key = input.dataset.visualControl;
                    input.value = state[key];
                });
            };

            const initControls = () => {
                document.querySelectorAll('[data-visual-control]').forEach(input => {
                    if (!input.dataset.bound) {
                        input.dataset.bound = 'true';
                        input.addEventListener('input', handleSlider);
                    }
                });
                document.querySelectorAll('[data-visual-toggle]').forEach(btn => {
                    if (!btn.dataset.bound) {
                        btn.dataset.bound = 'true';
                        btn.addEventListener('click', handleToggle);
                    }
                });
                document.querySelectorAll('[data-visual-preset]').forEach(btn => {
                    if (!btn.dataset.bound) {
                        btn.dataset.bound = 'true';
                        btn.addEventListener('click', () => applyPreset(btn.dataset.visualPreset));
                    }
                });
                applyFilters();
            };

            initControls();
            const observeMirador = () => {
                const target = document.getElementById('mirador-viewer');
                if (!target || target.dataset.visualObserver) {
                    return;
                }
                const observer = new MutationObserver(() => {
                    applyFilters();
                });
                observer.observe(target, { childList: true, subtree: true });
                target.dataset.visualObserver = 'true';
            };
            observeMirador();
            document.addEventListener('htmx:afterSwap', (event) => {
                if (event.detail?.target?.id === 'tab-content-visual') {
                    initControls();
                }
            });
        })();
    """.replace("__DEFAULT_STATE__", default_state_json).replace("__PRESETS__", presets_json)

    return [
        Div(
            H3("Filtri visuali per la trascrizione", cls="font-bold text-lg text-slate-800 dark:text-slate-200 mb-2"),
            Div(
                "Applica filtri solo all'immagine principale di Mirador, lasciando menu e miniature invariati.",
                cls="text-sm text-slate-500 dark:text-slate-400",
            ),
            Div(
                _visual_control_row("Luminosità", "visual-brightness", 0.6, 1.6, 0.05, defaults.get("brightness", 1.0)),
                _visual_control_row("Contrasto", "visual-contrast", 0.6, 1.6, 0.05, defaults.get("contrast", 1.0)),
                _visual_control_row(
                    "Saturazione", "visual-saturation", 0.5, 1.8, 0.05, defaults.get("saturation", 1.0)
                ),
                _visual_control_row("Tonalità (hue)", "visual-hue", -30, 30, 1, defaults.get("hue", 0)),
                cls="space-y-4 mt-4",
            ),
            Div(
                Button(
                    "Inverti colori",
                    type="button",
                    cls=(
                        "flex-1 text-sm font-semibold uppercase tracking-[0.2em] px-3 py-2 rounded-full "
                        "border border-slate-300 text-slate-700 dark:text-slate-100"
                    ),
                    **{"data-visual-toggle": "invert"},
                ),
                Button(
                    "B/N intenso",
                    type="button",
                    cls=(
                        "flex-1 text-sm font-semibold uppercase tracking-[0.2em] px-3 py-2 rounded-full "
                        "border border-slate-300 text-slate-700 dark:text-slate-100"
                    ),
                    **{"data-visual-toggle": "grayscale"},
                ),
                cls="flex gap-3 mt-4",
            ),
            Div(
                Button(
                    "Default",
                    type="button",
                    cls=(
                        "text-xs font-bold uppercase px-3 py-2 rounded-full bg-slate-100 "
                        "text-slate-800 dark:bg-slate-800 dark:text-slate-100 transition"
                    ),
                    **{"data-visual-preset": "default"},
                ),
                Button(
                    "Lettura notturna",
                    type="button",
                    cls=(
                        "text-xs font-bold uppercase px-3 py-2 rounded-full bg-gradient-to-r "
                        "from-indigo-500 to-slate-900 text-white shadow-lg"
                    ),
                    **{"data-visual-preset": "night"},
                ),
                Button(
                    "Contrasto +",
                    type="button",
                    cls=(
                        "text-xs font-bold uppercase px-3 py-2 rounded-full bg-gradient-to-r "
                        "from-emerald-500 to-emerald-700 text-white shadow-lg"
                    ),
                    **{"data-visual-preset": "contrast"},
                ),
                cls="flex flex-wrap gap-2 mt-4",
            ),
            Div(
                "Mirador mantiene zoom e navigazione: usa la barra di zoom sul viewer quando serve.",
                cls="text-xs text-slate-400 dark:text-slate-500 mt-3",
            ),
            Script(visual_script),
            cls=(
                "p-4 bg-white dark:bg-gray-900/60 rounded-2xl border "
                "border-gray-200 dark:border-gray-800 shadow-lg space-y-4"
            ),
        )
    ]
