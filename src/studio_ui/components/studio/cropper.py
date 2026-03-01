"""Studio Cropper Modal Component."""

from fasthtml.common import H3, Button, Div, Form, Input, Label, NotStr, Script, Textarea


def render_cropper_modal(doc_id, library, page, img_url):
    """Render the cropper modal."""
    return Div(
        Div(
            Div(
                Div(
                    Div(
                        H3("✂️ Crea Nuovo Ritaglio", cls="text-lg font-bold"),
                        Button(
                            "✕",
                            onclick="document.getElementById('cropper-modal-container').innerHTML=''",
                            cls="app-btn app-btn-neutral",
                        ),
                        cls="flex justify-between items-center p-4 border-b border-slate-200 dark:border-slate-700",
                    ),
                    Div(
                        Div(
                            NotStr(f'<img id="cropper-image" src="{img_url}">'),
                            cls="max-h-[60vh] overflow-hidden bg-black flex justify-center",
                        ),
                        cls="p-4 bg-slate-100 dark:bg-slate-900/60",
                    ),
                    Div(
                        Form(
                            Input(type="hidden", name="doc_id", value=doc_id),
                            Input(type="hidden", name="library", value=library),
                            Input(type="hidden", name="page", value=str(page)),
                            Input(type="hidden", id="crop-data", name="crop_data"),
                            Div(
                                Label("Trascrizione / Nota", cls="app-label mb-1"),
                                Textarea(
                                    name="transcription",
                                    rows="2",
                                    cls="app-field",
                                ),
                                cls="mb-4",
                            ),
                            Button(
                                "Salva Snippet",
                                type="submit",
                                cls="w-full app-btn app-btn-primary font-bold py-3 transition",
                            ),
                            hx_post="/api/save_snippet",
                            hx_target="#tab-content-snippets",
                            hx_indicator="#ocr-loading",
                            onclick="if(!prepareCropData()) return false;",
                        ),
                        cls="p-6 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40",
                    ),
                    cls="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-4xl overflow-hidden "
                    "animate-in zoom-in-95 duration-200",
                ),
                cls="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-[9999]",
            ),
            Script("""
            let cropper;
            function initCropper(){
                const img=document.getElementById('cropper-image');
                if(img) cropper=new Cropper(img,{
                    viewMode: 1,
                    dragMode: 'crop',
                    autoCropArea: 0.5,
                    restore: false,
                    guides: true,
                    center: true,
                    highlight: false,
                    cropBoxMovable: true,
                    cropBoxResizable: true,
                    toggleDragModeOnDblclick: false,
                });
            }
            function prepareCropData(){
                if(!cropper)return false;
                document.getElementById('crop-data').value=JSON.stringify(cropper.getData(true));
                return true;
            }
            setTimeout(initCropper, 100);
        """),
            id="cropper-modal",
        )
    )
