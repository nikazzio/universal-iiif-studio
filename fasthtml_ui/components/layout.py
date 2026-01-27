"""Base Layout Component.

Shell HTML con sidebar, headers per Tailwind/HTMX/Mirador, tema chiaro/scuro, e area contenuto principale.
"""

from fasthtml.common import A, Body, Button, Div, Head, Html, Link, Main, Meta, Nav, Script, Title


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
            Script(src="https://unpkg.com/mirador@latest/dist/mirador.min.js"),

            # Cropper.js (For snippets)
            Link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.css"),
            Script(src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.js"),

            # Theme initialization
            Script("""
                (function() {
                    const theme = localStorage.getItem('theme') || 'light';
                    if (theme === 'dark') document.documentElement.classList.add('dark');
                })();
            """),

            _style_tag(),
        ),

        Body(
            Div(
                _sidebar(active_page),
                Main(content, cls="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900 transition-colors duration-200"),
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
            Div("Universal IIIF", cls="text-xl font-bold mb-1 text-white"),
            Div("Downloader & Studio", cls="text-sm text-gray-400"),
            cls="mb-8 pb-4 border-b border-gray-700"
        ),

        Div(*[
            A(Div(Div(icon, cls="text-2xl mr-3"), Div(label, cls="font-medium"), cls="flex items-center"),
              href=url, cls=_sidebar_link_classes(key == active_page))
            for key, label, url, icon in nav_items
        ], cls="space-y-1 flex-1"),

        Button(Div(Div("☀️", id="light-icon", cls="text-xl"), Div("🌙", id="dark-icon", cls="text-xl hidden"), cls="flex items-center justify-center"),
               onclick="toggleTheme()", cls="w-full py-3 px-4 rounded bg-gray-700 hover:bg-gray-600 transition-colors mb-3 text-white"),

        Div(Div("v0.6.0 → FastHTML", cls="text-xs text-gray-500"), cls="pt-4 border-t border-gray-700"),

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
        cls="w-64 bg-gray-800 dark:bg-gray-950 text-white p-6 flex flex-col transition-colors duration-200"
    )


def _sidebar_link_classes(is_active: bool) -> str:
    base = "sidebar-link block py-3 px-4 rounded mb-2 transition-all duration-200"
    if is_active: return f"{base} bg-primary-600 border-l-4 border-white"
    return f"{base} hover:bg-gray-700 hover:translate-x-1"


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
        
        /* FIX MIRADOR THUMBNAIL ANIMATION */
        .mirador-thumbnail-nav-scroll-content { transition: transform 0.2s ease-out !important; }
        .mirador-thumbnail-nav-canvas { border-radius: 4px; overflow: hidden; }
        .mirador-thumbnail-nav-selected { border: 2px solid #6366f1 !important; box-shadow: 0 0 10px rgba(99, 102, 241, 0.4); }
    """
    return NotStr(f"<style>{css}</style>")
