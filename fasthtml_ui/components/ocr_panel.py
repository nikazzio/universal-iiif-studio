"""Simplified OCR Controls - Focused on single-page OCR.

Minimal UI for running OCR on current page only.
"""

from fasthtml.common import Button, Div, Form, Input, Option, Script, Select, Span


def ocr_quick_panel(
    doc_id: str,
    library: str,
    current_page: int,
) -> Div:
    """Generate minimal OCR panel for single-page processing.

    Args:
        doc_id: Document ID
        library: Library name
        current_page: Current page number

    Returns:
        Compact OCR panel Div
    """
    return Form(
        # Hidden fields
        Input(type="hidden", name="doc_id", value=doc_id),
        Input(type="hidden", name="library", value=library),
        Input(type="hidden", name="page", value=str(current_page)),
        Input(type="hidden", name="engine", id="ocr-engine-value", value="openai"),

        # Compact engine selector + button
        Div(
            Select(
                Option("GPT-4o", value="openai", selected=True),
                Option("Claude", value="anthropic"),
                Option("Google Vision", value="google"),
                id="ocr-engine-select",
                onchange="document.getElementById('ocr-engine-value').value = this.value",
                cls="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-l bg-white dark:bg-gray-800 dark:text-white text-sm w-32"
            ),

            Button(
                Span("✨ OCR", cls="font-medium"),
                type="submit",
                cls="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 text-white rounded-r transition text-sm"
            ),

            cls="flex"
        ),

        # Feedback area
        Div(id="ocr-feedback", cls="mt-2"),

        # HTMX attributes
        hx_post="/api/run_ocr",
        hx_target="#ocr-feedback",
        hx_swap="innerHTML",
        hx_indicator="#ocr-spinner"
    )


def ocr_feedback_message(status: str, message: str = "") -> Div:
    """Generate compact OCR feedback message.

    Args:
        status: "success", "error", "processing"
        message: Optional message text

    Returns:
        Feedback Div
    """
    if status == "success":
        return Div(
            Span("✅ Completato!", cls="text-sm font-medium text-green-700 dark:text-green-300"),
            Script("setTimeout(() => window.location.reload(), 1500);"),
            cls="bg-green-100 dark:bg-green-900 px-3 py-2 rounded text-sm"
        )
    elif status == "error":
        return Div(
            Span(f"❌ {message}", cls="text-sm text-red-700 dark:text-red-300"),
            cls="bg-red-100 dark:bg-red-900 px-3 py-2 rounded text-sm"
        )
    elif status == "processing":
        return Div(
            Div(cls="inline-block w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mr-2"),
            Span("Elaborazione...", cls="text-sm text-blue-700 dark:text-blue-300"),
            cls="bg-blue-100 dark:bg-blue-900 px-3 py-2 rounded text-sm flex items-center"
        )
    else:
        return Div()
