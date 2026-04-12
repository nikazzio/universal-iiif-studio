from __future__ import annotations

from fasthtml.common import H3, Button, Div, P, Script

from studio_ui.components.settings.controls import (
    setting_input,
    setting_number,
    setting_select,
    setting_toggle,
)


def _system_subtabs_script() -> Script:
    """Initialize nested System sub-tabs inside Settings > Paths & System pane."""
    return Script(
        """
        (function() {
            function activate(pane, tabName) {
                const target = (tabName || 'paths').trim();
                pane.dataset.systemActiveTab = target;
                const buttons = pane.querySelectorAll('[data-system-tab-btn]');
                const sections = pane.querySelectorAll('[data-system-tab-pane]');
                buttons.forEach((btn) => {
                    const isActive = (btn.dataset.systemTabBtn || '') === target;
                    btn.classList.toggle('app-btn-primary', isActive);
                    btn.classList.toggle('app-btn-neutral', !isActive);
                });
                sections.forEach((section) => {
                    const isActive = (section.dataset.systemTabPane || '') === target;
                    section.classList.toggle('hidden', !isActive);
                });
            }

            function bind(root) {
                const pane =
                    (root && root.querySelector && root.querySelector('[data-pane="system"]')) ||
                    (root && root.querySelector && root.querySelector('[data_pane="system"]')) ||
                    (
                        root &&
                        root.matches &&
                        (root.matches('[data-pane="system"]') || root.matches('[data_pane="system"]'))
                            ? root
                            : null
                    ) ||
                    document.querySelector('[data-pane="system"],[data_pane="system"]');
                if (!pane) return;

                if (pane.dataset.systemTabsBound !== '1') {
                    pane.dataset.systemTabsBound = '1';
                    pane.querySelectorAll('[data-system-tab-btn]').forEach((btn) => {
                        btn.addEventListener('click', () => activate(pane, btn.dataset.systemTabBtn || 'paths'));
                    });
                }
                activate(pane, pane.dataset.systemActiveTab || 'paths');
            }

            if (!window.__settingsSystemTabsBound) {
                window.__settingsSystemTabsBound = true;
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


def _build_system_pane(cm, s):
    paths = cm.data.get("paths", {})
    security = cm.data.get("security", {})
    storage = s.get("storage", {})
    paths_section = Div(
        H3("Paths & Logging", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2"),
        P(
            "Percorsi runtime locali e politiche base di logging/housekeeping.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
            setting_input(
                "Downloads Directory",
                "paths.downloads_dir",
                paths.get("downloads_dir", "data/local/downloads"),
                "text",
                help_text="Directory locale dei documenti scaricati (manifest + scans + metadata).",
            ),
            setting_input(
                "Exports Directory",
                "paths.exports_dir",
                paths.get("exports_dir", "data/local/exports"),
                "text",
                help_text="Directory locale degli artifact di export (PDF/ZIP) generati dal sistema.",
            ),
            setting_input(
                "Temp Images Directory",
                "paths.temp_dir",
                paths.get("temp_dir", "data/local/temp_images"),
                "text",
                help_text="Directory temporanea per immagini/staging durante pipeline di download ed export.",
            ),
            setting_input(
                "Models Directory",
                "paths.models_dir",
                paths.get("models_dir", "data/local/models"),
                "text",
                help_text="Percorso locale di modelli OCR/AI scaricati o cache di runtime.",
            ),
            setting_input(
                "Logs Directory",
                "paths.logs_dir",
                paths.get("logs_dir", "data/local/logs"),
                "text",
                help_text="Directory dei log applicativi.",
            ),
            setting_input(
                "Snippets Directory",
                "paths.snippets_dir",
                paths.get("snippets_dir", "data/local/snippets"),
                "text",
                help_text="Directory locale degli snippet ritagliati/salvati dallo Studio.",
            ),
            setting_select(
                "Logging Level",
                "settings.logging.level",
                s.get("logging", {}).get("level", "INFO"),
                [("DEBUG", "DEBUG"), ("INFO", "INFO"), ("WARNING", "WARNING"), ("ERROR", "ERROR")],
                help_text="Livello minimo di severità registrato nei log.",
            ),
            setting_number(
                "Temp Cleanup Days",
                "settings.housekeeping.temp_cleanup_days",
                s.get("housekeeping", {}).get("temp_cleanup_days", 7),
                min_val=1,
                max_val=365,
                step_val=1,
                help_text="Finestra retention per cleanup dei file temporanei generici.",
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        **{"data-system-tab-pane": "paths"},
    )

    storage_section = Div(
        H3("Storage & Security", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2"),
        P(
            "Policy di retention per export, thumbnails e staging high-res, piu opzioni di sicurezza.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
            setting_number(
                "Exports Retention Days",
                "settings.storage.exports_retention_days",
                storage.get("exports_retention_days", 30),
                min_val=1,
                max_val=3650,
                step_val=1,
                help_text="Rimuove export vecchi in automatico quando usi gli strumenti di cleanup.",
            ),
            setting_number(
                "Thumbnails Retention Days",
                "settings.storage.thumbnails_retention_days",
                storage.get("thumbnails_retention_days", 14),
                min_val=1,
                max_val=3650,
                step_val=1,
                help_text="Retention della cache miniature usata dalla griglia Export.",
            ),
            setting_number(
                "High-Res Temp Retention (h)",
                "settings.storage.highres_temp_retention_hours",
                storage.get("highres_temp_retention_hours", 6),
                min_val=1,
                max_val=720,
                step_val=1,
                help_text="Retention (ore) delle cartelle temporanee high-res create dagli export remoti.",
            ),
            setting_number(
                "Max Exports Per Item",
                "settings.storage.max_exports_per_item",
                storage.get("max_exports_per_item", 5),
                min_val=1,
                max_val=100,
                step_val=1,
                help_text="Numero massimo di export mantenuti per singolo item prima del pruning locale.",
            ),
            setting_number(
                "Remote Cache Max Bytes",
                "settings.storage.remote_cache.max_bytes",
                ((storage.get("remote_cache") or {}).get("max_bytes", 104857600)),
                min_val=1048576,
                max_val=21474836480,
                step_val=1048576,
                help_text="Dimensione massima della cache remota persistente (byte).",
            ),
            setting_number(
                "Remote Cache Retention (h)",
                "settings.storage.remote_cache.retention_hours",
                ((storage.get("remote_cache") or {}).get("retention_hours", 72)),
                min_val=1,
                max_val=8760,
                step_val=1,
                help_text="Retention ore delle entry cache remota non utilizzate.",
            ),
            setting_number(
                "Remote Cache Max Items",
                "settings.storage.remote_cache.max_items",
                ((storage.get("remote_cache") or {}).get("max_items", 2000)),
                min_val=100,
                max_val=100000,
                step_val=100,
                help_text="Numero massimo di entry conservate nella cache remota.",
            ),
            setting_toggle(
                "Auto Prune On Startup",
                "settings.storage.auto_prune_on_startup",
                storage.get("auto_prune_on_startup", False),
                help_text="Esegue pruning automatico di file temporanei/export secondo policy retention all'avvio.",
            ),
            setting_select(
                "Partial Promotion Mode",
                "settings.storage.partial_promotion_mode",
                storage.get("partial_promotion_mode", "never"),
                [("Mai (resta in temp)", "never"), ("Solo su Pausa", "on_pause")],
                help_text=(
                    "Controlla quando promuovere pagine validate da temp a scans: "
                    "'on_pause' lo fa solo quando un download viene messo in pausa."
                ),
            ),
            setting_toggle(
                "Run Live Tests",
                "settings.testing.run_live_tests",
                s.get("testing", {}).get("run_live_tests", False),
                help_text="Abilita test contro endpoint esterni reali.",
            ),
            setting_input(
                "Allowed Origins",
                "security.allowed_origins",
                ",".join(str(origin) for origin in security.get("allowed_origins", [])),
                help_text="Origini CORS consentite (lista separata da virgole, es. https://dominio-a,https://dominio-b).",
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="hidden",
        **{"data-system-tab-pane": "storage"},
    )

    return Div(
        Div(H3("System & Paths", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3")),
        P(
            "Configura percorsi runtime e policy di retention in due sotto-sezioni operative.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
            Button(
                "Paths & Logging",
                type="button",
                cls="app-btn app-btn-primary",
                **{"data-system-tab-btn": "paths"},
            ),
            Button(
                "Storage & Security",
                type="button",
                cls="app-btn app-btn-neutral",
                **{"data-system-tab-btn": "storage"},
            ),
            cls="flex items-center gap-2 mb-4",
        ),
        paths_section,
        storage_section,
        _system_subtabs_script(),
        cls="p-4",
        data_pane="system",
    )
