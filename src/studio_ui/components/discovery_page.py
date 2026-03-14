"""Top-level Discovery page content composition."""

from fasthtml.common import H2, H3, Div

from .discovery_form import discovery_form


def discovery_content(initial_preview=None, active_download_fragment=None) -> Div:
    """Top-level content block for the discovery page."""
    preview_block = initial_preview if initial_preview is not None else Div(id="discovery-preview", cls="mt-8")
    downloads_block = (
        active_download_fragment if active_download_fragment is not None else Div(id="download-manager-area")
    )

    return Div(
        H2("Discovery", cls="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-5"),
        Div(
            Div(
                discovery_form(),
                preview_block,
                cls="w-full xl:w-[66%] xl:pr-4",
            ),
            Div(
                H3("Download Manager", cls="text-lg font-semibold text-slate-700 dark:text-slate-200 mb-2"),
                downloads_block,
                cls="w-full xl:w-[34%] xl:sticky xl:top-6 self-start",
            ),
            cls="flex flex-col xl:flex-row gap-6",
        ),
        cls="p-6 max-w-7xl mx-auto",
    )
