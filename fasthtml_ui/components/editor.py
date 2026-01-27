"""OCR Controls Component.

Pannello per eseguire OCR su pagine singole o batch, selezionare engine e modelli.
"""

from fasthtml.common import Button, Div, Form, Input, Label, Option, P, Script, Select, Span


def ocr_controls(
    doc_id: str,
    library: str,
    current_page: int,
    has_transcription: bool = False
) -> Div:
    """Generate OCR control panel.

    Args:
        doc_id: Document ID
        library: Library name
        current_page: Current page number
        has_transcription: Whether current page has transcription

    Returns:
        OCR controls Div
    """
    return Div(
        # Header
        Div(
            Span("🤖", cls="text-2xl mr-2"),
            Span("OCR / HTR", cls="text-lg font-bold text-gray-800 dark:text-gray-100"),
            cls="flex items-center mb-4 pb-2 border-b border-gray-200 dark:border-gray-700"
        ),

        # Engine selection
        Div(
            Label(
                "Engine OCR:",
                for_="ocr-engine",
                cls="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
            ),
            Select(
                Option("OpenAI GPT-4o", value="openai", selected=True),
                Option("Anthropic Claude", value="anthropic"),
                Option("Google Vision", value="google"),
                Option("Hugging Face", value="huggingface"),
                Option("Kraken (local)", value="kraken"),
                id="ocr-engine",
                name="engine",
                cls="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 dark:text-white"
            ),
            cls="mb-4"
        ),

        # Model selection (shown for Kraken only)
        Div(
            Label(
                "Modello HTR:",
                for_="ocr-model",
                cls="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
            ),
            Select(
                Option("Nessun modello installato", value="", selected=True),
                id="ocr-model",
                name="model",
                cls="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 dark:text-white"
            ),
            P(
                "I modelli Kraken devono essere installati separatamente.",
                cls="text-xs text-gray-500 dark:text-gray-400 mt-1"
            ),
            id="model-selector",
            cls="mb-4 hidden"
        ),

        # Single page OCR
        Form(
            Input(type="hidden", name="doc_id", value=doc_id),
            Input(type="hidden", name="library", value=library),
            Input(type="hidden", name="page", value=str(current_page)),
            Input(type="hidden", name="engine", id="engine-input", value="openai"),
            Input(type="hidden", name="model", id="model-input", value=""),

            Button(
                Div(
                    Span("✨", cls="text-xl mr-2"),
                    Span("Esegui OCR Pagina", cls="font-medium"),
                    cls="flex items-center justify-center"
                ),
                type="submit",
                cls="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 text-white rounded transition-all hover:scale-105"
            ),

            # Warning if transcription exists
            Div(
                Span("⚠️", cls="text-xl mr-2"),
                Span("Sovrascriverà la trascrizione esistente", cls="text-xs"),
                cls="mt-2 text-orange-600 dark:text-orange-400 flex items-center"
            ) if has_transcription else None,

            # Feedback area
            Div(id="ocr-feedback", cls="mt-3"),

            hx_post="/api/run_ocr",
            hx_target="#ocr-feedback",
            hx_swap="innerHTML",
            hx_indicator="#ocr-spinner"
        ),

        # Divider
        Div(cls="my-6 border-t border-gray-200 dark:border-gray-700"),

        # Batch OCR
        Div(
            Div(
                Span("📚", cls="text-xl mr-2"),
                Span("OCR Batch", cls="font-medium text-gray-800 dark:text-gray-100"),
                cls="flex items-center mb-3"
            ),

            P(
                "Esegui OCR su tutte le pagine del manoscritto. Questa operazione può richiedere diversi minuti.",
                cls="text-sm text-gray-600 dark:text-gray-400 mb-3"
            ),

            Button(
                "Avvia OCR Completo",
                onclick="confirmBatchOCR()",
                cls="w-full py-2 px-4 bg-purple-600 hover:bg-purple-700 dark:bg-purple-500 dark:hover:bg-purple-600 text-white rounded transition"
            ),

            cls="mb-4"
        ),

        # Engine change handler script
        Script("""
            const engineSelect = document.getElementById('ocr-engine');
            const modelSelector = document.getElementById('model-selector');
            const engineInput = document.getElementById('engine-input');
            const modelInput = document.getElementById('model-input');

            engineSelect.addEventListener('change', function() {
                const engine = this.value;
                engineInput.value = engine;

                // Show model selector only for Kraken
                if (engine === 'kraken') {
                    modelSelector.classList.remove('hidden');
                } else {
                    modelSelector.classList.add('hidden');
                }
            });

            // Update hidden model input when model changes
            document.getElementById('ocr-model').addEventListener('change', function() {
                modelInput.value = this.value;
            });

            function confirmBatchOCR() {
                if (confirm('Confermi di voler eseguire OCR su tutte le pagine? Questa operazione potrebbe richiedere molto tempo.')) {
                    // TODO: Implement batch OCR
                    alert('Funzionalità in sviluppo');
                }
            }
        """),

        # Spinner (hidden by default, shown by htmx-indicator)
        Div(
            Div(cls="spinner w-6 h-6 border-4 border-primary-600 border-t-transparent rounded-full animate-spin"),
            id="ocr-spinner",
            cls="htmx-indicator flex justify-center mt-3"
        ),

        cls="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700"
    )


def ocr_status_message(status: str, message: str, engine: str = "") -> Div:
    """Generate OCR status/feedback message.

    Args:
        status: "success", "error", "processing"
        message: Status message text
        engine: OCR engine used (optional)

    Returns:
        Status message Div
    """
    if status == "success":
        return Div(
            Span("✅", cls="text-2xl mr-2"),
            Div(
                Div("Trascrizione completata!", cls="font-medium"),
                Div(f"Engine: {engine}" if engine else "", cls="text-xs text-gray-600 dark:text-gray-400 mt-1"),
                cls="flex-1"
            ),
            cls="bg-green-100 dark:bg-green-900 border border-green-400 dark:border-green-600 text-green-700 dark:text-green-200 px-4 py-3 rounded flex items-center"
        )
    elif status == "error":
        return Div(
            Span("❌", cls="text-2xl mr-2"),
            Div(
                Div("Errore OCR", cls="font-medium"),
                Div(message, cls="text-xs mt-1"),
                cls="flex-1"
            ),
            cls="bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-600 text-red-700 dark:text-red-200 px-4 py-3 rounded flex items-center"
        )
    elif status == "processing":
        return Div(
            Div(cls="spinner w-5 h-5 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mr-3"),
            Span(message or "Elaborazione in corso...", cls="text-gray-700 dark:text-gray-300"),
            cls="bg-blue-100 dark:bg-blue-900 border border-blue-400 dark:border-blue-600 px-4 py-3 rounded flex items-center"
        )
    else:
        return Div(
            Span(message, cls="text-gray-700 dark:text-gray-300"),
            cls="bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 px-4 py-3 rounded"
        )
