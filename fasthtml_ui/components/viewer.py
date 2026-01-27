"""Mirador Viewer Component (FastTags).

This component initializes Mirador and crucially sets up a Redux Store subscriber.
The subscriber listens for 'mirador/SET_CANVAS' or window updates and dispatches
a standard DOM CustomEvent 'mirador:page-changed' that HTMX can listen to.
"""

import json

from fasthtml.common import Div, Script


def mirador_viewer(manifest_url: str, container_id: str = "mirador-viewer", canvas_id: str = None) -> list:
    """Return the HTML/JS required to render Mirador with Redux bridging.

    Args:
        manifest_url: The URL of the IIIF manifest to load.
        container_id: The ID of the HTML div element.
        canvas_id: Optional initial canvas ID to display.
    """
    # Configuration object (Python dictionary)
    window_config = {
        "manifestId": manifest_url,
        "thumbnailNavigationPosition": "far-bottom",
        "allowClose": False,
        "allowMaximize": False,
        "defaultSideBarPanel": "info",
        "sideBarOpenAtStartup": False,
        "views": [{"key": "single"}],
    }

    # If a specific canvas is requested, add it to the config
    if canvas_id:
        window_config["canvasId"] = canvas_id

    # STRICT REQUIREMENT: Serialize to JSON string to ensure booleans are valid JS (false/true)
    # and strings are properly quoted.
    window_config_json = json.dumps(window_config)

    return [
        # 1. Container Div
        Div(id=container_id, cls="w-full h-full relative z-0"),
        # 2. Initialization Script
        Script(f"""
            (function() {{
                const containerId = '{container_id}';
                const manifestId = '{manifest_url}';
                
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
                            ...{window_config_json},
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
                    
                    miradorInstance.store.subscribe(() => {{
                        const state = miradorInstance.store.getState();
                        
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
