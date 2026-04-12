from __future__ import annotations

from fasthtml.common import H3, H4, Button, Div, P, Script, Span

from studio_ui.components.settings.controls import (
    setting_input,
    setting_number,
    setting_range,
    setting_select,
    setting_toggle,
)
from universal_iiif_core.image_settings import IMAGE_STRATEGY_PRESETS


def _images_subtabs_script() -> Script:
    """Initialize Images/Thumbnails/OCR sub-tabs inside the imaging pane."""
    return Script(
        """
        (function() {
            function syncCustomStrategyVisibility(pane) {
                const modeField = pane.querySelector('[name="settings.images.download_strategy_mode"]');
                const customWrap = pane.querySelector('[data-images-custom-strategy]');
                if (!modeField || !customWrap) return;
                const isCustom = String(modeField.value || '').trim() === 'custom';
                customWrap.classList.toggle('hidden', !isCustom);
                customWrap.setAttribute('aria-hidden', isCustom ? 'false' : 'true');
                customWrap.querySelectorAll('input,select,textarea').forEach((field) => {
                    if (field.name === 'settings.images.download_strategy_custom') {
                        field.disabled = !isCustom;
                    }
                });
            }

            function activate(pane, tabName) {
                const target = (tabName || 'images').trim();
                pane.dataset.imagesActiveTab = target;
                pane.querySelectorAll('[data-images-tab-btn]').forEach((btn) => {
                    const isActive = (btn.dataset.imagesTabBtn || '') === target;
                    btn.classList.toggle('app-btn-primary', isActive);
                    btn.classList.toggle('app-btn-neutral', !isActive);
                });
                pane.querySelectorAll('[data-images-tab-pane]').forEach((section) => {
                    const isActive = (section.dataset.imagesTabPane || '') === target;
                    section.classList.toggle('hidden', !isActive);
                });
            }

            function bind(root) {
                const pane =
                    (root && root.querySelector && root.querySelector('[data-pane="images"]')) ||
                    (root && root.querySelector && root.querySelector('[data_pane="images"]')) ||
                    (
                        root &&
                        root.matches &&
                        (root.matches('[data-pane="images"]') || root.matches('[data_pane="images"]'))
                            ? root
                            : null
                    ) ||
                    document.querySelector('[data-pane="images"],[data_pane="images"]');
                if (!pane) return;

                if (pane.dataset.imagesTabsBound !== '1') {
                    pane.dataset.imagesTabsBound = '1';
                    pane.querySelectorAll('[data-images-tab-btn]').forEach((btn) => {
                        btn.addEventListener('click', () => activate(pane, btn.dataset.imagesTabBtn || 'images'));
                    });
                    const modeField = pane.querySelector('[name="settings.images.download_strategy_mode"]');
                    if (modeField) {
                        modeField.addEventListener('change', () => syncCustomStrategyVisibility(pane));
                    }
                }
                activate(pane, pane.dataset.imagesActiveTab || 'images');
                syncCustomStrategyVisibility(pane);
            }

            if (!window.__settingsImagesTabsBound) {
                window.__settingsImagesTabsBound = true;
                document.addEventListener('DOMContentLoaded', () => bind(document));
                document.body.addEventListener('htmx:afterSwap', (evt) => {
                    const target = evt && evt.detail ? evt.detail.target : null;
                    bind(target || document);
                });
            }
            bind(document);
        })();
        """
    )


