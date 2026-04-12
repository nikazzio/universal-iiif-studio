"""PDF inventory panel and byte-size formatting."""

from __future__ import annotations

from urllib.parse import quote

from fasthtml.common import A, Div, Span


def _bytes_label(size_bytes: int) -> str:
    size = int(size_bytes or 0)
    if size <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    current = float(size)
    for unit in units:
        if current < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(current)} {unit}"
            return f"{current:.1f} {unit}"
        current /= 1024.0
    return f"{size} B"


def render_pdf_inventory_panel(pdf_files: list[dict], *, doc_id: str, library: str, polling: bool = True) -> Div:
    """Render item-level PDF inventory for one manuscript."""
    encoded_doc = quote(doc_id, safe="")
    encoded_lib = quote(library, safe="")
    attrs = {}
    if polling:
        attrs = {
            "hx_get": f"/api/studio/export/pdf_list?doc_id={encoded_doc}&library={encoded_lib}",
            "hx_trigger": "load, every 12s",
            "hx_swap": "outerHTML",
        }

    rows = []
    for item in pdf_files:
        href = str(item.get("download_url") or "#")
        name = str(item.get("name") or "-")
        kind = str(item.get("kind") or "other")
        size_text = _bytes_label(int(item.get("size_bytes") or 0))

        rows.append(
            Div(
                Div(
                    Span(name, cls="text-xs font-mono text-slate-700 dark:text-slate-200"),
                    Span(kind, cls="text-[11px] text-slate-500 dark:text-slate-400"),
                    cls="grid gap-0.5 min-w-0",
                ),
                Div(
                    Span(size_text, cls="text-xs text-slate-500 dark:text-slate-400"),
                    A(
                        "Apri",
                        href=href,
                        target="_blank",
                        cls="app-btn app-btn-neutral",
                    ),
                    cls="flex items-center gap-2",
                ),
                cls=(
                    "flex items-center justify-between gap-2 border border-slate-200 dark:border-slate-700 "
                    "rounded-xl p-2.5 bg-white dark:bg-slate-900"
                ),
            )
        )

    if not rows:
        rows = [
            Div(
                "Nessun PDF presente nella cartella item/pdf.",
                cls=(
                    "text-xs text-slate-500 dark:text-slate-400 p-2.5 border border-dashed rounded-xl "
                    "dark:border-slate-700"
                ),
            )
        ]

    return Div(
        Div(*rows, cls="space-y-2"),
        id="studio-export-pdf-list",
        **attrs,
    )
