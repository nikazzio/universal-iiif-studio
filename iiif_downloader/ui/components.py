import streamlit as st
import streamlit.components.v1 as components
import base64
from io import BytesIO

def inject_premium_styles():
    """Inject basic CSS for the page."""
    st.markdown("""
    <style>
        /* This hides the default padding for components to make them flush */
        iframe { border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.15) !important; }
    </style>
    """, unsafe_allow_html=True)

def interactive_viewer(image, zoom_percent: int):
    """Render the premium interactive image viewer using an isolated iframe component."""
    if not image:
        return
    
    # Get base64
    buffered = BytesIO()
    image.save(buffered, format="JPEG", quality=85)
    img_b64 = base64.b64encode(buffered.getvalue()).decode()
    
    # Isolated HTML Component
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body, html {{ 
                margin: 0; padding: 0; width: 100%; height: 100%; 
                background: #1a1a1e; overflow: hidden; font-family: sans-serif;
                touch-action: none;
            }}
            .viewer-container {{
                width: 100%; height: 100%; position: relative;
                display: flex; justify-content: center; align-items: center;
                cursor: grab; user-select: none;
            }}
            .viewer-container:active {{ cursor: grabbing; }}
            .viewer-image {{
                max-width: none; position: absolute;
                box-shadow: 0 10px 60px rgba(0,0,0,1);
                transform-origin: 0 0; will-change: transform;
                pointer-events: none; /* Let the container handle dragging */
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
            <img src="data:image/jpeg;base64,{img_b64}" class="viewer-image" id="v-img" style="width: {zoom_percent}%;">
            <div class="viewer-controls">
                <button class="v-btn" onclick="vMove(0, 100)">↑</button>
                <button class="v-btn" onclick="vMove(0, -100)">↓</button>
                <button class="v-btn" onclick="vMove(100, 0)">←</button>
                <button class="v-btn" onclick="vMove(-100, 0)">→</button>
                <span style="width: 1px; background: rgba(255,255,255,0.2); margin: 0 4px;"></span>
                <button class="v-btn" onclick="vZoom(1.2)">+</button>
                <button class="v-btn" onclick="vZoom(0.8)">-</button>
                <button class="v-btn" onclick="vReset()">⟲</button>
            </div>
        </div>

        <script>
            const cnt = document.getElementById('v-cnt');
            const img = document.getElementById('v-img');
            let scale = 1, pointX = 0, pointY = 0, start = {{ x: 0, y: 0 }}, isPanning = false;

            function setTransform() {{
                img.style.transform = `translate(${{pointX}}px, ${{pointY}}px) scale(${{scale}})`;
            }}

            // Handle Pointer Down
            cnt.addEventListener('pointerdown', (e) => {{
                if (e.target.tagName === 'BUTTON') return;
                isPanning = true;
                start = {{ x: e.clientX - pointX, y: e.clientY - pointY }};
                cnt.setPointerCapture(e.pointerId);
                e.preventDefault();
            }});

            // Handle Pointer Move
            window.addEventListener('pointermove', (e) => {{
                if (!isPanning) return;
                pointX = e.clientX - start.x;
                pointY = e.clientY - start.y;
                setTransform();
            }});

            // Handle Pointer Up (Global)
            const stopPanning = (e) => {{
                if (!isPanning) return;
                isPanning = false;
                if(cnt.releasePointerCapture && e) cnt.releasePointerCapture(e.pointerId);
            }};

            window.addEventListener('pointerup', stopPanning);
            window.addEventListener('pointercancel', stopPanning);
            window.addEventListener('blur', stopPanning); // Emergency release if window loses focus

            // Mouse Wheel Zoom
            cnt.onwheel = (e) => {{
                e.preventDefault();
                const xs = (e.clientX - pointX) / scale;
                const ys = (e.clientY - pointY) / scale;
                const delta = e.wheelDelta ? e.wheelDelta : -e.deltaY;
                (delta > 0) ? (scale *= 1.1) : (scale /= 1.1);
                pointX = e.clientX - xs * scale;
                pointY = e.clientY - ys * scale;
                setTransform();
            }};

            window.vZoom = (f) => {{ scale *= f; setTransform(); }};
            window.vMove = (dx, dy) => {{ pointX += dx; pointY += dy; setTransform(); }};
            window.vReset = () => {{ scale = 1; pointX = 0; pointY = 0; setTransform(); }};

            img.onload = () => {{ 
                pointX = (cnt.clientWidth - img.clientWidth) / 2;
                pointY = (cnt.clientHeight - img.clientHeight) / 2;
                setTransform(); 
            }};
            if (img.complete) img.onload();
        </script>
    </body>
    </html>
    """
    
    components.html(html_code, height=650)
