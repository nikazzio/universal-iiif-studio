"""Navigation Controls Component.

Controlli per la navigazione tra le pagine del manoscritto.
Utilizza ID assoluti e un encoding robusto per sincronizzarsi con Mirador.
"""

from fasthtml.common import Button, Div, Input, Script, Span


def page_navigation(doc_id: str, library: str, current_page: int, total_pages: int) -> Div:
    """Generate page navigation controls."""
    has_prev = current_page > 1
    has_next = current_page < total_pages

    return Div(
        # Navigation bar
        Div(
            # Left: Prev button
            Button(
                "← Precedente",
                onclick=f"navigateToPage({current_page - 1})",
                disabled=not has_prev,
                cls=_button_classes(has_prev),
            ),
            # Center: Page info
            Div(
                Span(
                    f"Pagina {current_page} di {total_pages}",
                    id="page-counter",
                    cls="font-mono text-sm font-bold text-indigo-600",
                ),
                cls="flex items-center",
            ),
            # Right: Next button
            Button(
                "Successiva →",
                onclick=f"navigateToPage({current_page + 1})",
                disabled=not has_next,
                cls=_button_classes(has_next),
            ),
            cls="flex justify-between items-center px-6 py-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700",
        ),
        # Page slider
        Div(
            Input(
                type="range",
                min="1",
                max=str(total_pages),
                value=str(current_page),
                id="page-slider",
                oninput="updateSliderLabel(this.value)",
                onchange="navigateToPage(this.value)",
                cls="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer",
            ),
            Div(
                id="slider-label",
                cls="hidden absolute bg-black text-white text-[10px] px-2 py-1 rounded pointer-events-none z-50",
            ),
            cls="relative px-6 py-2 bg-gray-50 dark:bg-gray-900",
        ),
        # Script per navigazione sincronizzata
        Script(f"""
            const docId = '{doc_id}';
            const library = '{library}';
            const totalPages = {total_pages};

            function navigateToPage(page) {{
                page = parseInt(page);
                if (page < 1 || page > totalPages) return;
                
                console.log('🚀 Navigating to page:', page);
                
                // 1. Update URL (history API)
                const url = new URL(window.location);
                url.searchParams.set('page', page);
                window.history.pushState({{}}, '', url);
                
                // 2. Update Mirador via Redux dispatch (Robust Lookup)
                if (window.miradorInstance) {{
                    const state = window.miradorInstance.store.getState();
                    const windowId = Object.keys(state.windows)[0];
                    
                    if (windowId) {{
                        const manifestId = state.windows[windowId].manifestId;
                        const manifest = state.manifests[manifestId];
                        
                        if (manifest && manifest.json) {{
                            // Strategy: Find the N-th canvas in the sequence
                            // Use Mirador's selectors logic (simplified)
                            const sequences = manifest.json.sequences;
                            if (sequences && sequences.length > 0) {{
                                const canvases = sequences[0].canvases;
                                const targetIndex = page - 1;
                                
                                if (canvases && canvases[targetIndex]) {{
                                    const targetCanvasId = canvases[targetIndex]['@id'] || canvases[targetIndex].id;
                                    console.log('✅ Found Canvas ID in store:', targetCanvasId);
                                    
                                    window.miradorInstance.store.dispatch({{
                                        type: 'mirador/SET_CANVAS',
                                        windowId: windowId,
                                        canvasId: targetCanvasId
                                    }});
                                }} else {{
                                    console.error('❌ Canvas index out of bounds:', targetIndex);
                                }}
                            }}
                        }}
                    }}
                }}
                
                // 3. Update UI via HTMX
                htmx.ajax('GET', `/studio/partial/tabs?doc_id=${{encodeURIComponent(docId)}}&library=${{encodeURIComponent(library)}}&page=${{page}}`, {{
                    target: '#studio-right-panel',
                    swap: 'innerHTML'
                }});
                
                // Aggiornamento componenti locali
                const counter = document.getElementById('page-counter');
                if (counter) counter.textContent = `Pagina ${{page}} di ${{totalPages}}`;
                const slider = document.getElementById('page-slider');
                if (slider) slider.value = page;
            }}

            function updateSliderLabel(value) {{
                const label = document.getElementById('slider-label');
                const slider = document.getElementById('page-slider');
                if (!label || !slider) return;
                
                const rect = slider.getBoundingClientRect();
                const percent = (value - 1) / (totalPages - 1);
                const left = rect.left + (rect.width * percent);

                label.textContent = `P.${{value}}`;
                label.style.left = `${{left}}px`;
                label.style.top = `-25px`;
                label.classList.remove('hidden');
            }}

            const sl = document.getElementById('page-slider');
            if(sl) sl.addEventListener('mouseleave', () => {{
                const l = document.getElementById('slider-label');
                if(l) l.classList.add('hidden');
            }});
        """),
        cls="w-full",
    )


def _button_classes(enabled: bool) -> str:
    base = "px-4 py-1.5 rounded text-sm font-bold transition-all shadow-sm active:scale-95"
    if enabled:
        return f"{base} bg-indigo-600 text-white hover:bg-indigo-700"
    return f"{base} bg-gray-200 text-gray-400 cursor-not-allowed shadow-none"
