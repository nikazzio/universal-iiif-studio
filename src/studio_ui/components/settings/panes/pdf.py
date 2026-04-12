from __future__ import annotations

import json

from fasthtml.common import H3, Button, Div, Input, Label, Option, P, Script, Select

from studio_ui.components.settings.controls import (
    setting_input,
    setting_number,
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
