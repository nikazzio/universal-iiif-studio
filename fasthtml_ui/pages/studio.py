"""Studio Page and Document Picker Layouts."""

import json
from urllib.parse import quote

from fasthtml.common import H2, H3, A, Button, Div, P, Script, Span

from fasthtml_ui.components.studio.tabs import render_studio_tabs
from fasthtml_ui.components.viewer import mirador_viewer
from iiif_downloader.ocr.storage import OCRStorage


def document_picker():
    """Render the initial document selection screen."""
    docs = OCRStorage().list_documents()
    if not docs:
        return Div(H2("Nessun documento trovato nel Vault.", cls="text-center p-20 text-gray-400 font-light"))

    # Enforce standardization in UI
    clean_docs = []
    for doc in docs:
        lib = doc.get("library", "Unknown")
        if lib == "Vaticana (BAV)":
            lib = "Vaticana"
        doc["library"] = lib
        clean_docs.append(doc)

    return Div(
        H2("Documenti Disponibili", cls="text-2xl font-bold text-slate-800 dark:text-white mb-8"),
        Div(
            *[
                Div(
                    Div(
                        Div(
                            H3(doc.get("label", doc["id"]), cls="font-bold text-lg text-slate-900 dark:text-white"),
                            P(doc["library"], cls="text-sm text-indigo-600 dark:text-indigo-400 font-medium"),
                            cls="flex-1",
                        ),
                        Div(
                            A(
                                "Apri Studio",
                                href=f"/studio?doc_id={quote(doc['id'])}&library={quote(doc['library'])}",
                                cls="bg-indigo-600 hover:bg-indigo-700 text-white dark:bg-indigo-500 "
                                "dark:hover:bg-indigo-600 px-6 py-2 rounded-lg font-bold shadow-sm transition mr-3",
                            ),
                            Button(
                                "🗑️ Cancella",
                                hx_delete=f"/studio/delete?doc_id={quote(doc['id'])}&library={quote(doc['library'])}",
                                hx_confirm=f"Sei sicuro di voler eliminare DEFINITIVAMENTE '{doc.get('label', doc['id'])}'? Questa operazione non può essere annullata.",
                                hx_target="closest .p-10", # Target the whole picker container to refresh the list
                                cls="bg-red-50 hover:bg-red-100 text-red-600 dark:bg-red-900/20 "
                                "dark:hover:bg-red-900/30 dark:text-red-400 px-4 py-2 rounded-lg font-medium transition",
                                onclick="event.stopPropagation();", # Prevent card click from opening studio
                            ),
                            cls="flex items-center",
                        ),
                        cls="flex justify-between items-center",
                    ),
                    cls="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-100 "
                    "dark:border-gray-700 mb-4 shadow-sm hover:shadow-lg transition-all "
                    "transform hover:-translate-y-1 cursor-pointer",
                    onclick=f"window.location='/studio?doc_id={quote(doc['id'])}&library={quote(doc['library'])}'",
                )
                for doc in clean_docs
            ],
            cls="max-w-4xl mx-auto",
        ),
        cls="p-10 bg-slate-50 dark:bg-slate-900 min-h-screen",
    )


def studio_layout(title, library, doc_id, page, manifest_url, initial_canvas, manifest_json, total_pages):
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
                                H2(title, cls="text-2xl font-black text-slate-900 dark:text-white tracking-tight"),
                                Div(
                                    Span(library, cls="bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-[9px] font-bold px-2 py-0.5 rounded uppercase tracking-wider"),
                                    Span(doc_id, cls="bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-[9px] font-mono px-2 py-0.5 rounded"),
                                    cls="flex gap-2 mt-1",
                                ),
                                cls="flex-1 min-w-0"
                            ),
                            cls="flex items-start justify-between"
                        ),
                        cls="px-6 py-8 border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900/50",
                    ),
                    # HTMX Target for Tab Content
                    Div(
                        render_studio_tabs(doc_id, library, int(page), manifest_json, total_pages),
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
            document.addEventListener('mirador:page-changed', function(e) {{
                const newPage = e.detail.page;
                const library = {json.dumps(library)};
                const docId = {json.dumps(doc_id)};
                const totalPages = {total_pages};

                console.log('📄 Page changed to:', newPage);
                
                // 1. Update URL History
                const url = new URL(window.location);
                url.searchParams.set('page', newPage);
                window.history.pushState({{}}, '', url);

                const target = `/studio/partial/tabs?doc_id=${{encodeURIComponent(docId)}}&library=${{encodeURIComponent(library)}}&page=${{newPage}}`;
                htmx.ajax('GET', target, {{
                    target: '#studio-right-panel',
                    swap: 'innerHTML'
                }});
            }});
        """),
        cls="flex flex-col h-screen overflow-hidden",
    )
