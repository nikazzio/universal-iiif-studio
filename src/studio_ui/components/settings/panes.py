import json

from fasthtml.common import H3, Button, Div, Input, Label, Option, P, Script, Select

from studio_ui.library_options import library_options, normalize_library_value
from studio_ui.theme import preset_options, resolve_ui_theme

from .controls import (
    setting_color,
    setting_input,
    setting_number,
    setting_range,
    setting_select,
    setting_textarea,
    setting_toggle,
)


def _pdf_subtabs_script() -> Script:
    """Initialize nested PDF sub-tabs inside Settings > PDF Export pane."""
    return Script(
        """
        (function() {
            function activate(pane, tabName) {
                const target = (tabName || 'defaults').trim();
                pane.dataset.pdfActiveTab = target;
                const buttons = pane.querySelectorAll('[data-pdf-tab-btn]');
                const sections = pane.querySelectorAll('[data-pdf-tab-pane]');
                buttons.forEach((btn) => {
                    const isActive = (btn.dataset.pdfTabBtn || '') === target;
                    btn.classList.toggle('app-btn-primary', isActive);
                    btn.classList.toggle('app-btn-neutral', !isActive);
                });
                sections.forEach((section) => {
                    const isActive = (section.dataset.pdfTabPane || '') === target;
                    section.classList.toggle('hidden', !isActive);
                });
            }

            function bind(root) {
                const pane =
                    (root && root.querySelector && root.querySelector('[data-pane="pdf"]')) ||
                    (root && root.querySelector && root.querySelector('[data_pane="pdf"]')) ||
                    (
                        root &&
                        root.matches &&
                        (root.matches('[data-pane="pdf"]') || root.matches('[data_pane="pdf"]'))
                            ? root
                            : null
                    ) ||
                    document.querySelector('[data-pane="pdf"],[data_pane="pdf"]');
                if (!pane) return;

                if (pane.dataset.pdfTabsBound !== '1') {
                    pane.dataset.pdfTabsBound = '1';
                    const buttons = pane.querySelectorAll('[data-pdf-tab-btn]');
                    buttons.forEach((btn) => {
                        btn.addEventListener('click', () => {
                            activate(pane, btn.dataset.pdfTabBtn || 'defaults');
                        });
                    });
                }
                activate(pane, pane.dataset.pdfActiveTab || 'defaults');
            }

            if (!window.__settingsPdfTabsBound) {
                window.__settingsPdfTabsBound = true;
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


def _pdf_profile_editor_script() -> Script:
    """Bind profile editor actions (select/save/delete) in Settings > PDF Export."""
    return Script(
        """
        (function() {
            function requestPath(evt) {
                try {
                    return (evt && evt.detail && evt.detail.pathInfo && evt.detail.pathInfo.requestPath) || '';
                } catch (_) {
                    return '';
                }
            }

            function sanitizeProfileKey(raw) {
                return String(raw || '')
                    .trim()
                    .toLowerCase()
                    .replace(/[^a-z0-9_-]+/g, '_')
                    .replace(/_+/g, '_')
                    .replace(/^_+|_+$/g, '');
            }

            function setValue(field, value) {
                if (!field) return;
                field.value = value === undefined || value === null ? '' : String(value);
            }

            function setCheckbox(field, value) {
                if (!field) return;
                field.checked = !!value;
            }

            function bind(root) {
                const pane =
                    (root && root.querySelector && root.querySelector('[data-pane="pdf"]')) ||
                    (root && root.querySelector && root.querySelector('[data_pane="pdf"]')) ||
                    (
                        root &&
                        root.matches &&
                        (root.matches('[data-pane="pdf"]') || root.matches('[data_pane="pdf"]'))
                            ? root
                            : null
                    ) ||
                    document.querySelector('[data-pane="pdf"],[data_pane="pdf"]');
                if (!pane) return;

                const form = pane.closest('form.settings-form') || document.querySelector('form.settings-form');
                const select = pane.querySelector('#settings-pdf-profile-select');
                const saveBtn = pane.querySelector('#settings-pdf-profile-save-btn');
                const deleteBtn = pane.querySelector('#settings-pdf-profile-delete-btn');
                const actionInput = pane.querySelector('#settings-pdf-profile-action');
                const selectedInput = pane.querySelector('#settings-pdf-profile-selected');
                const defaultInput = pane.querySelector('#settings-pdf-profile-default');
                const catalogInput = pane.querySelector('#settings-pdf-profile-catalog');
                const keyInput = pane.querySelector('[name="settings.pdf.profiles.editor.key"]');
                const labelInput = pane.querySelector('[name="settings.pdf.profiles.editor.label"]');
                const compressionField = pane.querySelector('[name="settings.pdf.profiles.editor.compression"]');
                const sourceModeField = pane.querySelector('[name="settings.pdf.profiles.editor.image_source_mode"]');
                const maxEdgeField = pane.querySelector('[name="settings.pdf.profiles.editor.image_max_long_edge_px"]');
                const jpegField = pane.querySelector('[name="settings.pdf.profiles.editor.jpeg_quality"]');
                const parallelField = pane.querySelector(
                    '[name="settings.pdf.profiles.editor.max_parallel_page_fetch"]'
                );
                const includeCoverField = pane.querySelector(
                    'input[type="checkbox"][name="settings.pdf.profiles.editor.include_cover"]'
                );
                const includeColophonField = pane.querySelector(
                    'input[type="checkbox"][name="settings.pdf.profiles.editor.include_colophon"]'
                );
                const forceRefetchField = pane.querySelector(
                    'input[type="checkbox"][name="settings.pdf.profiles.editor.force_remote_refetch"]'
                );
                const cleanupField = pane.querySelector(
                    'input[type="checkbox"][name="settings.pdf.profiles.editor.cleanup_temp_after_export"]'
                );
                const makeDefaultField = pane.querySelector(
                    'input[type="checkbox"][name="settings.pdf.profiles.editor.make_default"]'
                );

                if (!form || !select || !actionInput || !selectedInput || !catalogInput) return;

                let catalog = {};
                if (catalogInput.value) {
                    try {
                        catalog = JSON.parse(catalogInput.value);
                    } catch (_) {
                        catalog = {};
                    }
                }

                const balanced = (catalog && catalog.balanced) || {
                    label: 'Balanced',
                    compression: 'Standard',
                    image_source_mode: 'local_balanced',
                    image_max_long_edge_px: 2600,
                    jpeg_quality: 82,
                    max_parallel_page_fetch: 2,
                    include_cover: true,
                    include_colophon: true,
                    force_remote_refetch: false,
                    cleanup_temp_after_export: true
                };
                const defaultKey = String((defaultInput && defaultInput.value) || 'balanced');

                function setDeleteAvailability(enabled) {
                    if (!deleteBtn) return;
                    deleteBtn.disabled = !enabled;
                    deleteBtn.classList.toggle('opacity-40', !enabled);
                    deleteBtn.classList.toggle('cursor-not-allowed', !enabled);
                }

                function applyProfile(key) {
                    const selectedKey = String(key || 'balanced');
                    selectedInput.value = selectedKey;

                    if (selectedKey === '__new__') {
                        if (keyInput) {
                            keyInput.readOnly = false;
                            keyInput.value = '';
                        }
                        setValue(labelInput, balanced.label || 'Custom Profile');
                        setValue(compressionField, balanced.compression || 'Standard');
                        setValue(sourceModeField, balanced.image_source_mode || 'local_balanced');
                        setValue(maxEdgeField, balanced.image_max_long_edge_px || 2600);
                        setValue(jpegField, balanced.jpeg_quality || 82);
                        setValue(parallelField, balanced.max_parallel_page_fetch || 2);
                        setCheckbox(includeCoverField, balanced.include_cover !== false);
                        setCheckbox(includeColophonField, balanced.include_colophon !== false);
                        setCheckbox(forceRefetchField, !!balanced.force_remote_refetch);
                        setCheckbox(cleanupField, balanced.cleanup_temp_after_export !== false);
                        setCheckbox(makeDefaultField, false);
                        setDeleteAvailability(false);
                        return;
                    }

                    const payload = (catalog && catalog[selectedKey]) || balanced;
                    if (keyInput) {
                        keyInput.readOnly = true;
                        keyInput.value = selectedKey;
                    }
                    setValue(labelInput, payload.label || selectedKey);
                    setValue(compressionField, payload.compression || 'Standard');
                    setValue(sourceModeField, payload.image_source_mode || 'local_balanced');
                    setValue(maxEdgeField, payload.image_max_long_edge_px || 0);
                    setValue(jpegField, payload.jpeg_quality || 82);
                    setValue(parallelField, payload.max_parallel_page_fetch || 2);
                    setCheckbox(includeCoverField, payload.include_cover !== false);
                    setCheckbox(includeColophonField, payload.include_colophon !== false);
                    setCheckbox(forceRefetchField, !!payload.force_remote_refetch);
                    setCheckbox(cleanupField, payload.cleanup_temp_after_export !== false);
                    setCheckbox(makeDefaultField, selectedKey === defaultKey);
                    setDeleteAvailability(selectedKey !== 'balanced');
                }

                function submitAction(action) {
                    actionInput.value = action;
                    if (action === 'save' && selectedInput.value === '__new__') {
                        const key = sanitizeProfileKey(keyInput ? keyInput.value : '');
                        if (!key) {
                            window.alert('Inserisci una chiave valida per il nuovo profilo.');
                            actionInput.value = 'none';
                            return;
                        }
                    }
                    if (action === 'delete') {
                        const target = selectedInput.value;
                        if (!target || target === '__new__' || target === 'balanced') {
                            actionInput.value = 'none';
                            return;
                        }
                        if (!window.confirm('Eliminare il profilo selezionato?')) {
                            actionInput.value = 'none';
                            return;
                        }
                    }
                    form.requestSubmit();
                }

                if (pane.dataset.pdfProfileEditorBound !== '1') {
                    pane.dataset.pdfProfileEditorBound = '1';
                    select.addEventListener('change', () => applyProfile(select.value));
                    if (saveBtn) {
                        saveBtn.addEventListener('click', () => submitAction('save'));
                    }
                    if (deleteBtn) {
                        deleteBtn.addEventListener('click', () => submitAction('delete'));
                    }
                }

                if (!window.__settingsPdfProfileRequestBound) {
                    window.__settingsPdfProfileRequestBound = true;
                    document.body.addEventListener('htmx:afterRequest', (evt) => {
                        if (requestPath(evt) !== '/settings/save') return;
                        const paneRef = document.querySelector('[data-pane="pdf"],[data_pane="pdf"]');
                        if (!paneRef) return;
                        const actionField = paneRef.querySelector('#settings-pdf-profile-action');
                        if (actionField) actionField.value = 'none';
                    });
                }

                applyProfile(select.value || defaultKey);
            }

            if (!window.__settingsPdfProfileEditorBound) {
                window.__settingsPdfProfileEditorBound = true;
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
                "Key per Anthopic.",
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
            Input(type="hidden", name="settings.ui.theme_color", value=theme["accent"]),
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
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="general",
    )


def _build_processing_pane(cm, s):
    _ = cm
    system = s.get("system", {})
    pdf = s.get("pdf", {})
    return Div(
        Div(H3("Processing Core", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3")),
        P(
            "Queste opzioni governano il comportamento globale del downloader e il trattamento dei PDF nativi.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
            setting_number(
                "Max Concurrent Downloads",
                "settings.system.max_concurrent_downloads",
                system.get("max_concurrent_downloads", 2),
                min_val=1,
                max_val=16,
                step_val=1,
                help_text="Numero massimo di documenti scaricati in parallelo dal download manager.",
            ),
            setting_number(
                "PDF Viewer DPI",
                "settings.pdf.viewer_dpi",
                pdf.get("viewer_dpi", 150),
                help_text=(
                    "Risoluzione usata quando il sistema estrae JPG da un PDF nativo. "
                    "Valori alti migliorano il dettaglio ma aumentano spazio disco e tempi di processing."
                ),
                min_val=72,
                max_val=600,
                step_val=1,
            ),
            setting_toggle(
                "Prefer Native PDF",
                "settings.pdf.prefer_native_pdf",
                pdf.get("prefer_native_pdf", True),
                help_text=(
                    "Se il manifest espone un PDF nativo, il downloader prova quel flusso come sorgente primaria "
                    "e genera le pagine in scans/ per compatibilità Studio."
                ),
            ),
            setting_toggle(
                "Create PDF from Images",
                "settings.pdf.create_pdf_from_images",
                pdf.get("create_pdf_from_images", False),
                help_text=(
                    "Quando non si usa un PDF nativo, abilita la creazione di un PDF compilato dalle immagini locali "
                    "come artifact aggiuntivo."
                ),
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="performance",
    )


def _build_pdf_pane(cm, s):
    _ = cm
    pdf = s.get("pdf", {})
    cover = pdf.get("cover", {})
    export_cfg = pdf.get("export", {})
    profiles_cfg = pdf.get("profiles", {})
    raw_catalog = profiles_cfg.get("catalog", {}) if isinstance(profiles_cfg, dict) else {}
    profile_catalog = raw_catalog if isinstance(raw_catalog, dict) else {}

    normalized_catalog: dict[str, dict] = {
        str(profile_name): payload for profile_name, payload in profile_catalog.items() if isinstance(payload, dict)
    }
    if "balanced" not in normalized_catalog:
        normalized_catalog["balanced"] = {
            "label": "Balanced",
            "compression": "Standard",
            "include_cover": True,
            "include_colophon": True,
            "image_source_mode": "local_balanced",
            "image_max_long_edge_px": 2600,
            "jpeg_quality": 82,
            "force_remote_refetch": False,
            "cleanup_temp_after_export": True,
            "max_parallel_page_fetch": 2,
        }

    ordered_profile_keys = ["balanced"] + sorted(key for key in normalized_catalog if key and key != "balanced")

    default_profile = str(profiles_cfg.get("default") or "balanced")
    if default_profile not in normalized_catalog:
        default_profile = "balanced"

    profile_options: list[tuple[str, str]] = []
    for profile_key in ordered_profile_keys:
        payload = normalized_catalog.get(profile_key, {})
        label = str(payload.get("label") or profile_key)
        option_label = f"{label} ({profile_key})" if label.lower() != profile_key.lower() else label
        profile_options.append((profile_key, option_label))
    profile_options.append(("__new__", "Nuovo profilo..."))

    active_payload = normalized_catalog.get(default_profile, normalized_catalog.get("balanced", {}))

    defaults_section = Div(
        P(
            "Configura i default globali del flusso PDF e i metadati di copertina riusati in nuovi job.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
            Div(
                Label("Cover Logo", cls="block text-sm font-semibold text-slate-800 dark:text-slate-100 mb-1.5"),
                Div(
                    Input(
                        type="file",
                        id="cover_logo_file_input",
                        cls="settings-field w-full text-sm",
                        data_target_id="cover_logo_path_input",
                    ),
                    Input(
                        type="text",
                        id="cover_logo_path_input",
                        name="settings.pdf.cover.logo_path",
                        value=cover.get("logo_path", ""),
                        placeholder="logo-cover.png",
                        cls="settings-field w-full",
                    ),
                    cls="grid grid-cols-1 md:grid-cols-2 gap-2",
                ),
                P(
                    "Seleziona un file locale: in configurazione viene salvato il path usato dal runtime.",
                    cls="text-xs text-slate-500 dark:text-slate-400 mt-1",
                ),
                cls="mb-4",
            ),
            setting_input(
                "Curatore",
                "settings.pdf.cover.curator",
                cover.get("curator", ""),
                help_text="Nome del curatore o del team editoriale mostrato in copertina.",
            ),
            setting_textarea(
                "Descrizione",
                "settings.pdf.cover.description",
                cover.get("description", ""),
                help_text="Descrizione predefinita usata in copertina quando non sovrascritta nel job.",
            ),
            setting_select(
                "Formato export predefinito",
                "settings.pdf.export.default_format",
                export_cfg.get("default_format", "pdf_images"),
                [
                    ("pdf_images", "PDF (solo immagini)"),
                    ("pdf_searchable", "PDF ricercabile"),
                    ("pdf_facing", "PDF testo a fronte"),
                ],
                help_text=(
                    "Formato predefinito nel tab Export item. "
                    "Puoi sempre cambiarlo per il singolo job prima dell'avvio."
                ),
            ),
            setting_select(
                "Compressione predefinita",
                "settings.pdf.export.default_compression",
                export_cfg.get("default_compression", "Standard"),
                [("High-Res", "High-Res"), ("Standard", "Standard"), ("Light", "Light")],
                help_text="Compressione base applicata se non è selezionato un profilo con parametri specifici.",
            ),
            setting_select(
                "Profilo PDF predefinito",
                "settings.pdf.profiles.default",
                str(profiles_cfg.get("default") or "balanced"),
                [(key, label) for key, label in profile_options if key != "__new__"],
                help_text=(
                    "Profilo applicato di default nello Studio Export. "
                    "La scelta profilo nel singolo item vale solo per il job corrente."
                ),
            ),
            setting_toggle(
                "Includi copertina (default)",
                "settings.pdf.export.include_cover",
                export_cfg.get("include_cover", True),
                help_text="Stato iniziale del toggle copertina nel tab Export item.",
            ),
            setting_toggle(
                "Includi colophon (default)",
                "settings.pdf.export.include_colophon",
                export_cfg.get("include_colophon", True),
                help_text="Stato iniziale del toggle colophon nel tab Export item.",
            ),
            setting_number(
                "Righe descrizione",
                "settings.pdf.export.description_rows",
                export_cfg.get("description_rows", 3),
                min_val=2,
                max_val=8,
                step_val=1,
                help_text="Numero righe iniziali del campo descrizione nel form Export item.",
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        **{"data-pdf-tab-pane": "defaults"},
    )

    profile_select = Div(
        Label("Profilo da configurare", cls="block text-sm font-semibold text-slate-800 dark:text-slate-100 mb-1.5"),
        Select(
            *[
                Option(
                    option_label,
                    value=profile_key,
                    selected=profile_key == default_profile,
                )
                for profile_key, option_label in profile_options
            ],
            id="settings-pdf-profile-select",
            cls="settings-field w-full rounded-xl border px-3 py-2.5",
        ),
        P(
            "Scegli un profilo esistente per modificarlo, oppure 'Nuovo profilo...' per crearne uno.",
            cls="text-xs text-slate-500 dark:text-slate-400 mt-1",
        ),
        cls="mb-4",
    )

    catalog_section = Div(
        H3("Catalogo Profili PDF", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2"),
        P(
            "Ogni profilo definisce strategia immagini, qualita finale, "
            "parallelismo fetch remoto e gestione temporanei.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Input(
            type="hidden",
            id="settings-pdf-profile-action",
            name="settings.pdf.profiles.editor.action",
            value="none",
        ),
        Input(
            type="hidden",
            id="settings-pdf-profile-selected",
            name="settings.pdf.profiles.editor.selected",
            value=default_profile,
        ),
        Input(type="hidden", id="settings-pdf-profile-default", value=default_profile),
        Input(
            type="hidden",
            id="settings-pdf-profile-catalog",
            value=json.dumps(normalized_catalog, separators=(",", ":")),
        ),
        profile_select,
        Div(
            setting_toggle(
                "Includi copertina",
                "settings.pdf.profiles.editor.include_cover",
                active_payload.get("include_cover", True),
                help_text="Default del profilo per l'inclusione della copertina nel PDF finale.",
            ),
            setting_toggle(
                "Includi colophon",
                "settings.pdf.profiles.editor.include_colophon",
                active_payload.get("include_colophon", True),
                help_text="Default del profilo per l'inclusione del colophon tecnico finale.",
            ),
            setting_toggle(
                "Imposta come default globale",
                "settings.pdf.profiles.editor.make_default",
                default_profile == str(profiles_cfg.get("default") or "balanced"),
                help_text="Se attivo, il profilo salvato diventa il default usato nei nuovi export item.",
            ),
            setting_input(
                "Chiave profilo",
                "settings.pdf.profiles.editor.key",
                default_profile,
                help_text=(
                    "Identificatore tecnico del profilo. "
                    "Per profili esistenti e in sola lettura; in modalita nuovo profilo e modificabile."
                ),
                readonly=True,
            ),
            setting_input(
                "Etichetta",
                "settings.pdf.profiles.editor.label",
                active_payload.get("label", default_profile),
                help_text=(
                    "Etichetta leggibile mostrata nel selettore profili del tab Export item. "
                    "Serve a distinguere i preset operativi senza ricordare la chiave tecnica."
                ),
            ),
            setting_select(
                "Compressione",
                "settings.pdf.profiles.editor.compression",
                active_payload.get("compression", "Standard"),
                [("High-Res", "High-Res"), ("Standard", "Standard"), ("Light", "Light")],
                help_text=(
                    "Preset base di qualità/peso PDF. "
                    "I campi lato lungo max e qualità JPEG rifiniscono il risultato finale."
                ),
            ),
            setting_select(
                "Sorgente immagini",
                "settings.pdf.profiles.editor.image_source_mode",
                active_payload.get("image_source_mode", "local_balanced"),
                [
                    ("local_balanced", "Locale bilanciata"),
                    ("local_highres", "Locale high-res"),
                    ("remote_highres_temp", "Remoto high-res temporaneo"),
                ],
                help_text=(
                    "Locale bilanciata usa scans locali ottimizzate; locale high-res usa scans locali al massimo "
                    "dettaglio; remoto high-res temporaneo scarica online solo per il job corrente."
                ),
            ),
            setting_number(
                "Lato lungo max (px)",
                "settings.pdf.profiles.editor.image_max_long_edge_px",
                active_payload.get("image_max_long_edge_px", 2600),
                min_val=0,
                max_val=20000,
                step_val=1,
                help_text=(
                    "Limite del lato lungo per ogni pagina nel PDF. "
                    "0 conserva la risoluzione originale della sorgente selezionata."
                ),
            ),
            setting_number(
                "Qualità JPEG",
                "settings.pdf.profiles.editor.jpeg_quality",
                active_payload.get("jpeg_quality", 82),
                min_val=40,
                max_val=100,
                step_val=1,
                help_text=(
                    "Qualita JPEG incorporata nel PDF (40-100). "
                    "Valori alti migliorano la leggibilita paleografica ma aumentano il peso del file."
                ),
            ),
            setting_number(
                "Fetch pagine parallelo (max)",
                "settings.pdf.profiles.editor.max_parallel_page_fetch",
                active_payload.get("max_parallel_page_fetch", 2),
                min_val=1,
                max_val=8,
                step_val=1,
                help_text=(
                    "Numero massimo di pagine scaricate in parallelo quando il profilo usa "
                    "il fetch remoto high-res temporaneo."
                ),
            ),
            setting_toggle(
                "Forza refetch remoto",
                "settings.pdf.profiles.editor.force_remote_refetch",
                active_payload.get("force_remote_refetch", False),
                help_text=(
                    "Quando la sorgente e remota, forza un nuovo download senza riusare eventuale cache locale."
                ),
            ),
            setting_toggle(
                "Pulisci file temporanei dopo export",
                "settings.pdf.profiles.editor.cleanup_temp_after_export",
                active_payload.get("cleanup_temp_after_export", True),
                help_text="Rimuove automaticamente i file high-res temporanei al termine dell'export.",
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        Div(
            Button(
                "Salva Profilo",
                type="button",
                id="settings-pdf-profile-save-btn",
                cls="app-btn app-btn-primary",
            ),
            Button(
                "Elimina Profilo",
                type="button",
                id="settings-pdf-profile-delete-btn",
                cls=("app-btn border border-rose-700 bg-rose-600 text-white hover:bg-rose-700 disabled:opacity-40"),
            ),
            P(
                "Salva o elimina un profilo e ricarica la pagina per aggiornare subito il catalogo selezionabile.",
                cls="text-xs text-slate-500 dark:text-slate-400",
            ),
            cls="flex flex-wrap items-center gap-2 mt-1",
        ),
        P(
            "Le policy di retention (export, thumbnails, high-res temporanei) "
            "sono nel tab Paths & System > Storage & Security.",
            cls="text-xs text-slate-500 dark:text-slate-400 mt-3",
        ),
        cls="hidden",
        **{"data-pdf-tab-pane": "catalog"},
    )

    return Div(
        Div(H3("PDF Export", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3")),
        P(
            "Flusso consigliato: configura qui i default e i profili; "
            "nel tab Export item scegli solo il profilo da usare.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
            Button(
                "Predefiniti e copertina",
                type="button",
                cls="app-btn app-btn-primary",
                **{"data-pdf-tab-btn": "defaults"},
            ),
            Button(
                "Catalogo Profili",
                type="button",
                cls="app-btn app-btn-neutral",
                **{"data-pdf-tab-btn": "catalog"},
            ),
            cls="flex items-center gap-2 mb-4",
        ),
        defaults_section,
        catalog_section,
        _pdf_subtabs_script(),
        _pdf_profile_editor_script(),
        cls="p-4",
        data_pane="pdf",
    )


def _build_images_pane(cm, s):
    _ = cm
    images = s.get("images", {})
    ocr = s.get("ocr", {})
    defaults = s.get("defaults", {})
    return Div(
        Div(H3("Images & Download", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3")),
        P(
            "Questa sezione governa due aspetti distinti: qualita delle immagini locali "
            "e strategia di fetch dalla sorgente IIIF.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-1",
        ),
        P(
            "Nel tab Export vedi sempre sia la risoluzione locale sia la massima risoluzione online: "
            "puoi lavorare in locale bilanciato e richiedere high-res solo quando serve.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
            setting_select(
                "Download Strategy Mode",
                "settings.images.download_strategy_mode",
                str(images.get("download_strategy_mode") or "balanced"),
                [
                    ("balanced", "Balanced (3000 -> 1740 -> max)"),
                    ("quality_first", "Quality First (max -> 3000 -> 1740)"),
                    ("fast", "Fast (1740 -> 1200 -> max)"),
                    ("archival", "Archival (solo max)"),
                    ("custom", "Custom"),
                ],
                help_text=(
                    "Ordine dei tentativi `size` IIIF per pagina: "
                    "balanced privilegia stabilita/peso, quality_first cerca subito il massimo, "
                    "fast accelera caricamenti, archival usa solo max, custom usa la lista personalizzata."
                ),
            ),
            setting_input(
                "Custom Download Strategy",
                "settings.images.download_strategy_custom",
                ",".join(images.get("download_strategy_custom", images.get("download_strategy", []))),
                help_text=(
                    "Attiva solo con mode=custom. Definisce la sequenza tentativi `size` IIIF; "
                    "accetta interi positivi e `max` (esempio: 3000,1740,max)."
                ),
            ),
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
                help_text=(
                    "Parametro `quality` della URL IIIF (`.../full/.../{quality}.jpg`). "
                    "Non cambia la risoluzione, ma il rendering colore richiesto al server. "
                    "Usa `default` salvo casi specifici (es. `gray` o `bitonal` su stampe monocrome)."
                ),
            ),
            setting_toggle(
                "Probe Remote Max Resolution",
                "settings.images.probe_remote_max_resolution",
                images.get("probe_remote_max_resolution", True),
                help_text=(
                    "Interroga `info.json` e mostra in Studio Export la massima risoluzione disponibile online "
                    "per confrontarla con la copia locale."
                ),
            ),
            setting_range(
                "Viewer JPEG Quality",
                "settings.images.viewer_quality",
                images.get("viewer_quality", 95),
                help_text="Qualita JPEG usata per rendering immagini nel viewer locale e nella navigazione standard.",
                min_val=10,
                max_val=100,
                step_val=1.0,
            ),
            setting_range(
                "Tile Stitch Max RAM (GB)",
                "settings.images.tile_stitch_max_ram_gb",
                images.get("tile_stitch_max_ram_gb", 2),
                help_text=(
                    "Tetto RAM per lo stitching tile quando il server IIIF non fornisce un'immagine singola completa. "
                    "Alzalo solo se processi tavole molto grandi."
                ),
                min_val=0.1,
                max_val=64,
                step_val=0.1,
            ),
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
                help_text=(
                    "Motore OCR predefinito usato dai workflow Studio quando non scegli esplicitamente un backend."
                ),
            ),
            setting_toggle(
                "Kraken Enabled",
                "settings.ocr.kraken_enabled",
                ocr.get("kraken_enabled", False),
                help_text="Abilita il backend Kraken locale nelle opzioni OCR (richiede dipendenze/model disponibili).",
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="images",
    )


def _build_thumbnails_pane(cm, s):
    _ = cm
    thumbs = s.get("thumbnails", {})
    return Div(
        Div(H3("Thumbnail Pipeline", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3")),
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
                help_text="Comma-separated values, used by Studio Export selector.",
            ),
            setting_number(
                "Thumb Max Edge (px)",
                "settings.thumbnails.max_long_edge_px",
                thumbs.get("max_long_edge_px", 320),
                min_val=64,
                max_val=2000,
                step_val=1,
                help_text="Lato lungo massimo delle miniature generate localmente per la griglia Export.",
            ),
            setting_range(
                "Thumb JPEG Quality",
                "settings.thumbnails.jpeg_quality",
                thumbs.get("jpeg_quality", 70),
                min_val=10,
                max_val=100,
                step_val=1,
                help_text="Qualità JPEG delle miniature; valori più alti migliorano resa e aumentano peso cache.",
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="thumbnails",
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
    mirador = viewer.get("mirador", {}).get("openSeadragonOptions", {})
    visual = viewer.get("visual_filters", {})
    defaults = visual.get("defaults", {})
    zoom_section = Div(
        H3("Zoom & Navigation", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2"),
        P(
            "Controlli OpenSeadragon per la profondita di zoom nel viewer Mirador.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
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
            setting_toggle(
                "Auto Prune On Startup",
                "settings.storage.auto_prune_on_startup",
                storage.get("auto_prune_on_startup", False),
                help_text="Esegue pruning automatico di file temporanei/export secondo policy retention all'avvio.",
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
