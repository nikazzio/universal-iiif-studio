from __future__ import annotations

from fasthtml.common import H3, Div

from studio_ui.components.settings.controls import (
    setting_color,
    setting_input,
    setting_number,
    setting_select,
)
from studio_ui.library_options import library_options, normalize_library_value
from studio_ui.theme import preset_options, resolve_ui_theme


def _build_general_pane(cm, s):
    _ = cm
    api = cm.data.get("api_keys", {})
    ui = s.get("ui", {})
    theme = resolve_ui_theme(ui)
    defaults = s.get("defaults", {})
    library_settings = s.get("library", {})
    return Div(
        Div(H3("API Keys & Theme", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3")),
        Div(
            setting_input("OpenAI API Key", "api_keys.openai", api.get("openai", ""), "password", "Key per OpenAI."),
            setting_input(
                "Anthropic API Key",
                "api_keys.anthropic",
                api.get("anthropic", ""),
                "password",
                "Key per Anthropic.",
            ),
            setting_input(
                "Google Vision API Key",
                "api_keys.google_vision",
                api.get("google_vision", ""),
                "password",
                "Key per Google Vision.",
            ),
            setting_input(
                "HuggingFace Token",
                "api_keys.huggingface",
                api.get("huggingface", ""),
                "password",
                "Token HuggingFace.",
            ),
            setting_select(
                "Theme Preset",
                "settings.ui.theme_preset",
                theme["preset"],
                preset_options(),
                help_text="Preset armonici: imposta insieme Primary e Accent.",
            ),
            setting_color(
                "Primary Color",
                "settings.ui.theme_primary_color",
                theme["primary"],
                help_text="Colore principale del tema globale (menu, stati primari).",
            ),
            setting_color(
                "Accent Color",
                "settings.ui.theme_accent_color",
                theme["accent"],
                help_text="Accento UI (tab attivo, focus, slider, call to action).",
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        Div(H3("Defaults & Behaviour", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3 mt-6")),
        Div(
            setting_select(
                "Default Library",
                "settings.defaults.default_library",
                normalize_library_value(defaults.get("default_library", "Vaticana")),
                library_options(),
                help_text="Biblioteca predefinita proposta nei form di ricerca e risoluzione manifest.",
            ),
            setting_select(
                "Preferred OCR Engine",
                "settings.defaults.preferred_ocr_engine",
                defaults.get("preferred_ocr_engine", "openai"),
                [
                    ("openai", "OpenAI"),
                    ("anthropic", "Anthropic"),
                    ("google_vision", "Google Vision"),
                    ("kraken", "Kraken (Local)"),
                ],
                help_text="Motore OCR pre-selezionato nei workflow che non specificano un engine esplicito.",
            ),
            setting_select(
                "Library Default View",
                "settings.library.default_mode",
                str(library_settings.get("default_mode", "operativa")),
                [
                    ("operativa", "Vista Operativa"),
                    ("archivio", "Vista Archivio"),
                ],
                help_text="Modalita predefinita della pagina Library quando non ci sono filtri URL.",
            ),
            setting_number(
                "Library Items / Page",
                "settings.ui.items_per_page",
                ui.get("items_per_page", 12),
                min_val=4,
                max_val=200,
                step_val=1,
                help_text="Numero di record mostrati per pagina nella Libreria locale.",
            ),
            setting_number(
                "Toast Duration (ms)",
                "settings.ui.toast_duration",
                ui.get("toast_duration", 3000),
                min_val=500,
                max_val=15000,
                step_val=100,
                help_text="Durata delle notifiche globali (toast) in millisecondi.",
            ),
            setting_number(
                "Studio Recent Items",
                "settings.ui.studio_recent_max_items",
                ui.get("studio_recent_max_items", 8),
                min_val=1,
                max_val=20,
                step_val=1,
                help_text="Numero massimo di documenti mostrati nel mini-hub /studio (Recenti).",
            ),
            setting_number(
                "Download Manager Polling (s)",
                "settings.ui.polling.download_manager_interval_seconds",
                ((ui.get("polling") or {}).get("download_manager_interval_seconds", 3)),
                min_val=1,
                max_val=30,
                step_val=1,
                help_text="Intervallo polling HTMX del Download Manager (valori bassi = UI piu reattiva).",
            ),
            setting_number(
                "Download Status Polling (s)",
                "settings.ui.polling.download_status_interval_seconds",
                ((ui.get("polling") or {}).get("download_status_interval_seconds", 3)),
                min_val=1,
                max_val=30,
                step_val=1,
                help_text="Intervallo polling HTMX della card stato download in Discovery.",
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="general",
    )
