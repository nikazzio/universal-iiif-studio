"""Studio Info and Visual Tabs Components."""

from fasthtml.common import H3, Button, Div, Input, Label, Script


def info_row(label, value):
    val = value[0] if isinstance(value, list) and value else value
    return Div(
        Div(label, cls="text-[10px] font-bold text-gray-400 uppercase tracking-widest"),
        Div(str(val), cls="text-sm font-medium text-gray-800 dark:text-gray-200 break-words"),
    )


def info_tab_content(meta, total_pages):
    return [
        Div(
            info_row("Titolo", meta.get("label", "N/A")),
            info_row("Biblioteca", meta.get("library") or meta.get("attribution", "N/A")),
            info_row("Pagine Totali", str(total_pages)),
            info_row("ID Documento", meta.get("id", "N/A")),
            cls="space-y-4 p-4 bg-white dark:bg-gray-800 rounded-xl border dark:border-gray-700",
        )
    ]


def visual_tab_content():
    return [
        Div(
            H3("Filtri Visual", cls="font-bold mb-4 text-gray-700 dark:text-gray-300"),
            Div(
                Label("Luminosità", for_="b-range", cls="text-xs uppercase font-bold text-gray-400"),
                Input(
                    type="range",
                    id="b-range",
                    min="0.5",
                    max="2",
                    step="0.1",
                    value="1",
                    oninput="applyF()",
                    cls="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer",
                ),
            ),
            Div(
                Label("Contrasto", for_="c-range", cls="text-xs uppercase font-bold text-gray-400 mt-4"),
                Input(
                    type="range",
                    id="c-range",
                    min="0.5",
                    max="2.5",
                    step="0.1",
                    value="1",
                    oninput="applyF()",
                    cls="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer",
                ),
            ),
            Button(
                "Reset Filtri",
                onclick="resF()",
                cls="w-full bg-gray-200 hover:bg-gray-300 text-gray-700 font-bold mt-6 py-2 rounded transition",
            ),
            Script("""
                function applyF(){
                    const b=document.getElementById('b-range').value;
                    const c=document.getElementById('c-range').value;
                    const v=document.getElementById('mirador-viewer');
                    if(v)v.style.filter=`brightness(${b}) contrast(${c})`;
                }
                function resF(){
                    document.getElementById('b-range').value=1;
                    document.getElementById('c-range').value=1;
                    applyF();
                }
            """),
            cls="p-4 bg-white dark:bg-gray-800 rounded-xl border dark:border-gray-700",
        )
    ]
