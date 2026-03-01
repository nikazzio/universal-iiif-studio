"""Base Layout Component.

Shell HTML con sidebar, headers per Tailwind/HTMX/Mirador, tema chiaro/scuro, e area contenuto principale.
"""

import json

from fasthtml.common import A, Body, Button, Div, Head, Html, Img, Link, Main, Meta, Nav, Script, Title

from studio_ui.config import get_setting
from studio_ui.theme import mix_hex, parse_hex_rgb, readable_ink, resolve_ui_theme
from universal_iiif_core import __version__


def _tailwind_theme_script(primary: str, accent: str) -> str:
    primary_scale = {
        "50": mix_hex(primary, "#FFFFFF", 0.90),
        "500": primary,
        "600": mix_hex(primary, "#000000", 0.14),
        "700": mix_hex(primary, "#000000", 0.24),
        "900": mix_hex(primary, "#000000", 0.42),
    }
    accent_scale = {
        "50": mix_hex(accent, "#FFFFFF", 0.88),
        "500": accent,
        "600": mix_hex(accent, "#000000", 0.14),
        "700": mix_hex(accent, "#000000", 0.24),
        "900": mix_hex(accent, "#000000", 0.42),
    }
    return (
        "if (typeof tailwind !== 'undefined') {"
        "tailwind.config = {"
        "darkMode: 'class',"
        "theme: {extend: {colors: {"
        f"primary: {json.dumps(primary_scale)},"
        f"accent: {json.dumps(accent_scale)}"
        "}}}"
        "};"
        "}"
    )


def _library_nav_filters_bootstrap_script(default_mode: str) -> str:
    safe_mode = "archivio" if str(default_mode or "").strip().lower() == "archivio" else "operativa"
    return f"""
        (function() {{
            const STORAGE_KEY = 'ui.library.filters.v1';
            const DEFAULT_MODE = {json.dumps(safe_mode)};
            const FILTER_KEYS = [
                'q', 'state', 'library_filter', 'category', 'mode', 'view', 'action_required', 'sort_by'
            ];

            function normalize(raw) {{
                const base = {{
                    q: '',
                    state: '',
                    library_filter: '',
                    category: '',
                    mode: DEFAULT_MODE,
                    view: 'grid',
                    action_required: '0',
                    sort_by: ''
                }};
                const src = (raw && typeof raw === 'object') ? raw : {{}};
                FILTER_KEYS.forEach((key) => {{
                    base[key] = String(src[key] || '').trim();
                }});
                if (!base.mode) base.mode = DEFAULT_MODE;
                if (!base.view) base.view = 'grid';
                if (!base.action_required) base.action_required = '0';
                return base;
            }}

            function readSavedFilters() {{
                try {{
                    const raw = localStorage.getItem(STORAGE_KEY);
                    if (!raw) return null;
                    return normalize(JSON.parse(raw));
                }} catch (_e) {{
                    return null;
                }}
            }}

            function hasMeaningfulFilters(data) {{
                const f = normalize(data);
                return Boolean(
                    f.q ||
                    f.state ||
                    f.library_filter ||
                    f.category ||
                    f.sort_by ||
                    f.mode !== DEFAULT_MODE ||
                    f.view !== 'grid' ||
                    f.action_required !== '0'
                );
            }}

            function toQuery(data) {{
                const f = normalize(data);
                const params = new URLSearchParams();
                if (f.q) params.set('q', f.q);
                if (f.state) params.set('state', f.state);
                if (f.library_filter) params.set('library_filter', f.library_filter);
                if (f.category) params.set('category', f.category);
                if (f.sort_by) params.set('sort_by', f.sort_by);
                if (f.mode !== DEFAULT_MODE) params.set('mode', f.mode);
                if (f.view !== 'grid') params.set('view', f.view);
                if (f.action_required !== '0') params.set('action_required', f.action_required);
                return params.toString();
            }}

            function resolveSavedQuery() {{
                const saved = readSavedFilters();
                if (!saved || !hasMeaningfulFilters(saved)) return '';
                return toQuery(saved);
            }}

            const isLibraryPath = (window.location.pathname || '') === '/library';
            const hasQuery = (window.location.search || '').length > 1;
            if (isLibraryPath && !hasQuery) {{
                const query = resolveSavedQuery();
                if (query) {{
                    window.location.replace('/library?' + query);
                    return;
                }}
            }}

            if (window.__libraryNavFilterBootstrapBound) return;
            window.__libraryNavFilterBootstrapBound = true;
            document.addEventListener('click', function(event) {{
                const link = event.target && event.target.closest
                    ? event.target.closest('a[data-nav-key="library"]')
                    : null;
                if (!link) return;
                const href = String(link.getAttribute('href') || '');
                if (!href || href.indexOf('/library') !== 0 || href.indexOf('?') !== -1) return;
                const query = resolveSavedQuery();
                if (!query) return;
                const targetUrl = '/library?' + query;
                link.setAttribute('href', targetUrl);
                if (link.hasAttribute('hx-get')) {{
                    link.setAttribute('hx-get', targetUrl);
                }}
            }}, true);
        }})();
    """


