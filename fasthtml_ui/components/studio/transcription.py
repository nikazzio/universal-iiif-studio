"""Studio Transcription Tab Component."""

from urllib.parse import quote
from fasthtml.common import H3, Button, Div, Form, Input, Option, Select, Span, Textarea

from iiif_downloader.ocr.storage import OCRStorage


def transcription_tab_content(doc_id, library, page, error_msg: str = None, is_loading: bool = False):
    """Render the transcription tab content with OCR controls and editor."""
    from iiif_downloader.config_manager import get_config_manager
    from iiif_downloader.ocr.processor import OCRProcessor

    cfg = get_config_manager()
    selected_engine = cfg.get_setting("ocr.ocr_engine", "openai")

    # Get models only for the selected engine
    engines = OCRProcessor.get_available_models(selected_engine)

    # Check if provider is configured
    processor = OCRProcessor(
        openai_api_key=cfg.get_api_key("openai"),
        anthropic_api_key=cfg.get_api_key("anthropic"),
        google_api_key=cfg.get_api_key("google_vision"),
        hf_token=cfg.get_api_key("huggingface")
    )
    is_ready = processor.is_provider_ready(selected_engine)

    storage = OCRStorage()
    trans = storage.load_transcription(doc_id, page, library)
    text = trans.get("full_text", "") if trans else ""
    engine_name = trans.get("engine", "Manual") if trans else "N/A"
    timestamp = trans.get("timestamp", "N/A") if trans else "N/A"

    # Status Badge for the Engine
    status_badge = Span(
        "Configurato" if is_ready else "Chiave mancante",
        cls="text-[8px] font-bold px-1.5 py-0.5 rounded-full " + 
            ("bg-green-100 text-green-700 dark:bg-green-900/30" if is_ready else "bg-red-100 text-red-700 dark:bg-red-900/30")
    )

    error_alert = None
    if error_msg:
        error_alert = Div(
            Span(f"⚠️ {error_msg}", cls="text-[10px] font-medium"),
            cls="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800 text-red-700 dark:text-red-400 rounded-lg animate-in fade-in slide-in-from-top-1"
        )

    # Disable entire UI if loading
    ui_disabled = (not is_ready) or is_loading

    ocr_panel = Div(
        Div(
            Div(
                H3(f"AI Recognition: {selected_engine.upper()}", cls="text-[10px] font-bold text-indigo-400 uppercase tracking-widest"),
                status_badge,
                cls="flex items-center justify-between mb-3"
            ),
            error_alert,
            Form(
                Div(
                    Input(type="hidden", name="doc_id", value=doc_id),
                    Input(type="hidden", name="library", value=library),
                    Input(type="hidden", name="page", value=str(page)),
                    Div(
                        Select(
                            *[Option(label, value=val) for label, val in engines],
                            name="model",
                            disabled=ui_disabled,
                            cls="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 "
                            "text-gray-900 dark:text-gray-100 text-xs rounded-lg block w-full p-2 "
                            "focus:ring-2 focus:ring-indigo-500 transition-all "
                            f"{'' if not ui_disabled else 'opacity-50'}",
                        ),
                        cls="flex-1",
                    ),
                    Button(
                        Span("✨ Run OCR" if not is_loading else "⌛ Loading..."),
                        type="submit",
                        disabled=ui_disabled,
                        cls=f"bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold "
                            f"py-2 px-4 rounded-lg shadow-sm transition-all active:scale-95 flex items-center gap-2 "
                            f"{'opacity-100' if not ui_disabled else 'opacity-50 cursor-not-allowed'}",
                    ),
                    cls="flex gap-2 items-center",
                ),
                Input(type="hidden", name="engine", value=selected_engine),
                hx_post="/api/run_ocr_async",
                hx_target="#transcription-container",
                hx_swap="outerHTML",
                id="ocr-form"
            ),
            cls="bg-gray-50/50 dark:bg-gray-900/30 p-4 rounded-xl border border-gray-100 dark:border-gray-800 shadow-sm mb-6",
        )
    )

    info_line = Div(
        Div(
            Span(f"PAGINA {page}", cls="bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 text-[9px] font-bold px-2 py-0.5 rounded"),
            Div(
                Span(f"Motore: {engine_name}", cls="text-gray-400 text-[10px]"),
                Span("•", cls="mx-2 text-gray-300"),
                Span(f"Ultimo salvataggio: {timestamp}", cls="text-gray-400 text-[10px]"),
                cls="flex items-center"
            ),
            cls="flex items-center justify-between mb-2 px-1"
        )
    )

    # Spinner overlay for the whole pane IF loading
    spinner_overlay = None
    if is_loading:
        spinner_overlay = Div(
            Div(
                Div(cls="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4"),
                Span("AI in ascolto...", cls="text-indigo-600 font-bold tracking-widest uppercase text-[10px]"),
                cls="flex flex-col items-center justify-center h-full"
            ),
            cls=("absolute inset-0 bg-white/60 dark:bg-gray-950/60 backdrop-blur-[2px] z-50 rounded-xl "
                 "flex items-center justify-center"),
            hx_get=f"/api/check_ocr_status?doc_id={quote(doc_id)}&library={quote(library)}&page={page}",
            hx_trigger="every 2s",
            hx_target="#transcription-container",
            hx_swap="outerHTML",
        )

    # Return elements directly. Parent (render_studio_tabs or HTMX swap) will wrap in #transcription-container
    return [
        ocr_panel,
        Form(
            info_line,
            Textarea(
                text,
                name="text",
                id="transcription-textarea",
                disabled=is_loading,
                cls="w-full h-[55vh] p-4 text-sm border-0 rounded-xl bg-white dark:bg-gray-950 "
                "font-mono leading-relaxed shadow-inner focus:ring-2 focus:ring-indigo-500 transition-all "
                f"{'' if not is_loading else 'opacity-50'}",
                placeholder="Nessuna trascrizione disponibile. Scrivi qui o usa l'OCR..."
            ),
            Input(type="hidden", name="doc_id", value=doc_id),
            Input(type="hidden", name="library", value=library),
            Input(type="hidden", name="page", value=str(page)),
            Button(
                "💾 Salva Modifiche",
                type="submit",
                disabled=is_loading,
                cls="w-full mt-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 rounded-xl shadow-lg transition-all active:scale-[0.98] "
                f"{'' if not is_loading else 'opacity-50'}",
            ),
            hx_post="/api/save_transcription",
            hx_target="#save-feedback",
        ),
        Div(id="save-feedback"),
        spinner_overlay
    ]
