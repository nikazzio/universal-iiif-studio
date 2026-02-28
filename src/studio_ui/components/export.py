"""UI components for Export monitor and jobs."""

from __future__ import annotations

from fasthtml.common import H2, H3, A, Button, Div, P, Span

_STATUS_CLASSES = {
    "queued": "bg-slate-100 text-slate-700",
    "running": "bg-amber-100 text-amber-800",
    "completed": "bg-emerald-100 text-emerald-700",
    "error": "bg-rose-100 text-rose-700",
    "cancelled": "bg-slate-200 text-slate-600",
}


def _status_chip(status: str):
    value = (status or "queued").strip().lower()
    cls = _STATUS_CLASSES.get(value, _STATUS_CLASSES["queued"])
    return Span(value.upper(), cls=f"{cls} text-[10px] font-bold px-2 py-1 rounded")


def render_export_jobs_panel(
    jobs: list[dict],
    *,
    polling: bool = True,
    hx_url: str = "/api/export/jobs",
    panel_id: str = "export-jobs-panel",
) -> Div:
    """Render export jobs list and controls."""
    attrs = {}
    if polling:
        attrs = {
            "hx_get": hx_url,
            "hx_trigger": "load, every 4s",
            "hx_swap": "outerHTML",
        }

    cards = []
    for job in jobs:
        job_id = str(job.get("job_id") or "")
        status = str(job.get("status") or "queued")
        current = int(job.get("current_step") or 0)
        total = int(job.get("total_steps") or 0)
        fmt = str(job.get("export_format") or "-")
        destination = str(job.get("destination") or "local_filesystem")
        output_path = str(job.get("output_path") or "")
        error_text = str(job.get("error_message") or "")

        progress_text = f"{current}/{total}" if total > 0 else "0/0"
        can_cancel = status in {"queued", "running"}
        can_download = status == "completed" and bool(output_path)

        actions = []
        if can_download:
            actions.append(
                A(
                    "Scarica",
                    href=f"/api/export/download/{job_id}",
                    cls="px-3 py-1 rounded bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-semibold",
                )
            )
        if can_cancel:
            actions.append(
                Button(
                    "Annulla",
                    hx_post=f"/api/export/cancel/{job_id}",
                    hx_target=f"#{panel_id}",
                    hx_swap="outerHTML",
                    cls="px-3 py-1 rounded bg-rose-700 hover:bg-rose-600 text-white text-xs font-semibold",
                )
            )
        else:
            actions.append(
                Button(
                    "Rimuovi",
                    hx_post=f"/api/export/remove/{job_id}",
                    hx_target=f"#{panel_id}",
                    hx_swap="outerHTML",
                    cls="px-3 py-1 rounded bg-slate-700 hover:bg-slate-600 text-white text-xs font-semibold",
                )
            )

        cards.append(
            Div(
                Div(
                    Div(
                        Span(job_id, cls="font-mono text-xs text-slate-600"),
                        _status_chip(status),
                        cls="flex items-center gap-2",
                    ),
                    Div(
                        Span(f"Formato: {fmt}", cls="text-xs text-slate-600"),
                        Span(f"Destinazione: {destination}", cls="text-xs text-slate-500"),
                        cls="flex flex-wrap gap-3",
                    ),
                    cls="flex flex-col gap-2",
                ),
                Div(
                    Span(f"Progress: {progress_text}", cls="text-xs text-slate-600"),
                    Span(error_text, cls="text-xs text-rose-700") if error_text else "",
                    cls="flex flex-col gap-1",
                ),
                Div(*actions, cls="flex items-center gap-2"),
                cls="border border-slate-200 rounded-lg p-3 bg-white shadow-sm space-y-3",
            )
        )

    if not cards:
        cards = [Div("Nessun job export presente.", cls="text-sm text-slate-500 p-3 border border-dashed rounded")]

    return Div(
        Div(
            H3("Job Export", cls="text-lg font-semibold text-slate-800"),
            Span("Aggiornamento automatico ogni 4s", cls="text-xs text-slate-500"),
            cls="flex items-baseline justify-between mb-3",
        ),
        Div(*cards, cls="space-y-2"),
        id=panel_id,
        **attrs,
    )


def render_export_page(jobs: list[dict], capabilities: dict[str, list[dict]]) -> Div:
    """Render monitor-only Export page."""
    formats = capabilities.get("formats") or []
    destinations = capabilities.get("destinations") or []

    format_rows = []
    for item in formats:
        label = str(item.get("label") or item.get("key") or "-")
        available = bool(item.get("available"))
        status_text = "Disponibile" if available else "In arrivo"
        cls = "text-emerald-700" if available else "text-amber-700"
        format_rows.append(Div(Span(label, cls="text-sm text-slate-700"), Span(status_text, cls=f"text-xs {cls}"), cls="flex justify-between"))

    destination_rows = []
    for item in destinations:
        label = str(item.get("label") or item.get("key") or "-")
        available = bool(item.get("available"))
        status_text = "Disponibile" if available else "In arrivo"
        cls = "text-emerald-700" if available else "text-amber-700"
        destination_rows.append(
            Div(Span(label, cls="text-sm text-slate-700"), Span(status_text, cls=f"text-xs {cls}"), cls="flex justify-between")
        )

    return Div(
        H2("Export", cls="text-2xl font-bold text-slate-900 mb-1"),
        P(
            "Monitor coda/storico export. L'avvio export avviene nello Studio, a livello singolo item.",
            cls="text-sm text-slate-600 mb-6",
        ),
        Div(
            Div(
                H3("Capability", cls="text-base font-semibold text-slate-800 mb-2"),
                Div(Span("Formati", cls="text-xs font-semibold text-slate-500 uppercase"), *format_rows, cls="space-y-2"),
                Div(
                    Span("Destinazioni", cls="text-xs font-semibold text-slate-500 uppercase"),
                    *destination_rows,
                    cls="space-y-2 mt-4",
                ),
                cls="bg-slate-50 border border-slate-200 rounded-xl p-4",
            ),
            Div(render_export_jobs_panel(jobs, polling=True), cls="space-y-4"),
            cls="grid grid-cols-1 lg:grid-cols-2 gap-6",
        ),
    )
