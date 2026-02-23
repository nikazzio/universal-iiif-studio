"""Studio Snippets Tab Component."""

from pathlib import Path
from urllib.parse import quote

from fasthtml.common import Button, Div, NotStr, P, Span

from universal_iiif_core.services.ocr.storage import OCRStorage


def snippets_tab_content(doc_id, page, library):
    """Show saved snippets for this document."""
    vault = OCRStorage().vault
    snippets = vault.get_snippets(doc_id)
    content = [
        Div(
            Button(
                "✂️ Nuovo Ritaglio",
                hx_get=f"/studio/cropper?doc_id={quote(doc_id)}&library={quote(library)}&page={page}",
                hx_target="#cropper-modal-container",
                cls=(
                    "w-full bg-indigo-50 text-indigo-600 "
                    "border-2 border-dashed border-indigo-200 py-4 "
                    "rounded-xl font-bold mb-6 hover:bg-indigo-100 transition"
                ),
            ),
            cls="mb-2",
        )
    ]
    existing = [s for s in snippets if Path(s["image_path"]).exists()]
    if not existing:
        content.append(P("Nessun snippet salvato per questo documento.", cls="text-gray-400 italic py-10 text-center"))

    cards = []
    for s in existing:
        cards.append(
            Div(
                Div(
                    Span(
                        f"Pag. {s['page_num']}",
                        cls="text-[10px] font-bold bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded",
                    ),
                    Button(
                        "✖",
                        hx_delete=f"/api/delete_snippet/{s['id']}",
                        hx_target="closest .snippet",
                        hx_swap="outerHTML",
                        cls="text-red-400 hover:text-red-600",
                    ),
                    cls="flex justify-between items-center mb-2",
                ),
                NotStr(
                    f'<img src="/{s["image_path"]}" '
                    'class="w-full rounded border bg-white cursor-pointer hover:opacity-90 transition" '
                    'onclick="window.open(this.src)">'
                ),
                P(s.get("transcription", ""), cls=("text-xs mt-2 text-gray-600 italic line-clamp-3")),
                cls=(
                    "snippet bg-white dark:bg-gray-800 p-3 rounded-lg "
                    "border border-gray-200 dark:border-gray-700 shadow-sm "
                    "hover:shadow-md transition"
                ),
            )
        )

    content.append(Div(*cards, cls="grid grid-cols-1 gap-4"))
    return content
