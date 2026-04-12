from __future__ import annotations

from fasthtml.common import H3, Div

from studio_ui.components.settings.controls import (
    setting_input,
    setting_number,
    setting_range,
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
                help_text="Numero iniziale di miniature mostrate per pagina nel tab Studio Export.",
            ),
            setting_input(
                "Thumb / Page Options",
                "settings.thumbnails.page_size_options",
                ",".join(str(v) for v in thumbs.get("page_size_options", [24, 48, 72, 96])),
                help_text="Comma-separated values, used by Studio Export selector.",
            ),
            setting_number(
                "Thumb Max Edge (px)",
                "settings.thumbnails.max_long_edge_px",
                thumbs.get("max_long_edge_px", 320),
                min_val=64,
                max_val=2000,
                step_val=1,
                help_text="Lato lungo massimo delle miniature generate localmente per la griglia Export.",
            ),
            setting_range(
                "Thumb JPEG Quality",
                "settings.thumbnails.jpeg_quality",
                thumbs.get("jpeg_quality", 70),
                min_val=10,
                max_val=100,
                step_val=1,
                help_text="Qualità JPEG delle miniature; valori più alti migliorano resa e aumentano peso cache.",
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="thumbnails",
    )
