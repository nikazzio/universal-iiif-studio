from __future__ import annotations

from fasthtml.common import H3, Button, Div, P, Script

from studio_ui.components.settings.controls import (
    setting_number,
    setting_range,
    setting_select,
    setting_toggle,
)


def _viewer_subtabs_script() -> Script:
    """Initialize nested Viewer sub-tabs inside Settings > Viewer pane."""
    return Script(
        """
        (function() {
            function activate(pane, tabName) {
                const target = (tabName || 'zoom').trim();
                pane.dataset.viewerActiveTab = target;
                const buttons = pane.querySelectorAll('[data-viewer-tab-btn]');
                const sections = pane.querySelectorAll('[data-viewer-tab-pane]');
                buttons.forEach((btn) => {
                    const isActive = (btn.dataset.viewerTabBtn || '') === target;
                    btn.classList.toggle('app-btn-primary', isActive);
                    btn.classList.toggle('app-btn-neutral', !isActive);
                });
                sections.forEach((section) => {
                    const isActive = (section.dataset.viewerTabPane || '') === target;
                    section.classList.toggle('hidden', !isActive);
                });
            }

            function bind(root) {
                const pane =
                    (root && root.querySelector && root.querySelector('[data-pane="viewer"]')) ||
                    (root && root.querySelector && root.querySelector('[data_pane="viewer"]')) ||
                    (
                        root &&
                        root.matches &&
                        (root.matches('[data-pane="viewer"]') || root.matches('[data_pane="viewer"]'))
                            ? root
                            : null
                    ) ||
                    document.querySelector('[data-pane="viewer"],[data_pane="viewer"]');
                if (!pane) return;

                if (pane.dataset.viewerTabsBound !== '1') {
                    pane.dataset.viewerTabsBound = '1';
                    pane.querySelectorAll('[data-viewer-tab-btn]').forEach((btn) => {
                        btn.addEventListener('click', () => activate(pane, btn.dataset.viewerTabBtn || 'zoom'));
                    });
                }
                activate(pane, pane.dataset.viewerActiveTab || 'zoom');
            }

            if (!window.__settingsViewerTabsBound) {
                window.__settingsViewerTabsBound = true;
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


def _visual_preset_controls(filters: dict, preset_name: str):
    preset = filters.get("presets", {}).get(preset_name, {})
    path = f"settings.viewer.visual_filters.presets.{preset_name}"
    title = preset_name.capitalize()
    return [
        setting_range(
            f"{title} Brightness",
            f"{path}.brightness",
            preset.get("brightness", 1.0),
            min_val=0,
            max_val=2,
            step_val=0.05,
            help_text=f"Luminosita del preset {title.lower()} applicato dal pannello Viewer.",
        ),
        setting_range(
            f"{title} Contrast",
            f"{path}.contrast",
            preset.get("contrast", 1.0),
            min_val=0,
            max_val=2,
            step_val=0.05,
            help_text=f"Contrasto del preset {title.lower()} per enfatizzare tratto e fondo.",
        ),
        setting_range(
            f"{title} Saturation",
            f"{path}.saturation",
            preset.get("saturation", 1.0),
            min_val=0,
            max_val=2,
            step_val=0.05,
            help_text=f"Saturazione del preset {title.lower()}.",
        ),
        setting_range(
            f"{title} Hue",
            f"{path}.hue",
            preset.get("hue", 0),
            min_val=-180,
            max_val=180,
            step_val=1,
            help_text=f"Rotazione tinta (hue) del preset {title.lower()} in gradi.",
        ),
        setting_toggle(
            f"{title} Invert",
            f"{path}.invert",
            preset.get("invert", False),
            help_text=f"Inversione colori per il preset {title.lower()}.",
        ),
        setting_toggle(
            f"{title} Grayscale",
            f"{path}.grayscale",
            preset.get("grayscale", False),
            help_text=f"Scala di grigi per il preset {title.lower()}.",
        ),
    ]


def _build_viewer_pane(cm, s):
    _ = cm
    viewer = s.get("viewer", {})
    mirador_cfg = viewer.get("mirador", {})
    mirador = mirador_cfg.get("openSeadragonOptions", {})
    visual = viewer.get("visual_filters", {})
    defaults = visual.get("defaults", {})
    zoom_section = Div(
        H3("Zoom & Navigation", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2"),
        P(
            "Controlli OpenSeadragon per la profondita di zoom nel viewer Mirador.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
            setting_toggle(
                "Require complete local images",
                "settings.viewer.mirador.require_complete_local_images",
                mirador_cfg.get("require_complete_local_images", True),
                help_text=(
                    "Blocca Mirador finche non sono presenti tutte le pagine locali. "
                    "Riduce anteprime remote fuorvianti durante download parziali."
                ),
            ),
            setting_select(
                "Saved Source Policy",
                "settings.viewer.source_policy.saved_mode",
                str((viewer.get("source_policy") or {}).get("saved_mode", "remote_first")),
                [
                    ("remote_first", "Remote first (saved)"),
                    ("local_first", "Local first (saved)"),
                ],
                help_text="Per item salvati ma non completi, decide se Studio apre remoto o tenta lock locale.",
            ),
            setting_number(
                "Max Zoom Pixel Ratio",
                "settings.viewer.mirador.openSeadragonOptions.maxZoomPixelRatio",
                mirador.get("maxZoomPixelRatio", 5),
                min_val=1,
                max_val=10,
                step_val=0.1,
                help_text="Rapporto massimo pixel schermo/immagine: aumenta la profondita dello zoom percepito.",
            ),
            setting_number(
                "Max Zoom Level",
                "settings.viewer.mirador.openSeadragonOptions.maxZoomLevel",
                mirador.get("maxZoomLevel", 25),
                min_val=1,
                max_val=100,
                step_val=1,
                help_text="Limite assoluto di zoom OpenSeadragon; alzalo per analisi paleografica molto dettagliata.",
            ),
            setting_number(
                "Min Zoom Level",
                "settings.viewer.mirador.openSeadragonOptions.minZoomLevel",
                mirador.get("minZoomLevel", 0.35),
                min_val=0.05,
                max_val=1,
                step_val=0.05,
                help_text="Zoom minimo consentito quando riduci la pagina nel viewer.",
            ),
            cls="grid grid-cols-1 md:grid-cols-3 gap-4",
        ),
        **{"data-viewer-tab-pane": "zoom"},
    )

    defaults_section = Div(
        H3("Default Filters", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2"),
        P(
            "Valori base applicati al viewer all'apertura del documento prima di selezionare preset manuali.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
            setting_range(
                "Brightness",
                "settings.viewer.visual_filters.defaults.brightness",
                defaults.get("brightness", 1.0),
                min_val=0,
                max_val=2,
                step_val=0.05,
                help_text="Luminosita base applicata al canvas del viewer.",
            ),
            setting_range(
                "Contrast",
                "settings.viewer.visual_filters.defaults.contrast",
                defaults.get("contrast", 1.0),
                min_val=0,
                max_val=2,
                step_val=0.05,
                help_text="Contrasto base del viewer per migliorare leggibilita di inchiostri e fondi.",
            ),
            setting_range(
                "Saturation",
                "settings.viewer.visual_filters.defaults.saturation",
                defaults.get("saturation", 1.0),
                min_val=0,
                max_val=2,
                step_val=0.05,
                help_text="Saturazione base; ridurla aiuta su carte ingiallite o dominanti cromatiche forti.",
            ),
            setting_range(
                "Hue",
                "settings.viewer.visual_filters.defaults.hue",
                defaults.get("hue", 0),
                min_val=-180,
                max_val=180,
                step_val=1,
                help_text="Rotazione tonalita colore in gradi.",
            ),
            setting_toggle(
                "Invert",
                "settings.viewer.visual_filters.defaults.invert",
                defaults.get("invert", False),
                help_text="Inverte i colori nel viewer (utile per alcune analisi di contrasto).",
            ),
            setting_toggle(
                "Grayscale",
                "settings.viewer.visual_filters.defaults.grayscale",
                defaults.get("grayscale", False),
                help_text="Converte la vista in scala di grigi.",
            ),
            cls="grid grid-cols-1 md:grid-cols-3 gap-4",
        ),
        cls="hidden",
        **{"data-viewer-tab-pane": "defaults"},
    )

    presets_section = Div(
        H3("Preset Filters", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2"),
        P(
            "Preset rapidi selezionabili nel Viewer: modifica qui i loro parametri operativi.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
            *_visual_preset_controls(visual, "default"),
            *_visual_preset_controls(visual, "night"),
            *_visual_preset_controls(visual, "contrast"),
            cls="grid grid-cols-1 md:grid-cols-3 gap-4",
        ),
        cls="hidden",
        **{"data-viewer-tab-pane": "presets"},
    )

    return Div(
        Div(H3("Viewer (Mirador)", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3")),
        P(
            "Impostazioni suddivise in sotto-sezioni per una taratura piu chiara di zoom e filtri visivi.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
            Button(
                "Zoom",
                type="button",
                cls="app-btn app-btn-primary",
                **{"data-viewer-tab-btn": "zoom"},
            ),
            Button(
                "Defaults",
                type="button",
                cls="app-btn app-btn-neutral",
                **{"data-viewer-tab-btn": "defaults"},
            ),
            Button(
                "Presets",
                type="button",
                cls="app-btn app-btn-neutral",
                **{"data-viewer-tab-btn": "presets"},
            ),
            cls="flex items-center gap-2 mb-4",
        ),
        zoom_section,
        defaults_section,
        presets_section,
        _viewer_subtabs_script(),
        cls="p-4",
        data_pane="viewer",
    )
