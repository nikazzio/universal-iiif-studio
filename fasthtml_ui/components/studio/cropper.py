"""Studio Cropper Modal Component."""

from fasthtml.common import H3, Button, Div, Form, Input, Label, NotStr, Script, Textarea


def render_cropper_modal(doc_id, library, page, img_url):
    return Div(
        Div(
            Div(
                Div(
                    Div(
                        H3("✂️ Crea Nuovo Ritaglio", cls="text-lg font-bold"),
                        Button(
                            "✕",
                            onclick="document.getElementById('cropper-modal-container').innerHTML=''",
                            cls="text-gray-500 hover:text-gray-800",
                        ),
                        cls="flex justify-between items-center p-4 border-b",
                    ),
                    Div(
                        Div(
                            NotStr(f'<img id="cropper-image" src="{img_url}">'),
                            cls="max-h-[60vh] overflow-hidden bg-black flex justify-center",
                        ),
                        cls="p-4 bg-gray-100",
                    ),
                    Div(
                        Form(
                            Input(type="hidden", name="doc_id", value=doc_id),
                            Input(type="hidden", name="library", value=library),
                            Input(type="hidden", name="page", value=str(page)),
                            Input(type="hidden", id="crop-data", name="crop_data"),
                            Div(
                                Label("Trascrizione / Nota", cls="text-xs font-bold uppercase text-gray-500 mb-1"),
                                Textarea(
                                    name="transcription",
                                    rows="2",
                                    cls="w-full border rounded p-2 text-sm focus:ring-2 focus:ring-indigo-500",
                                ),
                                cls="mb-4",
                            ),
                            Button(
                                "Salva Snippet",
                                type="submit",
                                cls="w-full bg-indigo-600 hover:bg-indigo-700 text-white "
                                "font-bold py-3 rounded transition",
                            ),
                            hx_post="/api/save_snippet",
                            hx_target="#tab-content-snippets",
                            hx_indicator="#ocr-loading",
                            onclick="if(!prepareCropData()) return false;",
                        ),
                        cls="p-6 border-t bg-gray-50",
                    ),
                    cls="bg-white rounded-xl shadow-2xl w-full max-w-4xl overflow-hidden "
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
