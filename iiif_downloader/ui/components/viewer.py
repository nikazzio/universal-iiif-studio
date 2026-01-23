import base64
from io import BytesIO

import streamlit as st
import streamlit.components.v1 as components

from iiif_downloader.config_manager import get_config_manager


def inject_premium_styles():
    """Inject basic CSS for the page."""
    st.markdown(
        """
    <style>
        /* This hides the default padding for components to make them flush */
        iframe { border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.15) !important; }
    </style>
    """,
        unsafe_allow_html=True,
    )


def interactive_viewer(image, zoom_percent: int):
    """
    Render the premium interactive image viewer using an isolated iframe component.
    """
    if not image:
        return

    # Get base64 and dimensions
    quality = get_config_manager().get_setting("images.viewer_quality", 95)
    buffered = BytesIO()
    image.save(buffered, format="JPEG", quality=quality)
    img_b64 = base64.b64encode(buffered.getvalue()).decode()

    initial_scale = max(0.1, float(zoom_percent) / 100.0)

    # Isolated HTML Component
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body, html {{
                margin: 0; padding: 0; width: 100%; height: 100%;
                background: #1a1a1e; overflow: hidden; font-family: 'Inter', sans-serif;
                touch-action: none;
            }}
            .viewer-container {{
                width: 100%; height: 100%; position: relative;
                display: flex; justify-content: center; align-items: center;
                cursor: grab; user-select: none;
            }}
            .viewer-container:active {{ cursor: grabbing; }}
            .viewer-image {{
                position: absolute; top: 0; left: 0;
                width: auto; height: auto; max-width: none; max-height: none;
                box-shadow: 0 10px 60px rgba(0,0,0,0.5);
                transform-origin: 0 0; will-change: transform;
                pointer-events: none;
            }}
            .viewer-controls {{
                position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
                display: flex; gap: 8px; background: rgba(30, 30, 35, 0.9);
                backdrop-filter: blur(10px); padding: 8px 16px;
                border-radius: 40px; border: 1px solid rgba(255, 255, 255, 0.2);
                z-index: 1000; box-shadow: 0 4px 20px rgba(0,0,0,0.5);
                pointer-events: auto;
            }}
            .v-btn {{
                width: 36px; height: 36px; border-radius: 50%; border: 1px solid rgba(255, 255, 255, 0.1);
                background: rgba(255, 255, 255, 0.05); color: white; cursor: pointer;
                display: flex; justify-content: center; align-items: center;
                font-size: 16px; transition: all 0.2s;
            }}
            .v-btn:hover {{ background: rgba(255, 255, 255, 0.2); transform: scale(1.1); }}
        </style>
    </head>
    <body>
        <div class="viewer-container" id="v-cnt">
            <img src="data:image/jpeg;base64,{img_b64}" class="viewer-image" id="v-img">
            <div class="viewer-controls">
                <button class="v-btn" onclick="vReset()">⟲</button>
                <button class="v-btn" onclick="vZoom(0.8)">-</button>
                <button class="v-btn" onclick="vZoom(1.2)">+</button>
                <span style="width: 1px; background: rgba(255,255,255,0.2); margin: 0 4px;"></span>
                <button class="v-btn" onclick="vMove(0, 100)">↑</button>
                <button class="v-btn" onclick="vMove(0, -100)">↓</button>
            </div>
        </div>

        <script>
            const cnt = document.getElementById('v-cnt');
            const img = document.getElementById('v-img');

            const initialScale = {initial_scale};

            // State
            let state = {{ scale: initialScale, x: 0, y: 0 }};
            let isPanning = false;
            let start = {{ x: 0, y: 0 }};

            function updateTransform() {{
                img.style.transform = `translate(${{state.x}}px, ${{state.y}}px) scale(${{state.scale}})`;
            }}

            window.vZoom = (factor) => {{
                state.scale *= factor;
                updateTransform();
            }};

            window.vMove = (dx, dy) => {{
                state.x += dx; state.y += dy;
                updateTransform();
            }};

            window.vReset = () => {{
                const cntW = cnt.clientWidth;
                const cntH = cnt.clientHeight;
                const imgW = img.naturalWidth;
                const imgH = img.naturalHeight;
                const scaleW = cntW / imgW;
                const scaleH = cntH / imgH;
                const fitScale = Math.min(scaleW, scaleH) * 0.95;
                state.scale = fitScale;
                state.x = (cntW - imgW * fitScale) / 2;
                state.y = (cntH - imgH * fitScale) / 2;
                updateTransform();
            }};

            cnt.addEventListener('pointerdown', (e) => {{
                if (e.target.tagName === 'BUTTON') return;
                isPanning = true;
                start = {{ x: e.clientX - state.x, y: e.clientY - state.y }};
                cnt.setPointerCapture(e.pointerId);
                e.preventDefault();
            }});

            window.addEventListener('pointermove', (e) => {{
                if (!isPanning) return;
                state.x = e.clientX - start.x;
                state.y = e.clientY - start.y;
                updateTransform();
            }});

            const stop = () => isPanning = false;
            window.addEventListener('pointerup', stop);
            window.addEventListener('pointercancel', stop);

            cnt.addEventListener('wheel', (e) => {{
                e.preventDefault();
                const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
                const rect = cnt.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;
                const beforeX = (mouseX - state.x) / state.scale;
                const beforeY = (mouseY - state.y) / state.scale;
                state.scale *= zoomFactor;
                state.x = mouseX - beforeX * state.scale;
                state.y = mouseY - beforeY * state.scale;
                updateTransform();
            }}, {{ passive: false }});

            img.onload = () => window.vReset();
            if (img.complete && img.naturalWidth > 0) window.vReset();

        </script>
    </body>
    </html>
    """

    components.html(html_code, height=800)
