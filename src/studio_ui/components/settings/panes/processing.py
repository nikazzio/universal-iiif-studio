from __future__ import annotations

from fasthtml.common import H3, Div, P

from studio_ui.components.settings.controls import (
    setting_number,
    setting_range,
    setting_toggle,
)


def _build_processing_pane(cm, s):
    _ = cm
    pdf = s.get("pdf", {})
    return Div(
        Div(H3("Processing Core", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3")),
        P(
            "Queste opzioni governano il trattamento dei PDF nativi. Il tuning rete/download e nel tab Network.",
            cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
        ),
        Div(
            setting_number(
                "PDF Viewer DPI",
                "settings.pdf.viewer_dpi",
                pdf.get("viewer_dpi", 150),
                help_text=(
                    "Risoluzione usata quando il sistema estrae JPG da un PDF nativo. "
                    "Valori alti migliorano il dettaglio ma aumentano spazio disco e tempi di processing."
                ),
                min_val=72,
                max_val=600,
                step_val=1,
            ),
            setting_range(
                "PDF Raster JPEG Quality",
                "settings.pdf.viewer_jpeg_quality",
                pdf.get("viewer_jpeg_quality", 95),
                help_text=(
                    "Qualita JPEG usata solo quando un PDF nativo viene convertito in scans JPG. "
                    "Non influisce sui download IIIF normali."
                ),
                min_val=10,
                max_val=100,
                step_val=1.0,
            ),
            setting_toggle(
                "Prefer Native PDF",
                "settings.pdf.prefer_native_pdf",
                pdf.get("prefer_native_pdf", True),
                help_text=(
                    "Se il manifest espone un PDF nativo, il downloader prova quel flusso come sorgente primaria "
                    "e genera le pagine in scans/ per compatibilità Studio."
                ),
            ),
            setting_toggle(
                "Create PDF from Images",
                "settings.pdf.create_pdf_from_images",
                pdf.get("create_pdf_from_images", False),
                help_text=(
                    "Quando non si usa un PDF nativo, abilita la creazione di un PDF compilato dalle immagini locali "
                    "come artifact aggiuntivo."
                ),
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="performance",
    )
