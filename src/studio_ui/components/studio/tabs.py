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
    export_url: str | None = None,
):
    """Render the studio tabs."""
    page_idx = int(page)
    # Header buttons
    buttons = Div(
        Button(
            "📝 Trascrizione",
            onclick="switchTab('transcription')",
            id="tab-button-transcription",
            cls="tab-button studio-tab studio-tab-active",
        ),
        Button(
            "📂 Snippets",
            onclick="switchTab('snippets')",
            id="tab-button-snippets",
            cls="tab-button studio-tab",
        ),
        Button(
            "📝 History",
            onclick="switchTab('history')",
            id="tab-button-history",
            cls="tab-button studio-tab",
        ),
        Button(
            "🎨 Visual",
            onclick="switchTab('visual')",
            id="tab-button-visual",
            cls="tab-button studio-tab",
        ),
        Button(
            "ℹ️ Info",
            onclick="switchTab('info')",
            id="tab-button-info",
            cls="tab-button studio-tab",
        ),
        Button(
            "📄 Export",
            onclick="switchTab('export')",
            id="tab-button-export",
            cls="tab-button studio-tab",
        ),
        cls="studio-tablist",
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
            (
                export_fragment
                if export_fragment is not None
                else Div(
                    "Apri il tab Export per caricare miniature e strumenti di esportazione.",
                    cls="text-sm text-slate-500 dark:text-slate-400 p-2",
                )
            ),
            id="tab-content-export",
            cls="tab-content hidden h-full",
            data_export_loaded="1" if export_fragment is not None else "0",
            data_export_url=export_url or "",
        ),
        cls="flex-1 overflow-y-auto p-4",
    )

    switch_script = Script("""
        function switchTab(t){
            document.querySelectorAll('.tab-content').forEach(e=>e.classList.add('hidden'));
            document.querySelectorAll('.tab-button').forEach(b=>{
                b.classList.remove('studio-tab-active');
            });
            const target = document.getElementById('tab-content-'+t);
            if (!target) return;
            target.classList.remove('hidden');
            const btn = document.getElementById('tab-button-'+t);
            if (btn) {
                btn.classList.add('studio-tab-active');
            }

            if (t === 'export') {
                const loaded = target.dataset.exportLoaded === '1';
                const exportUrl = target.dataset.exportUrl || '';
                if (!loaded && exportUrl) {
                    target.dataset.exportLoaded = '1';
                    try {
                        htmx.ajax('GET', exportUrl, {target:'#tab-content-export', swap:'innerHTML'});
                    } catch (e) {
                        console.error('export-load-err', e);
                        target.dataset.exportLoaded = '0';
                    }
                }
            }
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
                Div(
                    cls="animate-spin rounded-full h-8 w-8 border-b-2 mb-4",
                    style="border-color: var(--app-accent);",
                ),
                Span(
                    "AI in ascolto...",
                    cls="font-bold tracking-widest uppercase text-[10px]",
                    style="color: var(--app-primary);",
                ),
                cls="flex flex-col items-center justify-center h-full",
            ),
            cls=(
                "absolute inset-0 bg-white/90 dark:bg-slate-950/90 backdrop-blur-[2px] z-50 rounded-xl "
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
