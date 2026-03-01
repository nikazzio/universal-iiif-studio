from fasthtml.common import H3, Div, Input, Label, P

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


def _build_general_pane(cm, s):
    paths = cm.data.get("paths", {})
    api = cm.data.get("api_keys", {})
    ui = s.get("ui", {})
    theme = resolve_ui_theme(ui)
    defaults = s.get("defaults", {})
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
            ),
            setting_number(
                "Library Items / Page",
                "settings.ui.items_per_page",
                ui.get("items_per_page", 12),
                min_val=4,
                max_val=200,
                step_val=1,
            ),
            setting_number(
                "Toast Duration (ms)",
                "settings.ui.toast_duration",
                ui.get("toast_duration", 3000),
                min_val=500,
                max_val=15000,
                step_val=100,
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        Div(H3("Paths", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3 mt-6")),
        Div(
            setting_input(
                "Downloads Directory",
                "paths.downloads_dir",
                paths.get("downloads_dir", "data/local/downloads"),
                "text",
                help_text="Editable but changing may break existing files.",
            ),
            setting_input(
                "Exports Directory",
                "paths.exports_dir",
                paths.get("exports_dir", "data/local/exports"),
                "text",
            ),
            setting_input(
                "Temp Images Directory",
                "paths.temp_dir",
                paths.get("temp_dir", "data/local/temp_images"),
                "text",
            ),
            setting_input("Models Directory", "paths.models_dir", paths.get("models_dir", "data/local/models"), "text"),
            setting_input("Logs Directory", "paths.logs_dir", paths.get("logs_dir", "data/local/logs"), "text"),
            setting_input(
                "Snippets Directory",
                "paths.snippets_dir",
                paths.get("snippets_dir", "data/local/snippets"),
                "text",
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="general",
    )


def _build_processing_pane(cm, s):
    _ = cm
    system = s.get("system", {})
    ocr = s.get("ocr", {})
    pdf = s.get("pdf", {})
    defaults = s.get("defaults", {})
    return Div(
        Div(H3("OCR & PDF", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3")),
        Div(
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
            ),
            setting_toggle("Kraken Enabled", "settings.ocr.kraken_enabled", ocr.get("kraken_enabled", False)),
            setting_number(
                "Download Workers",
                "settings.system.download_workers",
                system.get("download_workers", 4),
                min_val=1,
                max_val=32,
                step_val=1,
            ),
            setting_number(
                "Max Concurrent Downloads",
                "settings.system.max_concurrent_downloads",
                system.get("max_concurrent_downloads", 2),
                min_val=1,
                max_val=16,
                step_val=1,
            ),
            setting_number(
                "Request Timeout (s)",
                "settings.system.request_timeout",
                system.get("request_timeout", 30),
                min_val=5,
                max_val=600,
                step_val=1,
            ),
            setting_number(
                "OCR Concurrency",
                "settings.system.ocr_concurrency",
                system.get("ocr_concurrency", 1),
                min_val=1,
                max_val=8,
                step_val=1,
            ),
            setting_number(
                "PDF Viewer DPI",
                "settings.pdf.viewer_dpi",
                pdf.get("viewer_dpi", 150),
                help_text="DPI usati per estrarre immagini dal PDF per il viewer web.",
                min_val=72,
                max_val=600,
                step_val=1,
            ),
            setting_number(
                "PDF OCR DPI",
                "settings.pdf.ocr_dpi",
                pdf.get("ocr_dpi", 300),
                help_text="DPI consigliati per OCR: piu alto migliora il testo ma aumenta peso e tempi.",
                min_val=72,
                max_val=1200,
                step_val=1,
            ),
            setting_toggle(
                "Prefer Native PDF",
                "settings.pdf.prefer_native_pdf",
                pdf.get("prefer_native_pdf", True),
                help_text="Se il manifest contiene un PDF nativo, scaricalo e genera le pagine JPG in scans/.",
            ),
            setting_toggle(
                "Create PDF from Images",
                "settings.pdf.create_pdf_from_images",
                pdf.get("create_pdf_from_images", False),
                help_text="Se manca un PDF nativo, crea un PDF compilato dalle immagini scaricate.",
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
    return Div(
        Div(H3("PDF Export", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3")),
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
                    "Choose a local file; only the filename is stored.",
                    cls="text-xs text-slate-500 dark:text-slate-400 mt-1",
                ),
                cls="mb-4",
            ),
            setting_input("Curator", "settings.pdf.cover.curator", cover.get("curator", "")),
            setting_textarea("Description", "settings.pdf.cover.description", cover.get("description", "")),
            setting_select(
                "Default Export Format",
                "settings.pdf.export.default_format",
                export_cfg.get("default_format", "pdf_images"),
                [
                    ("pdf_images", "PDF (solo immagini)"),
                    ("pdf_searchable", "PDF ricercabile"),
                    ("pdf_facing", "PDF testo a fronte"),
                ],
            ),
            setting_select(
                "Default Compression",
                "settings.pdf.export.default_compression",
                export_cfg.get("default_compression", "Standard"),
                [("High-Res", "High-Res"), ("Standard", "Standard"), ("Light", "Light")],
            ),
            setting_toggle(
                "Default Include Cover",
                "settings.pdf.export.include_cover",
                export_cfg.get("include_cover", True),
            ),
            setting_toggle(
                "Default Include Colophon",
                "settings.pdf.export.include_colophon",
                export_cfg.get("include_colophon", True),
            ),
            setting_number(
                "Description Rows",
                "settings.pdf.export.description_rows",
                export_cfg.get("description_rows", 3),
                min_val=2,
                max_val=8,
                step_val=1,
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="pdf",
    )


def _build_images_pane(cm, s):
    _ = cm
    images = s.get("images", {})
    return Div(
        Div(H3("Images & Download", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3")),
        Div(
            setting_input(
                "Download Strategy (comma-separated)",
                "settings.images.download_strategy",
                ",".join(images.get("download_strategy", [])),
                help_text="Comma-separated list, e.g. max,3000,1740",
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
            ),
            setting_range(
                "Viewer JPEG Quality",
                "settings.images.viewer_quality",
                images.get("viewer_quality", 95),
                min_val=10,
                max_val=100,
                step_val=1.0,
            ),
            setting_range(
                "OCR Image Quality",
                "settings.images.ocr_quality",
                images.get("ocr_quality", 95),
                min_val=10,
                max_val=100,
                step_val=1.0,
            ),
            setting_number(
                "Tile Stitch Max RAM (GB)",
                "settings.images.tile_stitch_max_ram_gb",
                images.get("tile_stitch_max_ram_gb", 2),
                min_val=0.1,
                max_val=64,
                step_val=0.1,
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
            ),
            setting_input(
                "Thumb / Page Options",
                "settings.thumbnails.page_size_options",
                ",".join(str(v) for v in thumbs.get("page_size_options", [24, 48, 72, 96])),
                help_text="Comma-separated values, used by Studio Export selector.",
            ),
            setting_number(
                "Thumb Columns",
                "settings.thumbnails.columns",
                thumbs.get("columns", 6),
                min_val=1,
                max_val=12,
                step_val=1,
            ),
            setting_toggle(
                "Enable Pagination",
                "settings.thumbnails.paginate_enabled",
                thumbs.get("paginate_enabled", True),
            ),
            setting_toggle(
                "Default Select All",
                "settings.thumbnails.default_select_all",
                thumbs.get("default_select_all", True),
            ),
            setting_toggle(
                "Actions Apply To All Default",
                "settings.thumbnails.actions_apply_to_all_default",
                thumbs.get("actions_apply_to_all_default", False),
            ),
            setting_number(
                "Thumb Max Edge (px)",
                "settings.thumbnails.max_long_edge_px",
                thumbs.get("max_long_edge_px", 320),
                min_val=64,
                max_val=2000,
                step_val=1,
            ),
            setting_range(
                "Thumb JPEG Quality",
                "settings.thumbnails.jpeg_quality",
                thumbs.get("jpeg_quality", 70),
                min_val=10,
                max_val=100,
                step_val=1,
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        Div(H3("Hover Preview", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3 mt-6")),
        Div(
            setting_toggle(
                "Hover Preview Enabled",
                "settings.thumbnails.hover_preview_enabled",
                thumbs.get("hover_preview_enabled", True),
            ),
            setting_number(
                "Hover Delay (ms)",
                "settings.thumbnails.hover_preview_delay_ms",
                thumbs.get("hover_preview_delay_ms", 550),
                min_val=0,
                max_val=5000,
                step_val=10,
            ),
            setting_number(
                "Hover Max Edge (px)",
                "settings.thumbnails.hover_preview_max_long_edge_px",
                thumbs.get("hover_preview_max_long_edge_px", 900),
                min_val=64,
                max_val=4000,
                step_val=1,
            ),
            setting_range(
                "Hover JPEG Quality",
                "settings.thumbnails.hover_preview_jpeg_quality",
                thumbs.get("hover_preview_jpeg_quality", 82),
                min_val=10,
                max_val=100,
                step_val=1,
            ),
            setting_number(
                "Inline Base64 Max Tiles",
                "settings.thumbnails.inline_base64_max_tiles",
                thumbs.get("inline_base64_max_tiles", 120),
                min_val=1,
                max_val=1000,
                step_val=1,
            ),
            setting_number(
                "Hover Preview Max Tiles",
                "settings.thumbnails.hover_preview_max_tiles",
                thumbs.get("hover_preview_max_tiles", 72),
                min_val=1,
                max_val=1000,
                step_val=1,
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
        ),
        setting_range(
            f"{title} Contrast",
            f"{path}.contrast",
            preset.get("contrast", 1.0),
            min_val=0,
            max_val=2,
            step_val=0.05,
        ),
        setting_range(
            f"{title} Saturation",
            f"{path}.saturation",
            preset.get("saturation", 1.0),
            min_val=0,
            max_val=2,
            step_val=0.05,
        ),
        setting_range(
            f"{title} Hue",
            f"{path}.hue",
            preset.get("hue", 0),
            min_val=-180,
            max_val=180,
            step_val=1,
        ),
        setting_toggle(f"{title} Invert", f"{path}.invert", preset.get("invert", False)),
        setting_toggle(f"{title} Grayscale", f"{path}.grayscale", preset.get("grayscale", False)),
    ]


def _build_viewer_pane(cm, s):
    _ = cm
    viewer = s.get("viewer", {})
    mirador = viewer.get("mirador", {}).get("openSeadragonOptions", {})
    visual = viewer.get("visual_filters", {})
    defaults = visual.get("defaults", {})
    return Div(
        Div(H3("Viewer (Mirador)", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3")),
        Div(
            setting_number(
                "Max Zoom Pixel Ratio",
                "settings.viewer.mirador.openSeadragonOptions.maxZoomPixelRatio",
                mirador.get("maxZoomPixelRatio", 5),
                min_val=1,
                max_val=10,
                step_val=0.1,
            ),
            setting_number(
                "Max Zoom Level",
                "settings.viewer.mirador.openSeadragonOptions.maxZoomLevel",
                mirador.get("maxZoomLevel", 25),
                min_val=1,
                max_val=100,
                step_val=1,
            ),
            setting_number(
                "Min Zoom Level",
                "settings.viewer.mirador.openSeadragonOptions.minZoomLevel",
                mirador.get("minZoomLevel", 0.35),
                min_val=0.05,
                max_val=1,
                step_val=0.05,
            ),
            cls="grid grid-cols-1 md:grid-cols-3 gap-4",
        ),
        Div(H3("Visual Filters Defaults", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3 mt-6")),
        Div(
            setting_range(
                "Brightness",
                "settings.viewer.visual_filters.defaults.brightness",
                defaults.get("brightness", 1.0),
                min_val=0,
                max_val=2,
                step_val=0.05,
            ),
            setting_range(
                "Contrast",
                "settings.viewer.visual_filters.defaults.contrast",
                defaults.get("contrast", 1.0),
                min_val=0,
                max_val=2,
                step_val=0.05,
            ),
            setting_range(
                "Saturation",
                "settings.viewer.visual_filters.defaults.saturation",
                defaults.get("saturation", 1.0),
                min_val=0,
                max_val=2,
                step_val=0.05,
            ),
            setting_range(
                "Hue",
                "settings.viewer.visual_filters.defaults.hue",
                defaults.get("hue", 0),
                min_val=-180,
                max_val=180,
                step_val=1,
            ),
            setting_toggle(
                "Invert",
                "settings.viewer.visual_filters.defaults.invert",
                defaults.get("invert", False),
            ),
            setting_toggle(
                "Grayscale",
                "settings.viewer.visual_filters.defaults.grayscale",
                defaults.get("grayscale", False),
            ),
            cls="grid grid-cols-1 md:grid-cols-3 gap-4",
        ),
        Div(H3("Visual Filters Presets", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3 mt-6")),
        Div(
            *_visual_preset_controls(visual, "default"),
            *_visual_preset_controls(visual, "night"),
            *_visual_preset_controls(visual, "contrast"),
            cls="grid grid-cols-1 md:grid-cols-3 gap-4",
        ),
        cls="p-4",
        data_pane="viewer",
    )


def _build_system_pane(cm, s):
    paths = cm.data.get("paths", {})
    security = cm.data.get("security", {})
    return Div(
        Div(H3("System & Paths", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3")),
        Div(
            setting_input(
                "Downloads Directory",
                "paths.downloads_dir",
                paths.get("downloads_dir", "data/local/downloads"),
                "text",
                help_text="Editable but changing may break existing files.",
            ),
            setting_input(
                "Exports Directory",
                "paths.exports_dir",
                paths.get("exports_dir", "data/local/exports"),
                "text",
            ),
            setting_input(
                "Temp Images Directory",
                "paths.temp_dir",
                paths.get("temp_dir", "data/local/temp_images"),
                "text",
            ),
            setting_input("Models Directory", "paths.models_dir", paths.get("models_dir", "data/local/models"), "text"),
            setting_input("Logs Directory", "paths.logs_dir", paths.get("logs_dir", "data/local/logs"), "text"),
            setting_input(
                "Snippets Directory",
                "paths.snippets_dir",
                paths.get("snippets_dir", "data/local/snippets"),
                "text",
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
                min_val=1,
                max_val=365,
                step_val=1,
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
                help_text="CORS origins (comma-separated).",
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="system",
    )
