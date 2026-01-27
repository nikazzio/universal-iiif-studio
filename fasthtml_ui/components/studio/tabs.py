"""Studio Tabs Manager Component."""

from fasthtml.common import Button, Div, Script

from fasthtml_ui.components.studio.history import history_tab_content
from fasthtml_ui.components.studio.info import info_tab_content, visual_tab_content
from fasthtml_ui.components.studio.snippets import snippets_tab_content
from fasthtml_ui.components.studio.transcription import transcription_tab_content


def render_studio_tabs(doc_id, library, page, meta, total_pages):
    """Render the studio tabs."""
    return Div(
        Div(
            Button(
                "📝 Trascrizione",
                onclick="switchTab('transcription')",
                id="tab-button-transcription",
                cls="tab-button active px-4 py-2 text-sm font-medium border-b-2 "
                "border-indigo-600 text-indigo-600 dark:text-indigo-400",
            ),
            Button(
                "📂 Snippets",
                onclick="switchTab('snippets')",
                id="tab-button-snippets",
                cls="tab-button px-4 py-2 text-sm font-medium border-b-2 "
                "border-transparent text-gray-500 hover:text-gray-700",
            ),
            Button(
                "📝 History",
                onclick="switchTab('history')",
                id="tab-button-history",
                cls="tab-button px-4 py-2 text-sm font-medium border-b-2 "
                "border-transparent text-gray-500 hover:text-gray-700",
            ),
            Button(
                "🎨 Visual",
                onclick="switchTab('visual')",
                id="tab-button-visual",
                cls="tab-button px-4 py-2 text-sm font-medium border-b-2 "
                "border-transparent text-gray-500 hover:text-gray-700",
            ),
            Button(
                "ℹ️ Info",
                onclick="switchTab('info')",
                id="tab-button-info",
                cls="tab-button px-4 py-2 text-sm font-medium border-b-2 "
                "border-transparent text-gray-500 hover:text-gray-700",
            ),
            cls="flex gap-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 px-4",
        ),
        Div(
            Div(
                Div(
                    *transcription_tab_content(doc_id, library, page),
                    id="transcription-container",
                    cls="relative h-full"
                ),
                id="tab-content-transcription",
                cls="tab-content h-full",
            ),
            Div(
                *snippets_tab_content(doc_id, page, library),
                id="tab-content-snippets",
                cls="tab-content hidden h-full",
            ),
            Div(
                *history_tab_content(doc_id, page, library),
                id="tab-content-history",
                cls="tab-content hidden h-full",
            ),
            Div(*visual_tab_content(), id="tab-content-visual", cls="tab-content hidden h-full"),
            Div(*info_tab_content(meta, total_pages), id="tab-content-info", cls="tab-content hidden h-full"),
            cls="flex-1 overflow-y-auto p-4",
        ),
        Script("""
            function switchTab(t){
                document.querySelectorAll('.tab-content').forEach(e=>e.classList.add('hidden'));
                document.querySelectorAll('.tab-button').forEach(b=>{
                    b.classList.remove('active','border-indigo-600','text-indigo-600');
                    b.classList.add('border-transparent', 'text-gray-500');
                });
                document.getElementById('tab-content-'+t).classList.remove('hidden');
                const btn = document.getElementById('tab-button-'+t);
                btn.classList.add('active','border-indigo-600','text-indigo-600');
                btn.classList.remove('border-transparent', 'text-gray-500');
            }
        """),
        cls="flex flex-col h-full overflow-hidden",
    )
