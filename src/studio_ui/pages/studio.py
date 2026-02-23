"""Studio Page and Document Picker Layouts."""

import json
from urllib.parse import quote

from fasthtml.common import H2, H3, A, Button, Div, P, Script, Span

from studio_ui.components.studio.tabs import render_studio_tabs
from studio_ui.components.viewer import mirador_viewer
from studio_ui.ocr_state import is_ocr_job_running
from universal_iiif_core.services.ocr.storage import OCRStorage


def document_picker():
    """Render the initial document selection screen."""
    docs = OCRStorage().list_documents()
    if not docs:
        return Div(H2("Nessun documento trovato nel Vault.", cls="text-center p-20 text-gray-400 font-light"))

    # Enforce standardization in UI and annotate download state
    clean_docs = []
    for doc in docs:
        lib = doc.get("library", "Unknown")
        if lib == "Vaticana (BAV)":
            lib = "Vaticana"
        doc["library"] = lib
        # Default status if missing
        doc.setdefault("status", "complete")
        clean_docs.append(doc)

    # Build cards with conditional interactivity
    cards = []
    for doc in clean_docs:
        is_downloading = doc.get("status") in {"downloading", "pending"}

        # Left content
        left = Div(
            H3(doc.get("label", doc["id"]), cls="font-bold text-lg text-slate-900 dark:text-white"),
            P(doc["library"], cls="text-sm text-indigo-600 dark:text-indigo-400 font-medium"),
            cls="flex-1",
        )

        # Right controls
        open_control = (
            A(
                "Apri Studio",
                href=f"/studio?doc_id={quote(doc['id'])}&library={quote(doc['library'])}",
                hx_get=f"/studio?doc_id={quote(doc['id'])}&library={quote(doc['library'])}",
                hx_target="#app-main",
                hx_swap="innerHTML",
                hx_push_url="true",
                onclick="event.stopPropagation();",
                cls=(
                    "bg-indigo-600 hover:bg-indigo-700 text-white dark:bg-indigo-500 "
                    "dark:hover:bg-indigo-600 px-6 py-2 rounded-lg font-bold shadow-sm transition mr-3"
                ),
            )
            if not is_downloading
            else Div(
                "⏳ In download",
                cls=(
                    "bg-amber-50 text-amber-700 px-3 py-1 rounded-lg font-medium text-sm mr-3 border border-amber-200"
                ),
            )
        )

        delete_btn = Button(
            "🗑️ Cancella",
            hx_delete=f"/studio/delete?doc_id={quote(doc['id'])}&library={quote(doc['library'])}",
            hx_confirm=(
                "Sei sicuro di voler eliminare DEFINITIVAMENTE '"
                + doc.get("label", doc["id"])
                + "'? Questa operazione non può essere annullata."
            ),
            hx_target="closest .p-10",
            cls=(
                "bg-red-50 hover:bg-red-100 text-red-600 dark:bg-red-900/20 "
                "dark:hover:bg-red-900/30 dark:text-red-400 px-4 py-2 rounded-lg font-medium transition"
            ),
            onclick="event.stopPropagation();",
        )

        right = Div(open_control, delete_btn, cls="flex items-center")

        card_classes = (
            "bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-100 "
            "dark:border-gray-700 mb-4 shadow-sm transition-all"
        )
        if not is_downloading:
            card_classes += " hover:shadow-lg transform hover:-translate-y-1 cursor-pointer"
        else:
            card_classes += " opacity-85 cursor-not-allowed"

        # Build the card with conditional hx attributes
        card_kwargs = {
            "cls": card_classes,
        }
        if not is_downloading:
            card_kwargs.update(
                {
                    "hx_get": f"/studio?doc_id={quote(doc['id'])}&library={quote(doc['library'])}",
                    "hx_target": "#app-main",
                    "hx_swap": "innerHTML",
                    "hx_push_url": "true",
                }
            )

        cards.append(Div(Div(left, right, cls="flex justify-between items-center"), **card_kwargs))

    return Div(
        H2("Documenti Disponibili", cls="text-2xl font-bold text-slate-800 dark:text-white mb-8"),
        Div(*cards, cls="max-w-4xl mx-auto"),
        cls="p-10 bg-slate-50 dark:bg-slate-900 min-h-screen",
    )


def studio_layout(title, library, doc_id, page, manifest_url, initial_canvas, manifest_json, total_pages, meta):
    """Render the main Studio split-view layout."""
    return Div(
        Div(
            # LEFT: Mirador (55%)
            Div(
                *mirador_viewer(manifest_url, "mirador-viewer", canvas_id=initial_canvas),
                cls="flex-none bg-slate-900 border-r border-gray-200 dark:border-gray-800",
                style="width: 55%;",
            ),
            # RIGHT: Editor (45%)
            Div(
                Div(
                    Div(
                        Div(
                            Div(
                                H2(title, cls="text-3xl font-black text-slate-900 dark:text-white tracking-tight"),
                                Div(
                                    Span(
                                        library,
                                        cls=(
                                            "bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 "
                                            "dark:text-indigo-400 text-[11px] font-bold px-3 py-1 "
                                            "rounded uppercase tracking-wider"
                                        ),
                                    ),
                                    Span(
                                        doc_id,
                                        cls=(
                                            "bg-slate-100 dark:bg-slate-800 text-slate-500 "
                                            "dark:text-slate-400 text-[9px] font-mono px-2 py-0.5 rounded"
                                        ),
                                    ),
                                    cls="flex gap-2 mt-1",
                                ),
                                cls="flex-1 min-w-0",
                            ),
                            cls="flex items-start justify-between",
                        ),
                        cls="px-6 py-8 border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900/50",
                    ),
                    # HTMX Target for Tab Content
                    Div(
                        render_studio_tabs(
                            doc_id,
                            library,
                            int(page),
                            meta,
                            total_pages,
                            manifest_json=manifest_json,
                            is_ocr_loading=is_ocr_job_running(doc_id, int(page)),
                        ),
                        id="studio-right-panel",
                        cls="flex-1 overflow-hidden h-full",
                    ),
                    cls="h-full flex flex-col",
                ),
                cls="flex-none bg-white dark:bg-gray-900 shadow-2xl z-10",
                style="width: 45%;",
            ),
            cls="flex h-screen",
        ),
        # Modal placeholder
        Div(id="cropper-modal-container"),
        Script(f"""
            (function() {{
                if (window.__studioMiradorListenerBound) return;
                window.__studioMiradorListenerBound = true;

                document.addEventListener('mirador:page-changed', function(e) {{
                    const panel = document.getElementById('studio-right-panel');
                    if (!panel) return;

                    const newPage = e.detail.page;
                    const library = {json.dumps(library)};
                    const docId = {json.dumps(doc_id)};
                    const totalPages = {total_pages};

                    console.log('📄 Page changed to:', newPage);

                    // 1. Update URL History
                    const url = new URL(window.location);
                    url.searchParams.set('page', newPage);
                    window.history.pushState({{}}, '', url);

                    const target = '/studio/partial/tabs?doc_id=' + encodeURIComponent(docId) +
                        '&library=' + encodeURIComponent(library) +
                        '&page=' + newPage;
                    htmx.ajax('GET', target, {{
                        target: '#studio-right-panel',
                        swap: 'innerHTML'
                    }});
                }});
            }})();
        """),
        cls="flex flex-col h-screen overflow-hidden",
    )
