from fasthtml.common import H1, Button, Div, Form

from universal_iiif_core.config_manager import get_config_manager

from .controls import raw_file_script, raw_init
from .panes import (
    _build_general_pane,
    _build_images_pane,
    _build_pdf_pane,
    _build_processing_pane,
    _build_system_pane,
    _build_viewer_pane,
)


def settings_content() -> Div:
    """Renderizza il pannello delle impostazioni completo con tabs and panes."""
    cm = get_config_manager()

    # Read values from config manager
    s = cm.data.get("settings", {})

    # Tab buttons
    tab_buttons = Div(
        Div("", cls="hidden"),  # placeholder to keep structure stable
        Div("", cls="hidden"),
        cls="flex gap-1 mb-4 text-slate-100",
    )
    # Build panes via pane builders
    general_pane = _build_general_pane(cm, s)
    processing_pane = _build_processing_pane(cm, s)
    pdf_pane = _build_pdf_pane(cm, s)
    images_pane = _build_images_pane(cm, s)
    viewer_pane = _build_viewer_pane(cm, s)
    system_pane = _build_system_pane(cm, s)

    # Recreate the real tab buttons for clarity (kept here to allow localization)
    tab_buttons = Div(
        Div("General", data_tab="general", cls="px-4 py-2 cursor-pointer bg-slate-700 rounded-l"),
        Div("Performance", data_tab="performance", cls="px-4 py-2 cursor-pointer"),
        Div("PDF Export", data_tab="pdf", cls="px-4 py-2 cursor-pointer"),
        Div("Images / OCR", data_tab="images", cls="px-4 py-2 cursor-pointer"),
        Div("Viewer", data_tab="viewer", cls="px-4 py-2 cursor-pointer"),
        Div("Paths & System", data_tab="system", cls="px-4 py-2 cursor-pointer rounded-r"),
        cls="flex gap-1 mb-4 text-slate-100",
    )

    panes = Div(general_pane, processing_pane, pdf_pane, images_pane, viewer_pane, system_pane)

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

    wrapper = Div(H1("Settings", cls="text-3xl font-bold text-slate-100 mb-6"), form, cls="max-w-5xl mx-auto pb-20")

    if getattr(wrapper, "content", None) is None:
        wrapper.content = []
    wrapper.content.append(raw_init)
    wrapper.content.append(raw_file_script)

    return wrapper