def _build_images_pane(cm, s):
    _ = cm
    images = s.get("images", {})
    ocr = s.get("ocr", {})
    defaults = s.get("defaults", {})
    thumbs = s.get("thumbnails", {})

    images_section = Div(
        Div(
            H4("Download Pagine", cls="text-sm font-semibold text-slate-900 dark:text-slate-100"),
            P(
                "Queste opzioni governano il download standard del volume e il pulsante Std nello Studio Export.",
                cls="text-xs text-slate-600 dark:text-slate-300",
            ),
            Div(
                setting_select(
                    "Preset download",
                    "settings.images.download_strategy_mode",
                    str(images.get("download_strategy_mode") or "balanced"),
                    [
                        ("balanced", "Standard"),
                        ("quality_first", "Massima qualità"),
                        ("fast", "Veloce"),
                        ("archival", "Solo full/max"),
                        ("custom", "Personalizzata"),
                    ],
                    help_text="Definisce l'ordine dei tentativi diretti prima dell'eventuale fallback.",
                ),
                Div(
                    setting_input(
                        "Sequenza tentativi diretti",
                        "settings.images.download_strategy_custom",
                        ",".join(images.get("download_strategy_custom", [])),
                        help_text=(
                            "Usata solo con Personalizzata. `3000` e `1740` sono tentativi espliciti; "
                            "`max` prova `full/max`."
                        ),
                    ),
                    **{"data-images-custom-strategy": "true"},
                ),
                setting_select(
                    "Fallback immagini",
                    "settings.images.stitch_mode_default",
                    str(images.get("stitch_mode_default") or "auto_fallback"),
                    [
                        ("auto_fallback", "Automatico (diretto -> stitch)"),
                        ("direct_only", "Solo diretto"),
                        ("stitch_only", "Solo stitch"),
                    ],
                    help_text=(
                        "Decide se il download standard puo passare allo stitch quando i tentativi diretti falliscono."
                    ),
                ),
                Div(
                    H4("Preset correnti", cls="text-xs font-semibold text-slate-700 dark:text-slate-200"),
                    Span(
                        f"Standard: {' -> '.join(IMAGE_STRATEGY_PRESETS['balanced'])}",
                        cls="block text-xs text-slate-500 dark:text-slate-400",
                    ),
                    Span(
                        f"Massima qualità: {' -> '.join(IMAGE_STRATEGY_PRESETS['quality_first'])}",
                        cls="block text-xs text-slate-500 dark:text-slate-400",
                    ),
                    Span(
                        f"Veloce: {' -> '.join(IMAGE_STRATEGY_PRESETS['fast'])}",
                        cls="block text-xs text-slate-500 dark:text-slate-400",
                    ),
                    Span(
                        f"Solo full/max: {' -> '.join(IMAGE_STRATEGY_PRESETS['archival'])}",
                        cls="block text-xs text-slate-500 dark:text-slate-400",
                    ),
                    cls="space-y-1 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 px-3 py-2",
                ),
                cls="grid grid-cols-1 md:grid-cols-2 gap-4",
            ),
            cls="space-y-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-3",
        ),
        Div(
            H4("Ottimizzazione Locale", cls="text-sm font-semibold text-slate-900 dark:text-slate-100"),
            P(
                "Queste opzioni sono usate dal pulsante Opt. Non cambiano il download iniziale della pagina.",
                cls="text-xs text-slate-600 dark:text-slate-300",
            ),
            Div(
                setting_number(
                    "Lato lungo max (px)",
                    "settings.images.local_optimize.max_long_edge_px",
                    ((images.get("local_optimize") or {}).get("max_long_edge_px", 2600)),
                    min_val=512,
                    max_val=12000,
                    step_val=1,
                    help_text="Riduce il file locale fino al lato lungo massimo scelto.",
                ),
                setting_range(
                    "Qualità JPEG locale",
                    "settings.images.local_optimize.jpeg_quality",
                    ((images.get("local_optimize") or {}).get("jpeg_quality", 82)),
                    help_text="Compressione JPEG usata durante l'ottimizzazione locale.",
                    min_val=10,
                    max_val=100,
                    step_val=1.0,
                ),
                cls="grid grid-cols-1 md:grid-cols-2 gap-4",
            ),
            cls="space-y-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-3",
        ),
        Div(
            H4("Avanzate IIIF", cls="text-sm font-semibold text-slate-900 dark:text-slate-100"),
            P(
                "Controlli tecnici per servizi IIIF e stitching. In genere conviene lasciare i default.",
                cls="text-xs text-slate-600 dark:text-slate-300",
            ),
            Div(
                setting_select(
                    "IIIF Quality",
                    "settings.images.iiif_quality",
                    images.get("iiif_quality", "default"),
                    [
                        ("default", "default"),
                        ("color", "color"),
                        ("gray", "gray"),
                        ("bitonal", "bitonal"),
                        ("native", "native"),
                    ],
                    help_text="Parametro `quality` delle URL IIIF. Non decide la risoluzione dell'immagine.",
                ),
                setting_range(
                    "Tile Stitch Max RAM (GB)",
                    "settings.images.tile_stitch_max_ram_gb",
                    images.get("tile_stitch_max_ram_gb", 2),
                    help_text="Tetto RAM usato quando il sistema deve comporre tile molto grandi.",
                    min_val=0.1,
                    max_val=64,
                    step_val=0.1,
                ),
                cls="grid grid-cols-1 md:grid-cols-2 gap-4",
            ),
            cls="space-y-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-3",
        ),
        cls="space-y-4",
        **{"data-images-tab-pane": "images"},
    )

    thumbnails_section = Div(
        Div(
            setting_number(
                "Default Thumb / Page",
                "settings.thumbnails.page_size",
                thumbs.get("page_size", 48),
                min_val=1,
                max_val=120,
                step_val=1,
                help_text="Numero iniziale di miniature mostrate per pagina nel tab Studio Export.",
            ),
            setting_input(
                "Thumb / Page Options",
                "settings.thumbnails.page_size_options",
                ",".join(str(v) for v in thumbs.get("page_size_options", [24, 48, 72, 96])),
                help_text="Valori separati da virgola usati nel selettore.",
            ),
            setting_number(
                "Thumb Max Edge (px)",
                "settings.thumbnails.max_long_edge_px",
                thumbs.get("max_long_edge_px", 320),
                min_val=64,
                max_val=2000,
                step_val=1,
                help_text="Lato lungo massimo miniature generate localmente.",
            ),
            setting_range(
                "Thumb JPEG Quality",
                "settings.thumbnails.jpeg_quality",
                thumbs.get("jpeg_quality", 70),
                help_text="Qualita JPEG miniature (10-100).",
                min_val=10,
                max_val=100,
                step_val=1.0,
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="hidden",
        **{"data-images-tab-pane": "thumbnails"},
    )

    ocr_section = Div(
        Div(
            setting_select(
                "OCR Engine",
                "settings.ocr.ocr_engine",
                ocr.get("ocr_engine", defaults.get("preferred_ocr_engine", "openai")),
                [
                    ("openai", "OpenAI"),
                    ("anthropic", "Anthropic"),
                    ("google_vision", "Google Vision"),
                    ("kraken", "Kraken"),
                ],
                help_text="Motore OCR predefinito usato dai workflow Studio.",
            ),
            setting_toggle(
                "Kraken Enabled",
                "settings.ocr.kraken_enabled",
                ocr.get("kraken_enabled", False),
                help_text="Abilita Kraken locale nelle opzioni OCR.",
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="hidden",
        **{"data-images-tab-pane": "ocr"},
    )

    return Div(
        Div(H3("Imaging Pipeline", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3")),
        P(
            "Gestione unificata immagini, miniature e OCR. Le impostazioni immagini sono globali.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
            Button(
                "Images",
                type="button",
                cls="app-btn app-btn-primary",
                **{"data-images-tab-btn": "images"},
            ),
            Button(
                "Thumbnails",
                type="button",
                cls="app-btn app-btn-neutral",
                **{"data-images-tab-btn": "thumbnails"},
            ),
            Button(
                "OCR",
                type="button",
                cls="app-btn app-btn-neutral",
                **{"data-images-tab-btn": "ocr"},
            ),
            cls="flex items-center gap-2 mb-4",
        ),
        images_section,
        thumbnails_section,
        ocr_section,
        _images_subtabs_script(),
        cls="p-4",
        data_pane="images",
    )
