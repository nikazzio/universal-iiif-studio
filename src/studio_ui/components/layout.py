"""Base Layout Component.

Shell HTML con sidebar, headers per Tailwind/HTMX/Mirador, tema chiaro/scuro, e area contenuto principale.
"""

from fasthtml.common import A, Body, Button, Div, Head, Html, Img, Link, Main, Meta, Nav, Script, Title

from universal_iiif_core import __version__


def base_layout(title: str, content, active_page: str = "") -> Html:
    """Generate base page layout with sidebar, dark mode toggle, and headers."""
    return Html(
        Head(
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Title(title),

            # Tailwind CSS CDN
            Script(src="https://cdn.tailwindcss.com"),

            # Tailwind configuration
            Script("""
                if (typeof tailwind !== 'undefined') {
                    tailwind.config = {
                        darkMode: 'class',
                        theme: {
                            extend: {
                                colors: {
                                    primary: {
                                        50: '#eef2ff', 500: '#6366f1', 600: '#4f46e5', 700: '#4338ca', 900: '#312e81'
                                    }
                                }
                            }
                        }
                    };
                }
            """),

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
                cls="flex h-screen overflow-hidden"
            ),
            cls="antialiased bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100"
        )
    )


def _sidebar(active_page: str = "") -> Nav:
    nav_items = [
        ("studio", "Studio", "/studio", "📖"),
        ("discovery", "Discovery", "/discovery", "🔍"),
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
                        cls="flex flex-col leading-tight sidebar-brand-text"
                    ),
                    cls="flex items-center gap-3"
                ),
                Button(
                    "☰",
                    onclick="toggleSidebar()",
                    cls="text-2xl focus:outline-none",
                    id="sidebar-toggle",
                    aria_pressed="false",
                    title="Comprimi/espandi menu",
                ),
                cls="flex items-center justify-between mb-6"
            ),
            cls="sidebar-brand mb-6 pb-4 border-b border-gray-700"
        ),

        Div(*[
            A(
                Div(icon, cls="sidebar-icon text-2xl"),
                Div(label, cls="sidebar-label font-medium"),
                href=url,
                hx_get=url,
                hx_target="#app-main",
                hx_swap="innerHTML",
                hx_push_url="true",
                data_nav_link="true",
                cls=_sidebar_link_classes(),
                **({"aria_current": "page"} if key == active_page else {}),
            )
            for key, label, url, icon in nav_items
        ], cls="space-y-1 flex-1"),

        Button(
            Div(
                Div("☀️", id="light-icon", cls="text-xl"),
                Div("🌙", id="dark-icon", cls="text-xl hidden"),
                cls="flex items-center justify-center"
            ),
            onclick="toggleTheme()",
            cls="w-full py-3 px-4 rounded bg-gray-700 hover:bg-gray-600 transition-colors mb-3 text-white"
        ),

        Div(
            Div(f"v{__version__} → FastHTML", cls="text-xs text-gray-500"),
            cls="pt-4 border-t border-gray-700 sidebar-footer"
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
                const links = document.querySelectorAll('[data-nav-link]');
                links.forEach((link) => {
                    const isActive = link.getAttribute('href') === pathname;
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
        id="app-sidebar",
        cls="sidebar w-64 bg-gray-800 dark:bg-gray-950 text-white p-6 flex flex-col transition-all duration-200"
    )

def _sidebar_link_classes() -> str:
    return "sidebar-link flex items-center gap-3 py-3 px-4 rounded mb-2 transition-all duration-200"


def _style_tag():
    from fasthtml.common import NotStr
    css = """
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; }
        .sidebar-link { transition: all 0.2s ease; }
        .htmx-request .spinner { display: inline-block; width: 1rem; height: 1rem; border: 2px solid #f3f4f6; border-top-color: #6366f1; border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #f1f5f9; }
        .dark ::-webkit-scrollbar-track { background: #1e293b; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
        .dark ::-webkit-scrollbar-thumb { background: #475569; }
        
        .sidebar { width: 16rem; }
        .sidebar-link:hover { background: #374151; transform: translateX(0.25rem); }
        .sidebar-link[aria-current="page"] { background: #4f46e5; border-left: 4px solid #ffffff; transform: none; }
        .sidebar-icon { width: 2rem; text-align: center; }
        .sidebar-collapsed #app-sidebar { width: 3.5rem !important; padding-left: 0.75rem; padding-right: 0.75rem; }
        .sidebar-collapsed #app-sidebar .sidebar-label { display: none; }
        .sidebar-collapsed #app-sidebar .sidebar-link { justify-content: center; padding-left: 0.5rem; padding-right: 0.5rem; gap: 0; }
        .sidebar-collapsed #app-sidebar .sidebar-link:hover { transform: none; }
        .sidebar-collapsed #app-sidebar .sidebar-link[aria-current="page"] { border-left: 0; }
        .sidebar-collapsed #app-sidebar .sidebar-footer { display: none; }
        .sidebar-collapsed #app-sidebar .sidebar-brand-text { display: none; }
        #sidebar-toggle { background: transparent; border: none; color: inherit; }
        #sidebar-toggle:focus-visible { outline: 2px solid #6366f1; outline-offset: 2px; }

        /* FIX MIRADOR THUMBNAIL ANIMATION */
        .mirador-thumbnail-nav-scroll-content { transition: transform 0.2s ease-out !important; }
        .mirador-thumbnail-nav-canvas { border-radius: 4px; overflow: hidden; }
        .mirador-thumbnail-nav-selected { border: 2px solid #6366f1 !important; box-shadow: 0 0 10px rgba(99, 102, 241, 0.4); }
    """
    return NotStr(f"<style>{css}</style>")
