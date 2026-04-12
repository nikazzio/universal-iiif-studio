from __future__ import annotations

from fasthtml.common import H3, H4, Button, Div, P, Script, Span

from studio_ui.components.settings.controls import (
    setting_number,
    setting_toggle,
)
from universal_iiif_core.network_policy import DEFAULT_NETWORK_SETTINGS


def _network_subtabs_script() -> Script:
    """Initialize nested Network sub-tabs and per-library policy toggles."""
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

            function activateMainTab(pane, tabName) {
                const target = (tabName || 'global').trim();
                pane.dataset.networkActiveTab = target;
                const buttons = pane.querySelectorAll('[data-network-tab-btn]');
                const sections = pane.querySelectorAll('[data-network-tab-pane]');
                buttons.forEach((btn) => {
                    const isActive = (btn.dataset.networkTabBtn || '') === target;
                    btn.classList.toggle('app-btn-primary', isActive);
                    btn.classList.toggle('app-btn-neutral', !isActive);
                });
                sections.forEach((section) => {
                    const isActive = (section.dataset.networkTabPane || '') === target;
                    section.classList.toggle('hidden', !isActive);
                });
            }

            function syncGlobalMirrors(pane) {
                const fieldMap = {
                    max_concurrent_download_jobs: 'settings.network.global.max_concurrent_download_jobs',
                    connect_timeout_s: 'settings.network.global.connect_timeout_s',
                    read_timeout_s: 'settings.network.global.read_timeout_s',
                    transport_retries: 'settings.network.global.transport_retries'
                };

                Object.entries(fieldMap).forEach(([fieldKey, inputName]) => {
                    const input = pane.querySelector(`input[name="${inputName}"]`);
                    if (!input) return;
                    const value = (input.value || '').trim();
                    pane.querySelectorAll(`[data-network-global-field="${fieldKey}"]`).forEach((node) => {
                        node.textContent = value;
                    });
                });
            }

            function syncPolicyFields(pane, policyKey) {
                const policyNode = pane.querySelector(`[data-network-policy="${policyKey}"]`);
                if (!policyNode) return;

                const customName = `settings.network.libraries.${policyKey}.use_custom_policy`;
                const customCheckbox = policyNode.querySelector(`input[type="checkbox"][name="${customName}"]`);
                const customEnabled = customCheckbox ? customCheckbox.checked : false;

                policyNode.querySelectorAll('input, select, textarea').forEach((field) => {
                    const isCustomField = !!field.closest(`[data-network-custom="${policyKey}"]`);
                    field.disabled = isCustomField && !customEnabled;
                });
                policyNode.querySelectorAll(`[data-network-custom="${policyKey}"]`).forEach((block) => {
                    block.classList.toggle('opacity-50', !customEnabled);
                    block.classList.toggle('pointer-events-none', !customEnabled);
                    block.classList.toggle('select-none', !customEnabled);
                });

                const badges = policyNode.querySelectorAll(`[data-network-custom-badge="${policyKey}"]`);
                badges.forEach((badge) => {
                    badge.textContent = customEnabled ? 'Override attivo' : 'Usa default globali';
                    badge.classList.toggle('text-emerald-700', customEnabled);
                    badge.classList.toggle('text-slate-500', !customEnabled);
                });
            }

            function bind(root) {
                const pane =
                    (root && root.querySelector && root.querySelector('[data-pane="network"]')) ||
                    (root && root.querySelector && root.querySelector('[data_pane="network"]')) ||
                    (
                        root &&
                        root.matches &&
                        (root.matches('[data-pane="network"]') || root.matches('[data_pane="network"]'))
                            ? root
                            : null
                    ) ||
                    document.querySelector('[data-pane="network"],[data_pane="network"]');
                if (!pane) return;

                if (pane.dataset.networkTabsBound !== '1') {
                    pane.dataset.networkTabsBound = '1';
                    pane.querySelectorAll('[data-network-tab-btn]').forEach((btn) => {
                        btn.addEventListener('click', () => {
                            activateMainTab(pane, btn.dataset.networkTabBtn || 'global');
                        });
                    });
                    pane
                        .querySelectorAll(
                            [
                                'input[name="settings.network.global.max_concurrent_download_jobs"]',
                                'input[name="settings.network.global.connect_timeout_s"]',
                                'input[name="settings.network.global.read_timeout_s"]',
                                'input[name="settings.network.global.transport_retries"]'
                            ].join(',')
                        )
                        .forEach((input) => {
                            input.addEventListener('input', () => syncGlobalMirrors(pane));
                            input.addEventListener('change', () => syncGlobalMirrors(pane));
                        });
                    pane.querySelectorAll('[data-network-policy]').forEach((node) => {
                        const key = node.dataset.networkPolicy || '';
                        const customSelector =
                            `input[type="checkbox"][name="settings.network.libraries.${key}.use_custom_policy"]`;
                        const customCheckbox = node.querySelector(customSelector);
                        if (customCheckbox) {
                            customCheckbox.addEventListener('change', () => syncPolicyFields(pane, key));
                        }
                        syncPolicyFields(pane, key);
                    });
                } else {
                    pane.querySelectorAll('[data-network-policy]').forEach((node) => {
                        const key = node.dataset.networkPolicy || '';
                        syncPolicyFields(pane, key);
                    });
                }
                syncGlobalMirrors(pane);
                activateMainTab(pane, pane.dataset.networkActiveTab || 'global');
            }

            if (!window.__settingsNetworkTabsBound) {
                window.__settingsNetworkTabsBound = true;
                document.addEventListener('DOMContentLoaded', () => bind(document));
                document.body.addEventListener('htmx:afterRequest', (evt) => {
                    if (requestPath(evt) === '/settings/save' && evt && evt.detail && evt.detail.successful) {
                        bind(document);
                    }
                });
                document.body.addEventListener('htmx:afterSwap', (evt) => {
                    const target = evt && evt.detail ? evt.detail.target : null;
                    bind(target || document);
                });
            }

            bind(document);
        })();
        """
    )


def _network_custom_field(policy_key: str, field) -> Div:
    return Div(
        field,
        cls="transition-opacity duration-150",
        **{"data-network-custom": policy_key},
    )


def _build_network_library_card(*, title: str, policy_key: str, policy_cfg: dict, global_cfg: dict):
    base = f"settings.network.libraries.{policy_key}"
    download_defaults = DEFAULT_NETWORK_SETTINGS["download"]
    global_defaults = DEFAULT_NETWORK_SETTINGS["global"]
    max_jobs = global_cfg.get("max_concurrent_download_jobs", global_defaults["max_concurrent_download_jobs"])
    connect_timeout = global_cfg.get("connect_timeout_s", global_defaults["connect_timeout_s"])
    read_timeout = global_cfg.get("read_timeout_s", global_defaults["read_timeout_s"])
    transport_retries = global_cfg.get("transport_retries", global_defaults["transport_retries"])
    return Div(
        H3(title, cls="text-base font-bold text-slate-800 dark:text-slate-100 mb-2"),
        Div(
            setting_toggle(
                "Usa impostazioni custom",
                f"{base}.use_custom_policy",
                policy_cfg.get("use_custom_policy", False),
            ),
            cls="grid grid-cols-1 gap-4",
        ),
        Div(
            H4("Sempre Globali", cls="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2"),
            Div(
                P(
                    "Max Concurrent Download Jobs: ",
                    Span(str(max_jobs), **{"data-network-global-field": "max_concurrent_download_jobs"}),
                    cls="text-xs text-slate-600 dark:text-slate-300",
                ),
                P(
                    "Connect Timeout (s): ",
                    Span(str(connect_timeout), **{"data-network-global-field": "connect_timeout_s"}),
                    cls="text-xs text-slate-600 dark:text-slate-300",
                ),
                P(
                    "Read Timeout (s): ",
                    Span(str(read_timeout), **{"data-network-global-field": "read_timeout_s"}),
                    cls="text-xs text-slate-600 dark:text-slate-300",
                ),
                P(
                    "Transport Retries: ",
                    Span(str(transport_retries), **{"data-network-global-field": "transport_retries"}),
                    cls="text-xs text-slate-600 dark:text-slate-300",
                ),
                cls="grid grid-cols-1 md:grid-cols-2 gap-2",
            ),
            cls=(
                "p-4 rounded-2xl border border-slate-200/70 dark:border-slate-700/80 "
                "bg-white/60 dark:bg-slate-900/40 mb-4"
            ),
        ),
        Div(
            H4(
                "Override Download (solo con Override attivo)",
                cls="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2",
            ),
            Div(
                _network_custom_field(
                    policy_key,
                    setting_number(
                        "Workers per Job",
                        f"{base}.workers_per_job",
                        policy_cfg.get("workers_per_job", download_defaults["default_workers_per_job"]),
                        min_val=1,
                        max_val=8,
                        step_val=1,
                        help_text="Parallelismo per singolo documento.",
                    ),
                ),
                _network_custom_field(
                    policy_key,
                    setting_number(
                        "Min Delay (s)",
                        f"{base}.min_delay_s",
                        policy_cfg.get("min_delay_s", download_defaults["default_min_delay_s"]),
                        min_val=0.05,
                        max_val=120,
                        step_val=0.05,
                        help_text="Pausa minima tra richieste.",
                    ),
                ),
                _network_custom_field(
                    policy_key,
                    setting_number(
                        "Max Delay (s)",
                        f"{base}.max_delay_s",
                        policy_cfg.get("max_delay_s", download_defaults["default_max_delay_s"]),
                        min_val=0.1,
                        max_val=180,
                        step_val=0.1,
                        help_text="Pausa massima tra richieste.",
                    ),
                ),
                _network_custom_field(
                    policy_key,
                    setting_number(
                        "Retry Attempts",
                        f"{base}.retry_max_attempts",
                        policy_cfg.get("retry_max_attempts", download_defaults["default_retry_max_attempts"]),
                        min_val=1,
                        max_val=10,
                        step_val=1,
                        help_text="Tentativi massimi per pagina.",
                    ),
                ),
                _network_custom_field(
                    policy_key,
                    setting_number(
                        "Backoff Base (s)",
                        f"{base}.backoff_base_s",
                        policy_cfg.get("backoff_base_s", download_defaults["default_backoff_base_s"]),
                        min_val=1,
                        max_val=600,
                        step_val=1,
                        help_text="Attesa base su errori 403/429.",
                    ),
                ),
                _network_custom_field(
                    policy_key,
                    setting_number(
                        "Backoff Cap (s)",
                        f"{base}.backoff_cap_s",
                        policy_cfg.get("backoff_cap_s", download_defaults["default_backoff_cap_s"]),
                        min_val=5,
                        max_val=3600,
                        step_val=1,
                        help_text="Attesa massima su errori 403/429.",
                    ),
                ),
                _network_custom_field(
                    policy_key,
                    setting_toggle(
                        "Respect Retry-After",
                        f"{base}.respect_retry_after",
                        policy_cfg.get("respect_retry_after", download_defaults["respect_retry_after"]),
                        help_text="Usa header Retry-After quando presente.",
                    ),
                ),
                cls="grid grid-cols-1 md:grid-cols-2 gap-4",
            ),
            cls="p-4 rounded-2xl border border-slate-200/70 dark:border-slate-700/80 bg-white/60 dark:bg-slate-900/40",
        ),
        cls="p-4 rounded-2xl border border-slate-200/70 dark:border-slate-700/80 bg-white/60 dark:bg-slate-900/40",
        **{"data-network-policy": policy_key},
    )


def _build_network_pane(cm, s):
    _ = cm
    network = s.get("network", {})
    if not isinstance(network, dict):
        network = {}
    global_cfg = network.get("global", {})
    if not isinstance(global_cfg, dict):
        global_cfg = {}
    download_cfg = network.get("download", {})
    if not isinstance(download_cfg, dict):
        download_cfg = {}
    libraries_cfg = network.get("libraries", {})
    if not isinstance(libraries_cfg, dict):
        libraries_cfg = {}
    defaults = DEFAULT_NETWORK_SETTINGS

    global_section = Div(
        H3("Global Defaults", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2"),
        P(
            "Impostazioni centrali. Le librerie possono overrideare solo il gruppo Download.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
            H4(
                "Sempre Globali (tutte le librerie)",
                cls="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2",
            ),
            Div(
                setting_number(
                    "Max Concurrent Download Jobs",
                    "settings.network.global.max_concurrent_download_jobs",
                    global_cfg.get("max_concurrent_download_jobs", defaults["global"]["max_concurrent_download_jobs"]),
                    min_val=1,
                    max_val=8,
                    step_val=1,
                    help_text="Documenti scaricati in parallelo dal job manager.",
                ),
                setting_number(
                    "Default Workers per Job",
                    "settings.network.download.default_workers_per_job",
                    download_cfg.get("default_workers_per_job", defaults["download"]["default_workers_per_job"]),
                    min_val=1,
                    max_val=8,
                    step_val=1,
                    help_text="Richieste parallele interne per documento.",
                ),
                setting_number(
                    "Connect Timeout (s)",
                    "settings.network.global.connect_timeout_s",
                    global_cfg.get("connect_timeout_s", defaults["global"]["connect_timeout_s"]),
                    min_val=2,
                    max_val=120,
                    step_val=1,
                    help_text="Timeout di apertura connessione.",
                ),
                setting_number(
                    "Read Timeout (s)",
                    "settings.network.global.read_timeout_s",
                    global_cfg.get("read_timeout_s", defaults["global"]["read_timeout_s"]),
                    min_val=5,
                    max_val=300,
                    step_val=1,
                    help_text="Timeout lettura risposta HTTP.",
                ),
                cls="grid grid-cols-1 md:grid-cols-2 gap-4",
            ),
            cls=(
                "p-4 rounded-2xl border border-slate-200/70 dark:border-slate-700/80 "
                "bg-white/60 dark:bg-slate-900/40 mb-4"
            ),
        ),
        Div(
            H4(
                "Download Default (usato quando override libreria OFF)",
                cls="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2",
            ),
            Div(
                setting_number(
                    "Default Min Delay (s)",
                    "settings.network.download.default_min_delay_s",
                    download_cfg.get("default_min_delay_s", defaults["download"]["default_min_delay_s"]),
                    min_val=0.05,
                    max_val=120,
                    step_val=0.05,
                    help_text="Pausa minima tra richieste.",
                ),
                setting_number(
                    "Default Max Delay (s)",
                    "settings.network.download.default_max_delay_s",
                    download_cfg.get("default_max_delay_s", defaults["download"]["default_max_delay_s"]),
                    min_val=0.1,
                    max_val=180,
                    step_val=0.1,
                    help_text="Pausa massima tra richieste.",
                ),
                setting_number(
                    "Default Retry Attempts",
                    "settings.network.download.default_retry_max_attempts",
                    download_cfg.get("default_retry_max_attempts", defaults["download"]["default_retry_max_attempts"]),
                    min_val=1,
                    max_val=10,
                    step_val=1,
                    help_text="Tentativi massimi per pagina.",
                ),
                setting_number(
                    "Default Backoff Base (s)",
                    "settings.network.download.default_backoff_base_s",
                    download_cfg.get("default_backoff_base_s", defaults["download"]["default_backoff_base_s"]),
                    min_val=1,
                    max_val=600,
                    step_val=1,
                    help_text="Attesa base su errori 403/429.",
                ),
                setting_number(
                    "Default Backoff Cap (s)",
                    "settings.network.download.default_backoff_cap_s",
                    download_cfg.get("default_backoff_cap_s", defaults["download"]["default_backoff_cap_s"]),
                    min_val=5,
                    max_val=3600,
                    step_val=1,
                    help_text="Attesa massima su errori 403/429.",
                ),
                setting_toggle(
                    "Respect Retry-After",
                    "settings.network.download.respect_retry_after",
                    download_cfg.get("respect_retry_after", defaults["download"]["respect_retry_after"]),
                    help_text="Usa Retry-After quando presente.",
                ),
                cls="grid grid-cols-1 md:grid-cols-2 gap-4",
            ),
            cls="p-4 rounded-2xl border border-slate-200/70 dark:border-slate-700/80 bg-white/60 dark:bg-slate-900/40",
        ),
        **{"data-network-tab-pane": "global"},
    )

    gallica_section = Div(
        _build_network_library_card(
            title="Gallica (BnF)",
            policy_key="gallica",
            policy_cfg=libraries_cfg.get("gallica", defaults["libraries"]["gallica"]),
            global_cfg=global_cfg,
        ),
        cls="hidden",
        **{"data-network-tab-pane": "gallica"},
    )

    vaticana_section = Div(
        _build_network_library_card(
            title="Vaticana (BAV)",
            policy_key="vaticana",
            policy_cfg=libraries_cfg.get("vaticana", defaults["libraries"]["vaticana"]),
            global_cfg=global_cfg,
        ),
        cls="hidden",
        **{"data-network-tab-pane": "vaticana"},
    )

    bodleian_section = Div(
        _build_network_library_card(
            title="Bodleian (Oxford)",
            policy_key="bodleian",
            policy_cfg=libraries_cfg.get("bodleian", defaults["libraries"]["bodleian"]),
            global_cfg=global_cfg,
        ),
        cls="hidden",
        **{"data-network-tab-pane": "bodleian"},
    )

    institut_section = Div(
        _build_network_library_card(
            title="Institut de France (Bibnum)",
            policy_key="institut_de_france",
            policy_cfg=libraries_cfg.get(
                "institut_de_france",
                defaults["libraries"]["institut_de_france"],
            ),
            global_cfg=global_cfg,
        ),
        cls="hidden",
        **{"data-network-tab-pane": "institut_de_france"},
    )

    return Div(
        Div(H3("Network & Libraries", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3")),
        P(
            ("1) imposta i Global Defaults. 2) entra in una libreria e abilita override solo se serve."),
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
            Button(
                "Global Defaults",
                type="button",
                cls="app-btn app-btn-primary",
                **{"data-network-tab-btn": "global"},
            ),
            Button(
                "Gallica",
                type="button",
                cls="app-btn app-btn-neutral",
                **{"data-network-tab-btn": "gallica"},
            ),
            Button(
                "Vaticana",
                type="button",
                cls="app-btn app-btn-neutral",
                **{"data-network-tab-btn": "vaticana"},
            ),
            Button(
                "Bodleian",
                type="button",
                cls="app-btn app-btn-neutral",
                **{"data-network-tab-btn": "bodleian"},
            ),
            Button(
                "Institut",
                type="button",
                cls="app-btn app-btn-neutral",
                **{"data-network-tab-btn": "institut_de_france"},
            ),
            cls="flex items-center flex-wrap gap-2 mb-4",
        ),
        global_section,
        gallica_section,
        vaticana_section,
        bodleian_section,
        institut_section,
        _network_subtabs_script(),
        cls="p-4",
        data_pane="network",
    )
