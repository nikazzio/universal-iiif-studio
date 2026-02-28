"""Studio Tabs Manager Component."""

import json
from urllib.parse import quote

from fasthtml.common import Button, Div, Script, Span

from studio_ui.components.studio.history import history_tab_content
from studio_ui.components.studio.info import info_tab_content, visual_tab_content
from studio_ui.components.studio.snippets import snippets_tab_content
from studio_ui.components.studio.transcription import transcription_tab_content


def render_studio_tabs(
    doc_id,
    library,
    page,
    meta,
    total_pages,
    manifest_json=None,
    *,
    is_ocr_loading: bool = False,
    ocr_error: str | None = None,
    history_message: str | None = None,
    export_fragment=None,
):
    """Render the studio tabs."""
    page_idx = int(page)
    # Header buttons
    buttons = Div(
        Button(
            "📝 Trascrizione",
            onclick="switchTab('transcription')",
            id="tab-button-transcription",
            cls="tab-button active px-4 py-2 text-base font-medium border-b-2 "
            "border-indigo-600 text-indigo-600 dark:text-indigo-400",
        ),
        Button(
            "📂 Snippets",
            onclick="switchTab('snippets')",
            id="tab-button-snippets",
            cls="tab-button px-4 py-2 text-base font-medium border-b-2 "
            "border-transparent text-gray-500 hover:text-gray-700",
        ),
        Button(
            "📝 History",
            onclick="switchTab('history')",
            id="tab-button-history",
            cls="tab-button px-4 py-2 text-base font-medium border-b-2 "
            "border-transparent text-gray-500 hover:text-gray-700",
        ),
        Button(
            "🎨 Visual",
            onclick="switchTab('visual')",
            id="tab-button-visual",
            cls="tab-button px-4 py-2 text-base font-medium border-b-2 "
            "border-transparent text-gray-500 hover:text-gray-700",
        ),
        Button(
            "ℹ️ Info",
            onclick="switchTab('info')",
            id="tab-button-info",
            cls="tab-button px-4 py-2 text-base font-medium border-b-2 "
            "border-transparent text-gray-500 hover:text-gray-700",
        ),
        Button(
            "📄 Export",
            onclick="switchTab('export')",
            id="tab-button-export",
            cls="tab-button px-4 py-2 text-base font-medium border-b-2 "
            "border-transparent text-gray-500 hover:text-gray-700",
        ),
        cls="flex gap-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 px-4",
    )

    tab_contents = Div(
        Div(
            Div(
                *transcription_tab_content(doc_id, library, page_idx, error_msg=ocr_error, is_loading=is_ocr_loading),
                id="transcription-container",
                cls="relative h-full",
            ),
            id="tab-content-transcription",
            cls="tab-content h-full",
        ),
        Div(
            *snippets_tab_content(doc_id, page_idx, library),
            id="tab-content-snippets",
            cls="tab-content hidden h-full",
        ),
        Div(
            *history_tab_content(doc_id, page_idx, library, info_message=history_message),
            id="tab-content-history",
            cls="tab-content hidden h-full",
        ),
        Div(*visual_tab_content(), id="tab-content-visual", cls="tab-content hidden h-full"),
        Div(
            *info_tab_content(meta, total_pages, manifest_json, page_idx, doc_id, library),
            id="tab-content-info",
            cls="tab-content hidden h-full",
        ),
        Div(
            export_fragment if export_fragment is not None else Div("Export non disponibile.", cls="text-sm p-2"),
            id="tab-content-export",
            cls="tab-content hidden h-full",
        ),
        cls="flex-1 overflow-y-auto p-4",
    )

    switch_script = Script("""
        function switchTab(t){
            document.querySelectorAll('.tab-content').forEach(e=>e.classList.add('hidden'));
            document.querySelectorAll('.tab-button').forEach(b=>{
                b.classList.remove('active','border-indigo-600','text-indigo-600');
                b.classList.add('border-transparent', 'text-gray-500');
            });
            document.getElementById('tab-content-'+t).classList.remove('hidden');
            const btn = document.getElementById('tab-button-'+t);
            btn.classList.add('active','border-indigo-600','text-indigo-600');
            btn.classList.remove('border-transparent', 'text-gray-500');
        }
    """)

    main_panel = Div(buttons, tab_contents, switch_script, cls="flex flex-col h-full overflow-hidden")

    overlay = None
    overlay_script = None
    if is_ocr_loading:
        encoded_doc = quote(doc_id, safe="")
        encoded_lib = quote(library, safe="")
        hx_path = f"/api/check_ocr_status?doc_id={encoded_doc}&library={encoded_lib}&page={page_idx}"

        overlay = Div(
            Div(
                Div(cls="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4"),
                Span("AI in ascolto...", cls="text-indigo-600 font-bold tracking-widest uppercase text-[10px]"),
                cls="flex flex-col items-center justify-center h-full",
            ),
            cls=(
                "absolute inset-0 bg-white/90 dark:bg-gray-950/90 backdrop-blur-[2px] z-50 rounded-xl "
                "flex items-center justify-center pointer-events-auto"
            ),
            hx_get=hx_path,
            hx_trigger="every 2s",
            hx_target="#studio-right-panel",
            hx_swap="outerHTML",
        )

        doc_js = json.dumps(doc_id)
        lib_js = json.dumps(library)
        timeout_ms = 60000
        overlay_script = Script(
            f"""(function() {{
                const panel = document.getElementById('studio-right-panel');
                if (!panel) return;
                const docId = {doc_js};
                const libId = {lib_js};
                const pageIdx = {page_idx};
                const timeoutMs = {timeout_ms};
                let resolved = false;
                const timeoutId = window.setTimeout(() => {{
                    if (!resolved) {{
                        console.warn(
                            'OCR poll appears stuck for doc',
                            docId,
                            'lib', libId,
                            'page', pageIdx,
                            'after', timeoutMs, 'ms'
                        );
                    }}
                }}, timeoutMs);

                const handler = (event) => {{
                    if (event?.detail?.target?.id !== 'studio-right-panel') {{
                        return;
                    }}
                    resolved = true;
                    window.clearTimeout(timeoutId);
                    console.debug('OCR poll response received for doc', docId, 'page', pageIdx, event.detail);
                    panel.removeEventListener('htmx:afterSwap', handler);
                }};

                panel.addEventListener('htmx:afterSwap', handler);
            }})();"""
        )

    wrapper_children = [main_panel]
    if overlay:
        wrapper_children.append(overlay)
    if overlay_script:
        wrapper_children.append(overlay_script)

    return Div(*wrapper_children, cls="relative h-full")
