"""Mirador Viewer Component (FastTags).

This component initializes Mirador and crucially sets up a Redux Store subscriber.
The subscriber listens for 'mirador/SET_CANVAS' or window updates and dispatches
a standard DOM CustomEvent 'mirador:page-changed' that HTMX can listen to.
"""

import json

from fasthtml.common import Div, Script

from studio_ui.common.mirador import window_config_json


def mirador_viewer(
    manifest_url: str,
    container_id: str = "mirador-viewer",
    canvas_id: str | None = None,
    initial_page: int | None = None,
) -> list:
    """Return the HTML/JS required to render Mirador with Redux bridging.

    Args:
        manifest_url: The URL of the IIIF manifest to load.
        container_id: The ID of the HTML div element.
        canvas_id: Optional initial canvas ID to display.
        initial_page: Optional 1-based page hint used when the server cannot resolve a canvas ID.
    """
    config_json = window_config_json(manifest_url, canvas_id)

    return [
        # 1. Container Div
        Div(id=container_id, cls="w-full h-full relative z-0"),
        # 2. Initialization Script
        Script(f"""
            (function() {{
                const containerId = {json.dumps(container_id)};
                const manifestId = {json.dumps(manifest_url)};
                const initialPage = {json.dumps(initial_page)};

                function resolveCanvasId(manifestJson, page) {{
                    const targetIndex = Number(page) - 1;
                    if (targetIndex < 0) return null;

                    if (manifestJson.sequences) {{
                        const canvases = ((manifestJson.sequences || [{{}}])[0] || {{}}).canvases || [];
                        const canvas = canvases[targetIndex];
                        return canvas ? (canvas['@id'] || canvas.id || null) : null;
                    }}

                    const items = manifestJson.items || [];
                    const canvas = items[targetIndex];
                    return canvas ? (canvas['@id'] || canvas.id || null) : null;
                }}

                function initMirador() {{
                    if (!window.Mirador) {{
                        console.warn('Mirador library not loaded yet, retrying...');
                        setTimeout(initMirador, 100);
                        return;
                    }}

                    console.log('🚀 Initializing Mirador...');

                    // Create Instance
                    const miradorInstance = Mirador.viewer({{
                        id: containerId,
                        windows: [{{
                            ...{config_json},
                            hideWindowTitle: true,
                            sideBarOpen: false,
                            allowClose: false,
                            allowMaximize: false,
                            defaultSideBarPanel: 'none',
                        }}],
                        workspace: {{
                            type: 'mosaic', // Mosaic workspace allows multiple windows but we use only one
                            allowNewWindows: false,
                            showZoomControls: true,
                        }},
                        workspaceControlPanel: {{
                            enabled: false, // Disables the circle "+" button
                        }},
                        window: {{
                            allowClose: false,
                            allowFullscreen: true,
                            allowMaximize: false,
                            sideBarPanel: 'none',
                            defaultSideBarPanel: 'none',
                        }},
                        // Theming to match the app
                        theme: {{
                            palette: {{
                                type: 'dark',
                                primary: {{
                                    main: '#4f46e5', // Indigo-600
                                }},
                            }},
                        }},
                    }});

                    // --- REDUX STORE SUBSCRIBER (The Bridge) ---
                    // This is the only way to reliably detect page changes in Mirador 3.

                    // Use json.dumps for the initial canvas ID safety too, though unlikely to be complex
                    let currentCanvasId = {json.dumps(canvas_id) if canvas_id else "''"};
                    let pendingInitialPage = !currentCanvasId && Number.isInteger(initialPage) && initialPage > 1
                        ? initialPage
                        : 0;

                    function tryApplyInitialPage(state) {{
                        if (!pendingInitialPage) return;

                        const winIds = Object.keys(state.windows);
                        if (winIds.length === 0) return;

                        const winId = winIds[0];
                        const windowState = state.windows[winId] || {{}};
                        const windowManifestId = windowState.manifestId || manifestId;
                        const manifestData = state.manifests[windowManifestId] || state.manifests[manifestId];
                        if (!manifestData || !manifestData.json) return;

                        const targetCanvasId = resolveCanvasId(manifestData.json, pendingInitialPage);
                        if (!targetCanvasId) return;

                        pendingInitialPage = 0;
                        if (windowState.canvasId === targetCanvasId) {{
                            currentCanvasId = targetCanvasId;
                            return;
                        }}

                        currentCanvasId = targetCanvasId;
                        miradorInstance.store.dispatch({{
                            type: 'mirador/SET_CANVAS',
                            windowId: winId,
                            canvasId: targetCanvasId
                        }});
                    }}

                    miradorInstance.store.subscribe(() => {{
                        const state = miradorInstance.store.getState();
                        tryApplyInitialPage(state);

                        // We normally have only one window in this app
                        const winIds = Object.keys(state.windows);
                        if (winIds.length === 0) return;

                        const winId = winIds[0];
                        const newCanvasId = state.windows[winId].canvasId;

                        // Detect change
                        if (newCanvasId && newCanvasId !== currentCanvasId) {{
                            currentCanvasId = newCanvasId;
                            console.log('🔔 Mirador Canvas Changed:', newCanvasId);

                            // We need to map this Canvas ID back to a page index.
                            // We look it up in the manifest stored in Redux.
                            const manifestData = state.manifests[manifestId];
                            if (manifestData && manifestData.json) {{
                                // Try to find index in sequences (IIIF v2) or items (IIIF v3)
                                let pageIndex = -1;

                                // V2
                                if (manifestData.json.sequences) {{
                                    const canvases = manifestData.json.sequences[0].canvases;
                                    pageIndex = canvases.findIndex(c => c['@id'] === newCanvasId);
                                }}
                                // V3
                                else if (manifestData.json.items) {{
                                    const items = manifestData.json.items;
                                    pageIndex = items.findIndex(c => c.id === newCanvasId);
                                }}

                                if (pageIndex !== -1) {{
                                    // Dispatch Custom Event for HTMX / Studio.py
                                    // +1 because users expect 1-based page numbers
                                    const event = new CustomEvent('mirador:page-changed', {{
                                        detail: {{
                                            page: pageIndex + 1,
                                            canvasId: newCanvasId
                                        }}
                                    }});
                                    document.dispatchEvent(event);
                                }}
                            }}
                        }}
                    }});

                    // Store instance globally for external control (e.g. navigation buttons)
                    window.miradorInstance = miradorInstance;
                    tryApplyInitialPage(miradorInstance.store.getState());
                }}

                // Start initialization
                if (document.readyState === 'loading') {{
                    document.addEventListener('DOMContentLoaded', initMirador);
                }} else {{
                    initMirador();
                }}
            }})();
        """),
    ]
