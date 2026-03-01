"""Studio Transcription Tab Component."""

from fasthtml.common import H3, Button, Div, Form, Input, Option, Script, Select, Span, Textarea

from studio_ui.config import get_api_key, get_setting
from universal_iiif_core.services.ocr.storage import OCRStorage


def transcription_tab_content(doc_id, library, page, error_msg: str = None, is_loading: bool = False):
    """Render the transcription tab content with OCR controls and editor."""
    from universal_iiif_core.services.ocr.processor import OCRProcessor

    selected_engine = get_setting("ocr.ocr_engine", "openai")

    # Get models only for the selected engine
    engines = OCRProcessor.get_available_models(selected_engine)

    # Check if provider is configured
    processor = OCRProcessor(
        openai_api_key=get_api_key("openai"),
        anthropic_api_key=get_api_key("anthropic"),
        google_api_key=get_api_key("google_vision"),
        hf_token=get_api_key("huggingface"),
    )
    is_ready = processor.is_provider_ready(selected_engine)

    storage = OCRStorage()
    trans = storage.load_transcription(doc_id, page, library)
    text = trans.get("full_text", "") if trans else ""
    engine_name = trans.get("engine", "Manual") if trans else "N/A"
    timestamp = trans.get("timestamp", "N/A") if trans else "N/A"

    status_badge = Span(
        "Configurato" if is_ready else "Chiave mancante",
        cls=(
            "app-chip app-chip-success text-[10px] font-semibold"
            if is_ready
            else "app-chip app-chip-danger text-[10px] font-semibold"
        ),
    )

    error_alert = None
    if error_msg:
        error_alert = Div(
            Span(f"⚠️ {error_msg}", cls="text-[10px] font-medium"),
            cls=(
                "mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-100 "
                "dark:border-red-800 text-red-700 dark:text-red-400 rounded-lg "
                "animate-in fade-in slide-in-from-top-1"
            ),
        )

    # Disable entire UI if loading
    ui_disabled = (not is_ready) or is_loading

    ocr_panel = Div(
        Div(
            Div(
                H3(
                    f"AI Recognition: {selected_engine.upper()}",
                    cls="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest",
                ),
                status_badge,
                cls="flex items-center justify-between mb-3",
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
                            cls=f"app-field text-xs transition-all {'' if not ui_disabled else 'opacity-50'}",
                        ),
                        cls="flex-1",
                    ),
                    Button(
                        Span("✨ Run OCR" if not is_loading else "⌛ Loading..."),
                        type="submit",
                        disabled=ui_disabled,
                        cls=f"app-btn app-btn-primary text-xs transition-all active:scale-95 flex items-center gap-2 "
                        f"{'opacity-100' if not ui_disabled else 'opacity-50 cursor-not-allowed'}",
                    ),
                    cls="flex gap-2 items-center",
                ),
                Input(type="hidden", name="engine", value=selected_engine),
                hx_post="/api/run_ocr_async",
                hx_target="#transcription-container",
                hx_swap="outerHTML",
                id="ocr-form",
            ),
            cls=(
                "bg-slate-50/70 dark:bg-slate-900/40 p-4 rounded-2xl border "
                "border-slate-200 dark:border-slate-700 shadow-sm mb-6"
            ),
        )
    )

    info_line = Div(
        Span(
            f"PAGINA {page}",
            cls=(
                "text-xs sm:text-sm font-semibold tracking-widest text-slate-600 "
                "dark:text-slate-300 bg-slate-100 dark:bg-slate-800/40 px-3 py-1 "
                "rounded-lg shadow-inner"
            ),
        ),
        Div(
            Span(f"Motore: {engine_name}", cls="text-sm font-medium text-slate-500 dark:text-slate-300"),
            Span("•", cls="mx-2 text-slate-400"),
            Span(f"Ultimo salvataggio: {timestamp}", cls="text-sm text-slate-500 dark:text-slate-300"),
            cls="flex flex-wrap items-center gap-1",
        ),
        cls=(
            "flex flex-wrap items-center justify-between gap-3 border border-slate-200 "
            "dark:border-slate-700 rounded-2xl px-4 py-3 mb-3 bg-white/70 "
            "dark:bg-slate-900/50 shadow-sm"
        ),
    )

    components = [
        ocr_panel,
        Form(
            info_line,
            Textarea(
                text,
                name="text",
                id="transcription-simplemde",
                disabled=is_loading,
                cls=(
                    "w-full h-[55vh] border-0 rounded-2xl bg-gradient-to-br from-slate-50 "
                    "to-white/70 dark:from-slate-950 dark:to-slate-900/70 font-sans "
                    "text-base leading-relaxed shadow-inner "
                    "transition-all backdrop-blur-sm"
                    f"{'' if not is_loading else ' opacity-50'}"
                ),
                placeholder="Nessuna trascrizione disponibile. Scrivi qui o usa l'OCR...",
            ),
            Input(type="hidden", name="doc_id", value=doc_id),
            Input(type="hidden", name="library", value=library),
            Input(type="hidden", name="page", value=str(page)),
            Button(
                "💾 Salva Modifiche",
                type="submit",
                disabled=is_loading,
                cls="hidden",
            ),
            hx_post="/api/save_transcription",
            hx_target="#save-feedback",
            hx_swap="innerHTML",
            id="transcription-form",
        ),
        Div(id="save-feedback"),
    ]

    simplemde_script = Script(f"""
(function() {{
    const TEXTAREA_ID = 'transcription-simplemde';
    const isLoading = {"true" if is_loading else "false"};
    const editorStyles = `
        .SimpleMDEContainer {{
            border-radius: 1.4rem !important;
            border: 1px solid rgba(148, 163, 184, 0.4) !important;
            background: #04050f !important;
            box-shadow: 0 30px 60px rgba(2, 6, 23, 0.65) !important;
        }}
        .editor-toolbar {{
            background: rgba(15, 23, 42, 0.95) !important;
            border: 1px solid rgba(148, 163, 184, 0.35) !important;
            border-top-left-radius: 1.4rem;
            border-top-right-radius: 1.4rem;
            padding: 0.35rem 0.65rem;
            gap: 0.25rem;
        }}
        .editor-toolbar button {{
            color: #e2e8f0 !important;
            background: rgba(15, 23, 42, 0.35) !important;
            border: 1px solid rgba(226, 232, 240, 0.3) !important;
            font-size: 0.95rem;
            padding: 0.45rem 0.95rem;
            border-radius: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            margin-right: 0.35rem;
        }}
        .editor-toolbar button:hover,
        .editor-toolbar button:focus-visible {{
            background: rgba(248, 250, 252, 0.9) !important;
            color: #0f172a !important;
            border-color: rgba(148, 163, 184, 0.45) !important;
        }}
        .editor-toolbar button.active {{
            background: var(--app-primary) !important;
            border-color: var(--app-primary) !important;
            color: var(--app-primary-ink) !important;
            box-shadow: 0 10px 20px rgba(var(--app-primary-rgb), 0.35);
        }}
        .editor-toolbar .fa {{
            color: inherit !important;
            text-shadow: none !important;
        }}
        .editor-toolbar button.toggle-preview {{
            background: rgba(148, 163, 184, 0.25) !important;
            border-color: rgba(226, 232, 240, 0.4) !important;
            color: #e2e8f0 !important;
        }}
        .editor-toolbar button.toggle-preview.active {{
            background: var(--app-accent) !important;
            border-color: var(--app-accent) !important;
            color: var(--app-accent-ink) !important;
            box-shadow: inset 0 0 0 1px rgba(var(--app-accent-rgb), 0.6);
        }}
        .SimpleMDEContainer .editor-statusbar {{
            background: #050b1d !important;
            color: #cbd5f5 !important;
            border-top: 1px solid rgba(148, 163, 184, 0.25) !important;
            padding: 0.45rem 0.75rem !important;
        }}
        .SimpleMDEContainer .CodeMirror,
        .SimpleMDEContainer .editor-preview-side {{
            background: #020617 !important;
            color: #e2e8f0 !important;
            border-radius: 0.85rem;
            font-size: 1rem;
        }}
        .SimpleMDEContainer .CodeMirror-lines {{
            padding: 1.4rem !important;
        }}
        .SimpleMDEContainer .editor-preview-side {{
            border-left: 1px solid rgba(148, 163, 184, 0.25) !important;
        }}
    `;
    const ensureStyles = () => {{
        if (!document.getElementById('simplemde-stylesheet')) {{
            const link = document.createElement('link');
            link.id = 'simplemde-stylesheet';
            link.rel = 'stylesheet';
            link.href = 'https://cdn.jsdelivr.net/simplemde/latest/simplemde.min.css';
            document.head.appendChild(link);
        }}
        if (!document.getElementById('simplemde-theme')) {{
            const style = document.createElement('style');
            style.id = 'simplemde-theme';
            style.textContent = editorStyles;
            document.head.appendChild(style);
        }}
    }};
    const configureEditor = () => {{
        const textarea = document.getElementById(TEXTAREA_ID);
        if (!textarea || !window.SimpleMDE) {{
            return;
        }}
        if (window.simplemdeTranscription) {{
            try {{
                window.simplemdeTranscription.toTextArea();
            }} catch (err) {{
                console.debug('Failed to tear down previous SimpleMDE instance', err);
            }}
            window.simplemdeTranscription = null;
        }}
        window.simplemdeTranscription = new SimpleMDE({{
            element: textarea,
            spellChecker: false,
            status: false,
            autoDownloadFontAwesome: true,
            forceSync: true,
            renderingConfig: {{ singleLineBreaks: false }},
            toolbar: [
                'bold', 'italic', 'heading', '|',
                'quote', 'unordered-list', 'ordered-list', '|',
                'preview', 'guide'
            ],
            placeholder: textarea.placeholder || 'Nessuna trascrizione disponibile. Scrivi qui o usa l\\'OCR...'
        }});
        const editor = window.simplemdeTranscription;
        editor.value(textarea.value || '');
        editor.codemirror.setOption('readOnly', isLoading ? 'nocursor' : false);
        const form = document.getElementById('transcription-form');
        if (form) {{
            form.addEventListener('submit', () => {{
                textarea.value = editor.value();
            }});
        }}
    }};

    const scheduleInit = () => {{
        ensureStyles();
        if (window.SimpleMDE) {{
            configureEditor();
            return;
        }}
        window.__codex_simplemde_callbacks = window.__codex_simplemde_callbacks || [];
        window.__codex_simplemde_callbacks.push(configureEditor);
        if (window.__codex_simplemde_loading) {{
            return;
        }}
        window.__codex_simplemde_loading = true;
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/simplemde/latest/simplemde.min.js';
        script.onload = () => {{
            (window.__codex_simplemde_callbacks || []).forEach(cb => cb());
        }};
        document.head.appendChild(script);
    }};

    scheduleInit();
}})();
""")

    components.append(simplemde_script)

    # Floating always-visible Save button: triggers the transcription form submit
    floating_save = Div(
        Button(
            "💾 Salva",
            type="button",
            onclick=(
                "(function(){"
                "const f = document.getElementById('transcription-form');"
                "if(window.simplemdeTranscription){ "
                "const ta=document.getElementById('transcription-simplemde'); "
                "ta.value = window.simplemdeTranscription.value(); "
                "}"
                "if(f && f.requestSubmit) f.requestSubmit(); else if(f) f.submit();"
                "})()"
            ),
            cls=(
                "app-btn app-btn-primary font-bold py-2 px-4 rounded-full "
                "shadow-lg transition-all active:scale-95 pointer-events-auto"
            ),
        ),
        cls="pointer-events-none fixed top-6 right-6 z-60",
    )
    components.append(floating_save)

    return components
