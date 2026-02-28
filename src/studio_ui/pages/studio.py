"""Studio workspace page layouts."""

import json

from fasthtml.common import H2, Div, Script, Span

from studio_ui.components.studio.tabs import render_studio_tabs
from studio_ui.components.viewer import mirador_viewer
from studio_ui.ocr_state import is_ocr_job_running


def studio_layout(
    title,
    library,
    doc_id,
    page,
    manifest_url,
    initial_canvas,
    manifest_json,
    total_pages,
    meta,
    asset_status: str = "",
    has_native_pdf: bool | None = None,
    pdf_local_available: bool = False,
):
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
                                        (asset_status or "unknown").upper(),
                                        cls=(
                                            "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 "
                                            "text-[10px] font-bold px-2 py-0.5 rounded"
                                        ),
                                    ),
                                    Span(
                                        "PDF nativo" if has_native_pdf else "Solo immagini",
                                        cls=(
                                            "bg-emerald-50 dark:bg-emerald-900/30 "
                                            "text-emerald-700 dark:text-emerald-300 "
                                            "text-[10px] font-bold px-2 py-0.5 rounded"
                                        )
                                        if has_native_pdf is not None
                                        else (
                                            "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-300 "
                                            "text-[10px] font-bold px-2 py-0.5 rounded"
                                        ),
                                    ),
                                    Span(
                                        "PDF locale ✓" if pdf_local_available else "PDF locale -",
                                        cls=(
                                            "bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 "
                                            "text-[10px] font-bold px-2 py-0.5 rounded"
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
