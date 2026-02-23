from fasthtml.common import H3, Div, Input, Label, P

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
    return Div(
        Div(H3("API Keys & Theme", cls="text-lg font-bold text-slate-100 mb-3")),
        Div(
            setting_input("OpenAI API Key", "api_keys.openai", api.get("openai", ""), "password", "Key per OpenAI."),
            setting_input(
                "Anthropic API Key", "api_keys.anthropic", api.get("anthropic", ""), "password", "Key per Anthopic."
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
            setting_color("Theme Color", "settings.ui.theme_color", s.get("ui", {}).get("theme_color", "#FF4B4B")),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        Div(H3("Defaults & Behaviour", cls="text-lg font-bold text-slate-100 mb-3 mt-6")),
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
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        Div(H3("Paths", cls="text-lg font-bold text-slate-100 mb-3 mt-6")),
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
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="general",
    )


def _build_processing_pane(cm, s):
    return Div(
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
                "OCR Concurrency",
                "settings.system.ocr_concurrency",
                s.get("system", {}).get("ocr_concurrency", 1),
                min_val=1,
                max_val=8,
                step_val=1,
            ),
            setting_number(
                "PDF Viewer DPI",
                "settings.pdf.viewer_dpi",
                s.get("pdf", {}).get("viewer_dpi", 150),
                help_text="DPI usati per estrarre immagini dal PDF per il viewer web.",
                min_val=72,
                max_val=600,
                step_val=1,
            ),
            setting_number(
                "PDF OCR DPI",
                "settings.pdf.ocr_dpi",
                s.get("pdf", {}).get("ocr_dpi", 300),
                help_text="DPI consigliati per OCR: piu alto migliora il testo ma aumenta peso e tempi.",
                min_val=72,
                max_val=1200,
                step_val=1,
            ),
            setting_toggle(
                "Prefer Native PDF",
                "settings.pdf.prefer_native_pdf",
                s.get("pdf", {}).get("prefer_native_pdf", True),
                help_text="Se il manifest contiene un PDF nativo, scaricalo e genera le pagine JPG in scans/.",
            ),
            setting_toggle(
                "Create PDF from Images",
                "settings.pdf.create_pdf_from_images",
                s.get("pdf", {}).get("create_pdf_from_images", False),
                help_text="Se manca un PDF nativo, crea un PDF compilato dalle immagini scaricate.",
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="performance",
    )


def _build_pdf_pane(cm, s):
    return Div(
        Div(H3("PDF Export", cls="text-lg font-bold text-slate-100 mb-3")),
        Div(
            Div(
                Label("Cover Logo", cls="block text-sm font-medium text-slate-300 mb-1"),
                Div(
                    Input(
                        type="file",
                        id="cover_logo_file_input",
                        cls="text-sm text-slate-100",
                        data_target_id="cover_logo_path_input",
                    ),
                    Input(
                        type="text",
                        id="cover_logo_path_input",
                        name="settings.pdf.cover.logo_path",
                        value=s.get("pdf", {}).get("cover", {}).get("logo_path", ""),
                        cls=(
                            "ml-2 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100 "
                            " focus:border-blue-500 outline-none transition-colors"
                        ),
                    ),
                    cls="flex items-center gap-2",
                ),
                P("Choose a local file; its filename will be recorded.", cls="text-xs text-slate-500 mt-1"),
                cls="mb-4",
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
        data_pane="pdf",
    )


def _build_images_pane(cm, s):
    return Div(
        Div(H3("Images & Download", cls="text-lg font-bold text-slate-100 mb-3")),
        Div(
            setting_number(
                "Download Workers",
                "settings.system.download_workers",
                s.get("system", {}).get("download_workers", 4),
                min_val=1,
                max_val=32,
                step_val=1,
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
                s.get("images", {}).get("viewer_quality", 95),
                min_val=10,
                max_val=100,
                step_val=1.0,
            ),
            setting_range(
                "OCR Image Quality",
                "settings.images.ocr_quality",
                s.get("images", {}).get("ocr_quality", 95),
                min_val=10,
                max_val=100,
                step_val=1.0,
            ),
            setting_number(
                "Tile Stitch Max RAM (GB)",
                "settings.images.tile_stitch_max_ram_gb",
                s.get("images", {}).get("tile_stitch_max_ram_gb", 2),
                min_val=0.1,
                max_val=64,
                step_val=0.1,
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="images",
    )


def _build_viewer_pane(cm, s):
    return Div(
        Div(H3("Viewer (Mirador)", cls="text-lg font-bold text-slate-100 mb-3")),
        Div(
            setting_number(
                "Max Zoom Pixel Ratio",
                "settings.viewer.mirador.openSeadragonOptions.maxZoomPixelRatio",
                s.get("viewer", {}).get("mirador", {}).get("openSeadragonOptions", {}).get("maxZoomPixelRatio", 5),
                min_val=1,
                max_val=10,
                step_val=0.1,
            ),
            setting_number(
                "Max Zoom Level",
                "settings.viewer.mirador.openSeadragonOptions.maxZoomLevel",
                s.get("viewer", {}).get("mirador", {}).get("openSeadragonOptions", {}).get("maxZoomLevel", 25),
                min_val=1,
                max_val=100,
                step_val=1,
            ),
            setting_number(
                "Min Zoom Level",
                "settings.viewer.mirador.openSeadragonOptions.minZoomLevel",
                s.get("viewer", {}).get("mirador", {}).get("openSeadragonOptions", {}).get("minZoomLevel", 0.35),
                min_val=0.05,
                max_val=1,
                step_val=0.05,
            ),
            cls="grid grid-cols-1 md:grid-cols-3 gap-4",
        ),
        Div(H3("Visual Filters Defaults", cls="text-lg font-bold text-slate-100 mb-3 mt-6")),
        Div(
            setting_range(
                "Brightness",
                "settings.viewer.visual_filters.defaults.brightness",
                s.get("viewer", {}).get("visual_filters", {}).get("defaults", {}).get("brightness", 1.0),
                min_val=0,
                max_val=2,
                step_val=0.05,
            ),
            setting_range(
                "Contrast",
                "settings.viewer.visual_filters.defaults.contrast",
                s.get("viewer", {}).get("visual_filters", {}).get("defaults", {}).get("contrast", 1.0),
                min_val=0,
                max_val=2,
                step_val=0.05,
            ),
            setting_range(
                "Saturation",
                "settings.viewer.visual_filters.defaults.saturation",
                s.get("viewer", {}).get("visual_filters", {}).get("defaults", {}).get("saturation", 1.0),
                min_val=0,
                max_val=2,
                step_val=0.05,
            ),
            cls="grid grid-cols-1 md:grid-cols-3 gap-4",
        ),
        cls="p-4",
        data_pane="viewer",
    )


def _build_system_pane(cm, s):
    paths = cm.data.get("paths", {})
    return Div(
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
