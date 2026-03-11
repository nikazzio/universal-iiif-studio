"""Studio workspace page layouts."""

import json

from fasthtml.common import H2, A, Div, Script, Span

from studio_ui.components.studio.status_panel import technical_status_panel
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
    export_fragment=None,
    export_url: str | None = None,
    asset_status: str = "",
    has_native_pdf: bool | None = None,
    pdf_local_available: bool = False,
    local_pages_count: int = 0,
    temp_pages_count: int = 0,
    manifest_total_pages: int = 0,
    read_source_mode: str = "remote",
    mirador_enabled: bool = True,
    mirador_initial_page: int | None = None,
    mirador_override_url: str = "",
    active_tab: str = "transcription",
    source_notice_text: str = "",
    source_notice_tone: str = "info",
):
    """Render the main Studio split-view layout."""
    status_value = (asset_status or "unknown").strip().lower()
    source_mode = str(read_source_mode or "remote").strip().lower()
    source_value = source_mode if source_mode in {"local", "remote"} else "remote"
    status_value = status_value or "unknown"
    if has_native_pdf is True:
        pdf_source_value = "native"
    elif has_native_pdf is False:
        pdf_source_value = "images"
    else:
        pdf_source_value = "unknown"
    pdf_local_value = "yes" if pdf_local_available else "no"
    staging_count = int(temp_pages_count or 0)
    local_count = int(local_pages_count or 0)
    manifest_count = int(manifest_total_pages or 0)
    local_progress = f"{local_count}/{manifest_count}" if manifest_count > 0 else str(local_count)
    notice_text = str(source_notice_text or "").strip()
    notice_palette = {
        "info": "border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-800/70 dark:bg-sky-950/30 dark:text-sky-100",
        "warning": (
            "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-800/70 "
            "dark:bg-amber-950/30 dark:text-amber-100"
        ),
    }
    notice_cls = notice_palette.get(source_notice_tone, notice_palette["info"])
    if mirador_enabled:
        viewer_block = Div(
            *mirador_viewer(
                manifest_url,
                "mirador-viewer",
                canvas_id=initial_canvas,
                initial_page=mirador_initial_page,
            ),
            cls="flex-none bg-slate-900 border-r border-slate-200 dark:border-slate-700",
            style="width: 55%;",
        )
    else:
        viewer_block = Div(
            Div(
                Span(
                    "Viewer bloccato finche non sono disponibili tutte le immagini locali.",
                    cls="text-sm font-semibold",
                ),
                Span(
                    f"Pagine locali: {local_progress} • Temporanee: {staging_count}",
                    cls="text-xs text-slate-300",
                ),
                (
                    Span(
                        "Apri comunque Mirador (puo mostrare anteprime remote non ancora locali).",
                        cls="text-xs text-slate-400",
                    )
                    if mirador_override_url
                    else ""
                ),
                (
                    A(
                        "Apri Mirador comunque",
                        href=mirador_override_url,
                        cls="app-btn app-btn-warning text-xs",
                    )
                    if mirador_override_url
                    else ""
                ),
                cls="flex flex-col gap-3 p-5 max-w-md",
            ),
            cls=(
                "flex-none bg-slate-900 border-r border-slate-200 dark:border-slate-700 "
                "text-slate-100 flex items-center justify-center"
            ),
            style="width: 55%;",
            **{"data-mirador-gated": "1"},
        )

    return Div(
        Div(
            # LEFT: Mirador (55%)
            viewer_block,
            # RIGHT: Editor (45%)
            Div(
                Div(
                    Div(
                        Div(
                            Div(
                                H2(
                                    title,
                                    title=title,
                                    cls="text-3xl font-black text-slate-900 dark:text-white tracking-tight mb-3",
                                ),
                                technical_status_panel(
                                    doc_id=doc_id,
                                    library=library,
                                    state=status_value,
                                    read_source=source_value,
                                    scans_local=local_progress,
                                    staging_pages=str(staging_count),
                                    pdf_source=pdf_source_value,
                                    pdf_local=pdf_local_value,
                                ),
                                (
                                    Div(
                                        notice_text,
                                        cls=f"mt-3 rounded-lg border px-3 py-2 text-sm font-medium {notice_cls}",
                                        data_studio_source_notice=source_mode,
                                    )
                                    if notice_text
                                    else ""
                                ),
                                cls="flex-1 min-w-0",
                            ),
                            cls="flex items-start justify-between",
                        ),
                        cls="px-6 py-8 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/50",
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
                            export_fragment=export_fragment,
                            export_url=export_url,
                            active_tab=active_tab,
                        ),
                        id="studio-right-panel",
                        cls="flex-1 overflow-hidden h-full",
                    ),
                    cls="h-full flex flex-col",
                ),
                cls="flex-none bg-white dark:bg-slate-900 shadow-2xl z-10",
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

                    console.log('📄 Page changed to:', newPage);

                    const url = new URL(window.location.href);
                    const activeTab = (url.searchParams.get('tab') || 'transcription').trim() || 'transcription';
                    url.searchParams.set('page', newPage);
                    url.searchParams.set('tab', activeTab);
                    window.history.pushState({{}}, '', url);

                    const saveBody = new URLSearchParams();
                    saveBody.set('doc_id', docId);
                    saveBody.set('library', library);
                    saveBody.set('page', String(newPage));
                    saveBody.set('tab', activeTab);
                    fetch('/api/studio/context/save', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' }},
                        body: saveBody.toString(),
                        credentials: 'same-origin'
                    }}).catch(() => null);

                    const target = '/studio/partial/tabs?doc_id=' + encodeURIComponent(docId) +
                        '&library=' + encodeURIComponent(library) +
                        '&page=' + newPage +
                        '&tab=' + encodeURIComponent(activeTab);
                    htmx.ajax('GET', target, {{
                        target: '#studio-right-panel',
                        swap: 'innerHTML'
                    }});
                }});
            }})();
        """),
        cls="flex flex-col h-screen overflow-hidden",
    )
