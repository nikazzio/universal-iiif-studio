from fasthtml.common import H1, H3, Button, Div, Form, Input, Label, Option, P, Script, Select, Span, Textarea

from universal_iiif_core.config_manager import get_config_manager


def _val_or_default(val, default=""):
    return "" if val is None else val


def settings_content() -> Div:
    """Renderizza il pannello delle impostazioni completo con tabs e helper riutilizzabili."""
    cm = get_config_manager()

    # Script to initialize tabs and handle clicks robustly
    tabs_script = Script(
        """
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize panes: show only the first
            const panes = document.querySelectorAll('[data-pane]');
            panes.forEach((p, i) => p.style.display = (i === 0) ? 'block' : 'none');
            const firstTab = document.querySelector('[data-tab]');
            if (firstTab) firstTab.classList.add('bg-slate-700');

            document.addEventListener('click', function(e) {
                const btn = e.target.closest('[data-tab]');
                if (!btn) return;
                const t = btn.getAttribute('data-tab');
                document.querySelectorAll('[data-pane]').forEach(p => p.style.display = 'none');
                document.querySelectorAll('[data-tab]').forEach(b => b.classList.remove('bg-slate-700'));
                const pane = document.querySelector('[data-pane="' + t + '"]');
                if (pane) pane.style.display = 'block';
                btn.classList.add('bg-slate-700');
            });
        });
        """,
    )

    # Reusable form helpers
    def setting_input(label, key, value, type="text", help_text=""):
        return Div(
            Label(label, cls="block text-sm font-medium text-slate-300 mb-1"),
            Input(
                type=type,
                name=key,
                value=_val_or_default(value),
                cls="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100 focus:border-blue-500 outline-none transition-colors",
            ),
            P(help_text, cls="text-xs text-slate-500 mt-1") if help_text else "",
            cls="mb-4",
        )

    def setting_number(label, key, value, help_text=""):
        return setting_input(label, key, value, type="number", help_text=help_text)

    def setting_color(label, key, value, help_text=""):
        return Div(
            Label(label, cls="block text-sm font-medium text-slate-300 mb-1"),
            Input(type="color", name=key, value=_val_or_default(value) or "#ffffff", cls="h-10 w-16 p-0"),
            P(help_text, cls="text-xs text-slate-500 mt-1") if help_text else "",
            cls="mb-4",
        )

    def setting_toggle(label, key, value, help_text=""):
        checked = "checked" if value else None
        return Div(
            Label(label, cls="block text-sm font-medium text-slate-300 mb-1"),
            Input(type="checkbox", name=key, checked=checked, value="1"),
            P(help_text, cls="text-xs text-slate-500 mt-1") if help_text else "",
            cls="mb-4",
        )

    def setting_select(label, key, value, options, help_text=""):
        opts = []
        for v, label_text in options:
            opts.append(Option(label_text, value=v, selected=(v == value)))
        return Div(
            Label(label, cls="block text-sm font-medium text-slate-300 mb-1"),
            Select(*opts, name=key, cls="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100"),
            P(help_text, cls="text-xs text-slate-500 mt-1") if help_text else "",
            cls="mb-4",
        )

    def setting_textarea(label, key, value, help_text=""):
        return Div(
            Label(label, cls="block text-sm font-medium text-slate-300 mb-1"),
            Textarea(
                name=key,
                cls="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100 h-24",
                content=_val_or_default(value),
            ),
            P(help_text, cls="text-xs text-slate-500 mt-1") if help_text else "",
            cls="mb-4",
        )

    # Read values from config manager
    paths = cm.data.get("paths", {})
    api = cm.data.get("api_keys", {})
    s = cm.data.get("settings", {})

    # Tab buttons
    tab_buttons = Div(
        Span("General & API", data_tab="general", cls="px-4 py-2 cursor-pointer bg-slate-700 rounded-l"),
        Span("Processing", data_tab="processing", cls="px-4 py-2 cursor-pointer"),
        Span("Images & Download", data_tab="images", cls="px-4 py-2 cursor-pointer"),
        Span("Viewer", data_tab="viewer", cls="px-4 py-2 cursor-pointer"),
        Span("System & Paths", data_tab="system", cls="px-4 py-2 cursor-pointer rounded-r"),
        cls="flex gap-1 mb-4 text-slate-100",
    )

    # Build panes
    general_pane = Div(
        Div(H3("API Keys", cls="text-lg font-bold text-slate-100 mb-3")),
        Div(
            setting_input("OpenAI API Key", "api_keys.openai", api.get("openai", ""), "password", "Key per OpenAI."),
            setting_input(
                "Anthropic API Key", "api_keys.anthropic", api.get("anthropic", ""), "password", "Key per Anthropic."
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
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        Div(H3("Defaults", cls="text-lg font-bold text-slate-100 mb-3 mt-6")),
        Div(
            setting_input(
                "Default Library",
                "settings.defaults.default_library",
                s.get("defaults", {}).get("default_library", ""),
                "text",
            ),
            setting_select(
                "Preferred OCR Engine",
                "settings.defaults.preferred_ocr_engine",
                s.get("defaults", {}).get("preferred_ocr_engine", "openai"),
                [
                    ("openai", "OpenAI"),
                    ("anthropic", "Anthropic"),
                    ("google_vision", "Google Vision"),
                    ("kraken", "Kraken (Local)"),
                ],
            ),
            setting_toggle(
                "Auto-generate PDF",
                "settings.defaults.auto_generate_pdf",
                s.get("defaults", {}).get("auto_generate_pdf", False),
            ),
            cls="grid grid-cols-1 md:grid-cols-3 gap-4",
        ),
        cls="p-4",
        data_pane="general",
    )

    processing_pane = Div(
        Div(H3("OCR & PDF", cls="text-lg font-bold text-slate-100 mb-3")),
        Div(
            setting_select(
                "OCR Engine",
                "settings.ocr.ocr_engine",
                s.get("ocr", {}).get("ocr_engine", s.get("defaults", {}).get("preferred_ocr_engine", "openai")),
                [
                    ("openai", "OpenAI"),
                    ("anthropic", "Anthropic"),
                    ("google_vision", "Google Vision"),
                    ("kraken", "Kraken"),
                ],
            ),
            setting_toggle(
                "Kraken Enabled", "settings.ocr.kraken_enabled", s.get("ocr", {}).get("kraken_enabled", False)
            ),
            setting_number(
                "OCR Concurrency", "settings.system.ocr_concurrency", s.get("system", {}).get("ocr_concurrency", 1)
            ),
            setting_number("PDF Viewer DPI", "settings.pdf.viewer_dpi", s.get("pdf", {}).get("viewer_dpi", 150)),
            setting_number("PDF OCR DPI", "settings.pdf.ocr_dpi", s.get("pdf", {}).get("ocr_dpi", 300)),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        Div(H3("PDF Cover (optional)", cls="text-lg font-bold text-slate-100 mb-3 mt-6")),
        Div(
            setting_input(
                "Cover Logo Path",
                "settings.pdf.cover.logo_path",
                s.get("pdf", {}).get("cover", {}).get("logo_path", ""),
            ),
            setting_input(
                "Curator", "settings.pdf.cover.curator", s.get("pdf", {}).get("cover", {}).get("curator", "")
            ),
            setting_textarea(
                "Description",
                "settings.pdf.cover.description",
                s.get("pdf", {}).get("cover", {}).get("description", ""),
            ),
            cls="grid grid-cols-1 gap-4",
        ),
        cls="p-4",
        data_pane="processing",
    )

    images_pane = Div(
        Div(H3("Images & Download", cls="text-lg font-bold text-slate-100 mb-3")),
        Div(
            setting_number(
                "Download Workers", "settings.system.download_workers", s.get("system", {}).get("download_workers", 4)
            ),
            setting_input(
                "Download Strategy (comma-separated)",
                "settings.images.download_strategy",
                ",".join(s.get("images", {}).get("download_strategy", [])),
                help_text="Comma-separated list, e.g. max,3000,1740",
            ),
            setting_select(
                "IIIF Quality",
                "settings.images.iiif_quality",
                s.get("images", {}).get("iiif_quality", "default"),
                [("default", "default"), ("native", "native")],
            ),
            setting_number(
                "Viewer JPEG Quality", "settings.images.viewer_quality", s.get("images", {}).get("viewer_quality", 95)
            ),
            setting_number(
                "OCR Image Quality", "settings.images.ocr_quality", s.get("images", {}).get("ocr_quality", 95)
            ),
            setting_number(
                "Tile Stitch Max RAM (GB)",
                "settings.images.tile_stitch_max_ram_gb",
                s.get("images", {}).get("tile_stitch_max_ram_gb", 2),
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="images",
    )

    viewer_pane = Div(
        Div(H3("Viewer (Mirador)", cls="text-lg font-bold text-slate-100 mb-3")),
        Div(
            setting_number(
                "Max Zoom Pixel Ratio",
                "settings.viewer.mirador.openSeadragonOptions.maxZoomPixelRatio",
                s.get("viewer", {}).get("mirador", {}).get("openSeadragonOptions", {}).get("maxZoomPixelRatio", 5),
            ),
            setting_number(
                "Max Zoom Level",
                "settings.viewer.mirador.openSeadragonOptions.maxZoomLevel",
                s.get("viewer", {}).get("mirador", {}).get("openSeadragonOptions", {}).get("maxZoomLevel", 25),
            ),
            setting_number(
                "Min Zoom Level",
                "settings.viewer.mirador.openSeadragonOptions.minZoomLevel",
                s.get("viewer", {}).get("mirador", {}).get("openSeadragonOptions", {}).get("minZoomLevel", 0.35),
            ),
            cls="grid grid-cols-1 md:grid-cols-3 gap-4",
        ),
        Div(H3("Visual Filters Defaults", cls="text-lg font-bold text-slate-100 mb-3 mt-6")),
        Div(
            setting_number(
                "Brightness",
                "settings.viewer.visual_filters.defaults.brightness",
                s.get("viewer", {}).get("visual_filters", {}).get("defaults", {}).get("brightness", 1.0),
            ),
            setting_number(
                "Contrast",
                "settings.viewer.visual_filters.defaults.contrast",
                s.get("viewer", {}).get("visual_filters", {}).get("defaults", {}).get("contrast", 1.0),
            ),
            setting_number(
                "Saturation",
                "settings.viewer.visual_filters.defaults.saturation",
                s.get("viewer", {}).get("visual_filters", {}).get("defaults", {}).get("saturation", 1.0),
            ),
            cls="grid grid-cols-1 md:grid-cols-3 gap-4",
        ),
        cls="p-4",
        data_pane="viewer",
    )

    system_pane = Div(
        Div(H3("System & Paths", cls="text-lg font-bold text-slate-100 mb-3")),
        Div(
            setting_input(
                "Downloads Directory",
                "paths.downloads_dir",
                paths.get("downloads_dir", "data/local/downloads"),
                "text",
                help_text="Editable but changing may break existing files.",
            ),
            setting_input(
                "Temp Images Directory", "paths.temp_dir", paths.get("temp_dir", "data/local/temp_images"), "text"
            ),
            setting_input("Models Directory", "paths.models_dir", paths.get("models_dir", "data/local/models"), "text"),
            setting_input("Logs Directory", "paths.logs_dir", paths.get("logs_dir", "data/local/logs"), "text"),
            setting_input(
                "Snippets Directory", "paths.snippets_dir", paths.get("snippets_dir", "data/local/snippets"), "text"
            ),
            setting_select(
                "Logging Level",
                "settings.logging.level",
                s.get("logging", {}).get("level", "INFO"),
                [("DEBUG", "DEBUG"), ("INFO", "INFO"), ("WARNING", "WARNING"), ("ERROR", "ERROR")],
            ),
            setting_number(
                "Temp Cleanup Days",
                "settings.housekeeping.temp_cleanup_days",
                s.get("housekeeping", {}).get("temp_cleanup_days", 7),
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="system",
    )

    # Ensure only first pane visible by default
    panes = Div(general_pane, processing_pane, images_pane, viewer_pane, system_pane)
    # Wrap form
    form = Form(
        tab_buttons,
        panes,
        Div(
            Button(
                "💾 Save Settings",
                type="submit",
                cls="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded shadow",
            ),
            cls="flex justify-end mt-6",
        ),
        hx_post="/settings/save",
        hx_swap="none",
    )

    # Inject small JS and initial visibility
    wrapper = Div(H1("Settings", cls="text-3xl font-bold text-slate-100 mb-6"), form, cls="max-w-5xl mx-auto pb-20")
    # Small raw HTML injection for script and initial pane style
    raw_init = "<script>document.querySelectorAll('[data-pane]').forEach((p,i)=>{p.style.display=(i===0?'block':'none')});document.querySelector('[data-tab]').classList.add('bg-slate-700');</script>"
    # Ensure wrapper has a mutable content list then append raw scripts
    if getattr(wrapper, "content", None) is None:
        wrapper.content = []
    wrapper.content.append(raw_init)
    wrapper.content.append(tabs_script)

    return wrapper