def base_layout(title: str, content, active_page: str = "") -> Html:
    """Generate base page layout with sidebar, dark mode toggle, and headers."""
    theme = resolve_ui_theme(
        {
            "theme_preset": get_setting("ui.theme_preset", ""),
            "theme_primary_color": get_setting("ui.theme_primary_color", ""),
            "theme_accent_color": get_setting("ui.theme_accent_color", ""),
            "theme_color": get_setting("ui.theme_color", ""),
        }
    )
    primary = theme["primary"]
    accent = theme["accent"]
    primary_rgb = parse_hex_rgb(primary)
    accent_rgb = parse_hex_rgb(accent)
    primary_ink = readable_ink(primary)
    accent_ink = readable_ink(accent)
    library_default_mode = str(get_setting("library.default_mode", "operativa"))

    return Html(
        Head(
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Title(title),
            # Tailwind CSS CDN
            Script(src="https://cdn.tailwindcss.com"),
            # Tailwind configuration
            Script(_tailwind_theme_script(primary, accent)),
            # HTMX
            Script(src="https://unpkg.com/htmx.org@1.9.10"),
            # Mirador
            Link(rel="stylesheet", href="https://unpkg.com/mirador@latest/dist/mirador.min.css"),
            Link(rel="icon", href="/assets/morte_tamburo.png"),
            Script(src="https://unpkg.com/mirador@latest/dist/mirador.min.js"),
            # Cropper.js (For snippets)
            Link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.css"),
            Script(src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.js"),
            # Theme + sidebar state initialization (run early to avoid layout flash)
            Script("""
                (function() {
                    const root = document.documentElement;
                    const theme = localStorage.getItem('theme') || 'light';
                    if (theme === 'dark') root.classList.add('dark');
                    if (localStorage.getItem('sidebar-collapsed') === 'true') {
                        root.classList.add('sidebar-collapsed');
                    }
                })();
            """),
            Script(_library_nav_filters_bootstrap_script(library_default_mode)),
            _style_tag(),
        ),
        Body(
            Div(
                _sidebar(active_page),
                Main(
                    content,
                    id="app-main",
                    hx_history_elt="true",
                    cls="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900 transition-colors duration-200",
                ),
                cls="flex h-screen overflow-hidden",
            ),
            Div(
                id="studio-toast-holder",
                cls=(
                    "pointer-events-none fixed top-4 right-4 z-50 flex w-[min(420px,95vw)] flex-col gap-2 items-stretch"
                ),
            ),
            Script("""
                (function () {
                    if (window.__studioToastSystemBound) return;
                    window.__studioToastSystemBound = true;

                    const ENTER_FROM = ['opacity-0', 'translate-y-2', 'scale-95'];
                    const ENTER_TO = ['opacity-100', 'translate-y-0', 'scale-100'];
                    const EXIT_TO = ['opacity-0', 'translate-y-2', 'scale-95'];
                    const CLOSE_SELECTOR = '[data-toast-close],[data_toast_close]';

                    function dismissToast(toast) {
                        if (!toast) return;
                        const closingFlag = toast.getAttribute('data-toast-closing')
                            || toast.getAttribute('data_toast_closing');
                        if (closingFlag === 'true') return;
                        toast.setAttribute('data-toast-closing', 'true');
                        toast.classList.remove(...ENTER_TO);
                        toast.classList.add(...EXIT_TO);
                        window.setTimeout(() => {
                            if (toast && toast.parentNode) toast.remove();
                        }, 250);
                    }

                    function resolveTimeoutMs(toast) {
                        const raw = toast.getAttribute('data-toast-timeout')
                            || toast.getAttribute('data_toast_timeout')
                            || '3000';
                        const parsed = Number.parseInt(raw, 10);
                        if (!Number.isFinite(parsed)) return 3000;
                        return Math.min(15000, Math.max(1000, parsed));
                    }

                    function initToast(toast) {
                        if (!toast) return;
                        const readyFlag = toast.getAttribute('data-toast-ready')
                            || toast.getAttribute('data_toast_ready');
                        if (readyFlag === 'true') return;
                        toast.setAttribute('data-toast-ready', 'true');
                        toast.classList.add(...ENTER_FROM);
                        window.requestAnimationFrame(() => {
                            toast.classList.remove(...ENTER_FROM);
                            toast.classList.add(...ENTER_TO);
                        });
                        window.setTimeout(() => dismissToast(toast), resolveTimeoutMs(toast));
                    }

                    function initToastsIn(root) {
                        if (!root || typeof root.querySelectorAll !== 'function') return;
                        root.querySelectorAll('.studio-toast-entry').forEach(initToast);
                    }

                    function bindToastObserver() {
                        const holder = document.getElementById('studio-toast-holder');
                        if (!holder || holder.dataset.toastObserverBound === 'true') return;
                        holder.dataset.toastObserverBound = 'true';

                        const observer = new MutationObserver((mutations) => {
                            mutations.forEach((mutation) => {
                                mutation.addedNodes.forEach((node) => {
                                    if (!(node instanceof Element)) return;
                                    if (node.classList.contains('studio-toast-entry')) {
                                        initToast(node);
                                        return;
                                    }
                                    initToastsIn(node);
                                });
                            });
                        });
                        observer.observe(holder, { childList: true });
                        initToastsIn(holder);

                        if (holder.dataset.toastClickBound !== 'true') {
                            holder.addEventListener('click', (event) => {
                                const closeBtn = event.target.closest(CLOSE_SELECTOR);
                                if (!closeBtn) return;
                                const toast = closeBtn.closest('.studio-toast-entry');
                                if (toast) dismissToast(toast);
                            });
                            holder.dataset.toastClickBound = 'true';
                        }
                    }

                    document.addEventListener('DOMContentLoaded', bindToastObserver);
                    document.body.addEventListener('htmx:afterSwap', bindToastObserver);
                    document.body.addEventListener('htmx:oobAfterSwap', (event) => {
                        bindToastObserver();
                        initToastsIn(event.target || document);
                    });
                })();
            """),
            style=(
                f"--app-primary: {primary};"
                f"--app-accent: {accent};"
                f"--app-primary-rgb: {primary_rgb[0]}, {primary_rgb[1]}, {primary_rgb[2]};"
                f"--app-accent-rgb: {accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]};"
                f"--app-primary-ink: {primary_ink};"
                f"--app-accent-ink: {accent_ink};"
            ),
            cls="antialiased bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100",
        ),
    )


def _sidebar(active_page: str = "") -> Nav:
    nav_items = [
        ("discovery", "Discovery", "/discovery", "🔍"),
        ("library", "Libreria", "/library", "📚"),
        ("export", "Export", "/export", "📄"),
        ("settings", "Impostazioni", "/settings", "⚙️"),
    ]

    return Nav(
        Div(
            Div(
                Div(
                    Img(src="/assets/morte_tamburo.png", cls="w-10 h-10 rounded-full border border-white/30 shadow-sm"),
                    Div(
                        Div("Universal IIIF", cls="text-xl font-bold text-white leading-tight"),
                        Div("Downloader & Studio", cls="text-xs uppercase tracking-[0.3em] text-gray-400"),
                        cls="flex flex-col leading-tight sidebar-brand-text",
                    ),
                    cls="flex items-center gap-3",
                ),
                Button(
                    "☰",
                    onclick="toggleSidebar()",
                    cls="text-2xl focus:outline-none",
                    id="sidebar-toggle",
                    aria_pressed="false",
                    title="Comprimi/espandi menu",
                ),
                cls="flex items-center justify-between mb-6",
            ),
            cls="sidebar-brand mb-6 pb-4 border-b border-gray-700",
        ),
        Div(
            *[
                A(
                    Div(icon, cls="sidebar-icon text-2xl"),
                    Div(label, cls="sidebar-label font-medium"),
                    href=url,
                    hx_get=url,
                    hx_target="#app-main",
                    hx_swap="innerHTML",
                    hx_push_url="true",
                    data_nav_link="true",
                    data_nav_key=key,
                    cls=_sidebar_link_classes(),
                    **({"aria_current": "page"} if key == active_page else {}),
                )
                for key, label, url, icon in nav_items
            ],
            cls="space-y-1 flex-1",
        ),
        Button(
            Div(
                Div("☀️", id="light-icon", cls="text-xl"),
                Div("🌙", id="dark-icon", cls="text-xl hidden"),
                cls="flex items-center justify-center",
            ),
            onclick="toggleTheme()",
            cls="w-full py-3 px-4 rounded bg-gray-700 hover:bg-gray-600 transition-colors mb-3 text-white",
        ),
        Div(
            Div(f"v{__version__} → FastHTML", cls="text-xs text-gray-500"),
            cls="pt-4 border-t border-gray-700 sidebar-footer",
        ),
        Script("""
            function toggleTheme() {
                const html = document.documentElement;
                const isDark = html.classList.contains('dark');
                if (isDark) {
                    html.classList.remove('dark');
                    localStorage.setItem('theme', 'light');
                    document.getElementById('light-icon').classList.remove('hidden');
                    document.getElementById('dark-icon').classList.add('hidden');
                } else {
                    html.classList.add('dark');
                    localStorage.setItem('theme', 'dark');
                    document.getElementById('light-icon').classList.add('hidden');
                    document.getElementById('dark-icon').classList.remove('hidden');
                }
            }
            window.addEventListener('DOMContentLoaded', () => {
                const isDark = document.documentElement.classList.contains('dark');
                if (isDark) {
                    document.getElementById('light-icon').classList.add('hidden');
                    document.getElementById('dark-icon').classList.remove('hidden');
                }
            });
        """),
        Script("""
            function setSidebarCollapse(collapsed) {
                const root = document.documentElement;
                root.classList.toggle('sidebar-collapsed', collapsed);
                localStorage.setItem('sidebar-collapsed', collapsed ? 'true' : 'false');
                const toggle = document.getElementById('sidebar-toggle');
                if (toggle) toggle.setAttribute('aria-pressed', collapsed ? 'true' : 'false');
            }
            function toggleSidebar() {
                const root = document.documentElement;
                setSidebarCollapse(!root.classList.contains('sidebar-collapsed'));
            }
            function syncActiveNav(pathname) {
                const normalizedPath = pathname.startsWith('/studio') ? '/library' : pathname;
                const links = document.querySelectorAll('[data-nav-link]');
                links.forEach((link) => {
                    const isActive = link.getAttribute('href') === normalizedPath;
                    if (isActive) {
                        link.setAttribute('aria-current', 'page');
                    } else {
                        link.removeAttribute('aria-current');
                    }
                });
            }
            window.addEventListener('DOMContentLoaded', () => {
                setSidebarCollapse(document.documentElement.classList.contains('sidebar-collapsed'));
                syncActiveNav(window.location.pathname);
            });
            document.addEventListener('htmx:afterSwap', (event) => {
                if (event.detail?.target?.id !== 'app-main') return;
                syncActiveNav(window.location.pathname);
            });
            window.addEventListener('popstate', () => {
                syncActiveNav(window.location.pathname);
            });
        """),
        # Global settings tabs initializer (works for swapped fragments)
        Script("""
            // Initialize tab UI for settings pages. This function is global so
            // it can be invoked after HTMX swaps content into #app-main.
            (function(){
                const paneSelector = '[data_pane],[data-pane]';
                const tabSelector = '[data_tab],[data-tab]';
                const settingsRootSelector = '.settings-shell';

                function readTabFromUrl() {
                    try {
                        const url = new URL(window.location.href);
                        const queryTab = url.searchParams.get('tab');
                        if (queryTab) return queryTab;
                        const hash = window.location.hash || '';
                        if (hash.startsWith('#tab=')) return decodeURIComponent(hash.slice(5));
                        if (hash.length > 1) return decodeURIComponent(hash.slice(1));
                    } catch (e) {
                        console.warn('readTabFromUrl error', e);
                    }
                    return null;
                }

                function writeTabToUrl(tabName) {
                    if (!tabName) return;
                    try {
                        const url = new URL(window.location.href);
                        url.searchParams.set('tab', tabName);
                        const next = url.pathname + '?' + url.searchParams.toString() + url.hash;
                        window.history.replaceState(window.history.state, '', next);
                    } catch (e) {
                        console.warn('writeTabToUrl error', e);
                    }
                }

                function activateTabByName(name, root=document) {
                    root.querySelectorAll(paneSelector).forEach(p => p.style.display = 'none');
                    root.querySelectorAll(tabSelector).forEach(b => b.classList.remove('settings-tab-active'));
                    const pane = root.querySelector('[data-pane="' + name + '"]') ||
                        root.querySelector('[data_pane="' + name + '"]');
                    const btn = root.querySelector('[data-tab="' + name + '"]') ||
                        root.querySelector('[data_tab="' + name + '"]');
                    if (pane) pane.style.display = 'block';
                    if (btn) btn.classList.add('settings-tab-active');
                    return !!(pane && btn);
                }

                function initSettingsTabs(root=document) {
                    const isRootSettingsShell = root.matches && root.matches(settingsRootSelector);
                    const settingsRoot = root.querySelector(settingsRootSelector)
                        || (isRootSettingsShell ? root : null);
                    if (!settingsRoot) return;
                    const panes = settingsRoot.querySelectorAll(paneSelector);
                    if (!panes.length) return;
                    panes.forEach((p, i) => p.style.display = (i === 0) ? 'block' : 'none');
                    const tabs = settingsRoot.querySelectorAll(tabSelector);
                    tabs.forEach(b => b.classList.remove('settings-tab-active'));
                    const firstTab = settingsRoot.querySelector(tabSelector);
                    if (firstTab) firstTab.classList.add('settings-tab-active');
                    const requestedTab = readTabFromUrl();
                    if (requestedTab) {
                        activateTabByName(requestedTab, settingsRoot);
                    } else {
                        const selectedName = firstTab
                            ? (firstTab.getAttribute('data-tab') || firstTab.getAttribute('data_tab'))
                            : null;
                        if (selectedName) writeTabToUrl(selectedName);
                    }
                }

                // Delegated click handler bound once on document
                if (!document._settingsTabsBoundGlobal) {
                    document.addEventListener('click', function(e){
                        const btn = e.target.closest(tabSelector);
                        if (!btn) return;
                        const settingsRoot = btn.closest(settingsRootSelector);
                        if (!settingsRoot) return;
                        const name = btn.getAttribute('data-tab') || btn.getAttribute('data_tab');
                        if (!name) return;
                        if (activateTabByName(name, settingsRoot)) {
                            writeTabToUrl(name);
                        }
                    });
                    document._settingsTabsBoundGlobal = true;
                }

                // Run on initial load
                window.addEventListener('DOMContentLoaded', () => initSettingsTabs());

                // Re-run after HTMX swaps into #app-main
                document.addEventListener('htmx:afterSwap', (evt) => {
                    try {
                        if (evt.detail && evt.detail.target && evt.detail.target.id === 'app-main') {
                            initSettingsTabs(evt.detail.target);
                        }
                    } catch (e) {
                        console.warn('initSettingsTabs error', e);
                    }
                });
            })();
        """),
        id="app-sidebar",
        cls="sidebar w-64 bg-gray-800 dark:bg-gray-950 text-white p-6 flex flex-col transition-all duration-200",
    )


def _sidebar_link_classes() -> str:
    return "sidebar-link flex items-center gap-3 py-3 px-4 rounded mb-2 transition-all duration-200"


def _style_tag():
    from fasthtml.common import NotStr

    parts = [
        "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');\n",
        ":root { --app-primary: #4f46e5; --app-accent: #e8a6b6; --app-primary-rgb: 79, 70, 229; "
        "--app-accent-rgb: 232, 166, 182; --app-primary-ink: #f8fafc; --app-accent-ink: #0f172a; }\n",
        "body { font-family: 'Inter', sans-serif; }\n",
        ".sidebar-link { transition: all 0.2s ease; }\n",
        ".app-btn { display: inline-flex; align-items: center; justify-content: center; gap: 0.35rem; "
        "padding: 0.52rem 0.82rem; border-radius: 0.62rem; border: 1px solid transparent; "
        "font-size: 0.875rem; font-weight: 600; line-height: 1.1; text-decoration: none; "
        "transition: all 0.15s ease; cursor: pointer; }\n",
        ".app-btn:hover { transform: translateY(-1px); }\n",
        ".app-btn:focus-visible { outline: 2px solid rgba(var(--app-accent-rgb), 0.45); outline-offset: 2px; }\n",
        ".app-btn-primary { background: var(--app-primary); color: var(--app-primary-ink); "
        "border-color: rgba(var(--app-primary-rgb), 0.62); }\n",
        ".app-btn-primary:hover { filter: brightness(0.95); }\n",
        ".app-btn-accent { background: var(--app-accent); color: var(--app-accent-ink); "
        "border-color: rgba(var(--app-accent-rgb), 0.62); }\n",
        ".app-btn-accent:hover { filter: brightness(0.95); }\n",
        ".app-btn-neutral { background: rgba(var(--app-primary-rgb), 0.10); color: #334155; "
        "border-color: rgba(var(--app-primary-rgb), 0.35); }\n",
        ".app-btn-neutral:hover { background: rgba(var(--app-primary-rgb), 0.18); }\n",
        ".dark .app-btn-neutral { background: rgba(var(--app-primary-rgb), 0.22); color: #e2e8f0; "
        "border-color: rgba(var(--app-primary-rgb), 0.45); }\n",
        ".dark .app-btn-neutral:hover { background: rgba(var(--app-primary-rgb), 0.30); }\n",
        ".app-btn-info { background: rgba(var(--app-accent-rgb), 0.12); color: #1e3a8a; "
        "border-color: rgba(var(--app-accent-rgb), 0.42); }\n",
        ".app-btn-info:hover { background: rgba(var(--app-accent-rgb), 0.20); }\n",
        ".dark .app-btn-info { color: #dbeafe; }\n",
        ".app-btn-success { background: #e8f8ef; color: #166534; border-color: #86efac; }\n",
        ".app-btn-success:hover { background: #d2f3df; }\n",
        ".dark .app-btn-success { background: rgba(34, 197, 94, 0.24); color: #bbf7d0; "
        "border-color: rgba(34, 197, 94, 0.45); }\n",
        ".dark .app-btn-success:hover { background: rgba(34, 197, 94, 0.32); }\n",
        ".app-btn-warning { background: #fff6e9; color: #92400e; border-color: #fdba74; }\n",
        ".app-btn-warning:hover { background: #ffedd5; }\n",
        ".dark .app-btn-warning { background: rgba(245, 158, 11, 0.24); color: #fde68a; "
        "border-color: rgba(245, 158, 11, 0.45); }\n",
        ".dark .app-btn-warning:hover { background: rgba(245, 158, 11, 0.32); }\n",
        ".app-btn-danger { background: #fdecec; color: #991b1b; border-color: #fca5a5; }\n",
        ".app-btn-danger:hover { background: #fee2e2; }\n",
        ".dark .app-btn-danger { background: rgba(239, 68, 68, 0.24); color: #fecaca; "
        "border-color: rgba(239, 68, 68, 0.45); }\n",
        ".dark .app-btn-danger:hover { background: rgba(239, 68, 68, 0.32); }\n",
        ".app-btn-muted { background: rgba(148, 163, 184, 0.18); color: #64748b; "
        "border-color: rgba(148, 163, 184, 0.35); "
        "cursor: not-allowed; pointer-events: none; }\n",
        ".dark .app-btn-muted { background: rgba(148, 163, 184, 0.16); color: #94a3b8; "
        "border-color: rgba(148, 163, 184, 0.28); }\n",
        ".app-chip { display: inline-flex; align-items: center; padding: 0.28rem 0.56rem; border-radius: 0.56rem; "
        "border: 1px solid transparent; font-size: 0.75rem; font-weight: 600; line-height: 1.2; }\n",
        ".app-chip-neutral { background: rgba(148, 163, 184, 0.16); color: #334155; "
        "border-color: rgba(148, 163, 184, 0.35); }\n",
        ".dark .app-chip-neutral { background: rgba(148, 163, 184, 0.18); color: #e2e8f0; "
        "border-color: rgba(148, 163, 184, 0.30); }\n",
        ".app-chip-primary { background: rgba(var(--app-primary-rgb), 0.16); color: #1e293b; "
        "border-color: rgba(var(--app-primary-rgb), 0.38); }\n",
        ".dark .app-chip-primary { background: rgba(var(--app-primary-rgb), 0.24); color: #f1f5f9; "
        "border-color: rgba(var(--app-primary-rgb), 0.46); }\n",
        ".app-chip-accent { background: rgba(var(--app-accent-rgb), 0.18); color: #1e293b; "
        "border-color: rgba(var(--app-accent-rgb), 0.42); }\n",
        ".dark .app-chip-accent { background: rgba(var(--app-accent-rgb), 0.26); color: #f1f5f9; "
        "border-color: rgba(var(--app-accent-rgb), 0.52); }\n",
        ".app-chip-success { background: #e8f8ef; color: #166534; border-color: #86efac; }\n",
        ".dark .app-chip-success { background: rgba(34, 197, 94, 0.22); color: #bbf7d0; "
        "border-color: rgba(34, 197, 94, 0.42); }\n",
        ".app-chip-warning { background: #fff6e9; color: #92400e; border-color: #fdba74; }\n",
        ".dark .app-chip-warning { background: rgba(245, 158, 11, 0.22); color: #fde68a; "
        "border-color: rgba(245, 158, 11, 0.42); }\n",
        ".app-chip-danger { background: #fdecec; color: #991b1b; border-color: #fca5a5; }\n",
        ".dark .app-chip-danger { background: rgba(239, 68, 68, 0.22); color: #fecaca; "
        "border-color: rgba(239, 68, 68, 0.42); }\n",
        ".app-field { width: 100%; border: 1px solid #cbd5e1; border-radius: 0.65rem; padding: 0.45rem 0.62rem; "
        "font-size: 0.875rem; line-height: 1.25; background: #ffffff; color: #0f172a; "
        "transition: border-color 0.15s ease, "
        "box-shadow 0.15s ease; }\n",
        ".app-field::placeholder { color: #94a3b8; }\n",
        ".app-field:focus-visible { outline: none; border-color: rgba(var(--app-accent-rgb), 0.66); "
        "box-shadow: 0 0 0 3px rgba(var(--app-accent-rgb), 0.20); }\n",
        ".dark .app-field { background: rgba(15, 23, 42, 0.84); color: #f1f5f9; border-color: #475569; }\n",
        ".dark .app-field::placeholder { color: #64748b; }\n",
        ".app-label { display: inline-block; font-size: 0.76rem; font-weight: 600; letter-spacing: 0.01em; "
        "color: #475569; }\n",
        ".dark .app-label { color: #cbd5e1; }\n",
        ".app-check { width: 1.05rem; height: 1.05rem; border-radius: 0.25rem; cursor: pointer; "
        "accent-color: var(--app-accent); }\n",
        ".app-range { width: 100%; height: 0.45rem; border-radius: 0.5rem; background: #cbd5e1; cursor: pointer; "
        "accent-color: var(--app-accent); }\n",
        ".dark .app-range { background: #334155; }\n",
        ".app-tech-list { display: grid; gap: 0.3rem; }\n",
        ".app-tech-row { display: flex; align-items: baseline; gap: 0.35rem; "
        "font-size: 0.78rem; line-height: 1.25; }\n",
        ".app-tech-key { color: #64748b; font-weight: 600; }\n",
        ".app-tech-val { color: #0f172a; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "
        "'Liberation Mono', 'Courier New', monospace; }\n",
        ".dark .app-tech-key { color: #94a3b8; }\n",
        ".dark .app-tech-val { color: #e2e8f0; }\n",
        ".studio-tablist { display: flex; gap: 0.35rem; border-bottom: 1px solid rgba(148, 163, 184, 0.35); "
        "padding: 0.45rem 1rem; background: rgba(var(--app-primary-rgb), 0.06); }\n",
        ".dark .studio-tablist { border-bottom-color: rgba(71, 85, 105, 0.65); background: rgba(15, 23, 42, 0.55); }\n",
        ".studio-tab { cursor: pointer; display: inline-flex; align-items: center; justify-content: center; "
        "padding: 0.52rem 0.72rem; border: 1px solid transparent; border-bottom-width: 2px; "
        "border-radius: 0.62rem 0.62rem 0 0; font-size: 0.92rem; font-weight: 600; color: #475569; "
        "background: transparent; transition: all 0.15s ease; }\n",
        ".studio-tab:hover { color: #0f172a; background: rgba(var(--app-primary-rgb), 0.12); }\n",
        ".dark .studio-tab { color: #94a3b8; }\n",
        ".dark .studio-tab:hover { color: #f1f5f9; background: rgba(var(--app-primary-rgb), 0.24); }\n",
        ".studio-tab-active { border-color: rgba(var(--app-primary-rgb), 0.56); color: var(--app-primary); "
        "background: rgba(var(--app-primary-rgb), 0.16); }\n",
        ".dark .studio-tab-active { color: #f8fafc; background: rgba(var(--app-primary-rgb), 0.30); "
        "border-color: rgba(var(--app-primary-rgb), 0.66); }\n",
        ".studio-export-page-card-selected { border-color: rgba(var(--app-primary-rgb), 0.66) !important; "
        "background: rgba(var(--app-primary-rgb), 0.10) !important; }\n",
        ".dark .studio-export-page-card-selected { border-color: rgba(var(--app-primary-rgb), 0.74) !important; "
        "background: rgba(var(--app-primary-rgb), 0.24) !important; }\n",
        ".studio-export-page-card:focus-visible { outline: 2px solid rgba(var(--app-accent-rgb), 0.65); "
        "outline-offset: 2px; border-radius: 0.75rem; }\n",
        ".bg-indigo-600, .bg-indigo-500, .dark .dark\\:bg-indigo-500 { "
        "background-color: var(--app-primary) !important; color: var(--app-primary-ink) !important; }\n",
        ".hover\\:bg-indigo-700:hover, .hover\\:bg-indigo-600:hover, .hover\\:bg-indigo-500:hover, "
        ".dark .dark\\:hover\\:bg-indigo-600:hover { "
        "background-color: rgba(var(--app-primary-rgb), 0.86) !important; }\n",
        ".text-indigo-600, .dark .dark\\:text-indigo-300, .dark .dark\\:text-indigo-400 { "
        "color: var(--app-primary) !important; }\n",
        ".border-indigo-600, .border-indigo-500, .dark .dark\\:border-indigo-500 { "
        "border-color: rgba(var(--app-primary-rgb), 0.58) !important; }\n",
        ".bg-sky-900\\/40, .bg-cyan-900\\/40 { background-color: rgba(var(--app-accent-rgb), 0.26) !important; }\n",
        ".text-sky-800, .text-cyan-800, .dark .dark\\:text-sky-100, .dark .dark\\:text-cyan-100 { "
        "color: var(--app-accent) !important; }\n",
        ".border-sky-200, .border-cyan-200, .dark .dark\\:border-sky-700\\/40, .dark .dark\\:border-cyan-700\\/40 { "
        "border-color: rgba(var(--app-accent-rgb), 0.45) !important; }\n",
        ".htmx-request .spinner { display: inline-block; width: 1rem; height: 1rem; ",
        "border: 2px solid #f3f4f6; border-top-color: var(--app-accent); border-radius: 50%; ",
        "animation: spin 0.8s linear infinite; }\n",
        "@keyframes spin { to { transform: rotate(360deg); } }\n",
        "@keyframes studio-toast-in {",
        " from { opacity: 0; transform: translateY(8px) scale(0.96); }",
        " to { opacity: 1; transform: translateY(0) scale(1); }",
        " }\n",
        "@keyframes studio-toast-out {",
        " from { opacity: 1; transform: translateY(0) scale(1); }",
        " to { opacity: 0; transform: translateY(8px) scale(0.96); }",
        " }\n",
        "::-webkit-scrollbar { width: 8px; height: 8px; }\n",
        "::-webkit-scrollbar-track { background: #f1f5f9; }\n",
        ".dark ::-webkit-scrollbar-track { background: #1e293b; }\n",
        "::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }\n",
        ".dark ::-webkit-scrollbar-thumb { background: #475569; }\n",
        "\n",
        ".sidebar { width: 16rem; }\n",
        ".sidebar-link:hover { background: rgba(var(--app-primary-rgb), 0.26); transform: translateX(0.25rem); }\n",
        '.sidebar-link[aria-current="page"] { background: var(--app-primary); border-left: 4px solid '
        "var(--app-accent); color: var(--app-primary-ink); transform: none; }\n",
        ".sidebar-icon { width: 2rem; text-align: center; }\n",
        ".sidebar-collapsed #app-sidebar { width: 3.5rem !important; ",
        "padding-left: 0.75rem; padding-right: 0.75rem; }\n",
        ".sidebar-collapsed #app-sidebar .sidebar-label { display: none; }\n",
        ".sidebar-collapsed #app-sidebar .sidebar-link { justify-content: center; ",
        "padding-left: 0.5rem; padding-right: 0.5rem; gap: 0; }\n",
        ".sidebar-collapsed #app-sidebar .sidebar-link:hover { transform: none; }\n",
        '.sidebar-collapsed #app-sidebar .sidebar-link[aria-current="page"] { border-left: 0; }\n',
        ".sidebar-collapsed #app-sidebar .sidebar-footer { display: none; }\n",
        ".sidebar-collapsed #app-sidebar .sidebar-brand-text { display: none; }\n",
        "#sidebar-toggle { background: transparent; border: none; color: inherit; }\n",
        "#sidebar-toggle:focus-visible { outline: 2px solid var(--app-accent); outline-offset: 2px; }\n",
        "@media (max-width: 1024px) {\n",
        "  #app-sidebar { width: 3.5rem !important; padding-left: 0.75rem; padding-right: 0.75rem; }\n",
        "  #app-sidebar .sidebar-label { display: none; }\n",
        "  #app-sidebar .sidebar-link { justify-content: center; padding-left: 0.5rem; ",
        "padding-right: 0.5rem; gap: 0; }\n",
        "  #app-sidebar .sidebar-link:hover { transform: none; }\n",
        "  #app-sidebar .sidebar-footer, #app-sidebar .sidebar-brand-text { display: none; }\n",
        "  #app-main { min-width: 0; }\n",
        "}\n",
        "\n",
        "/* FIX MIRADOR THUMBNAIL ANIMATION */\n",
        ".mirador-thumbnail-nav-scroll-content { transition: transform 0.2s ease-out !important; }\n",
        ".mirador-thumbnail-nav-canvas { border-radius: 4px; overflow: hidden; }\n",
        ".mirador-thumbnail-nav-selected { border: 2px solid var(--app-accent) !important; ",
        "box-shadow: 0 0 10px rgba(var(--app-accent-rgb), 0.42); }\n",
    ]
    return NotStr("<style>" + "".join(parts) + "</style>")
