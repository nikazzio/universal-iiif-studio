"""UI components for Export monitor and jobs."""

from __future__ import annotations

from fasthtml.common import H2, H3, A, Button, Div, P, Span

_STATUS_CLASSES = {
    "queued": "app-chip app-chip-primary",
    "running": "app-chip app-chip-warning",
    "completed": "app-chip app-chip-success",
    "error": "app-chip app-chip-danger",
    "cancelled": "app-chip app-chip-neutral",
}
_STATUS_LABELS = {
    "queued": "In coda",
    "running": "In corso",
    "completed": "Completato",
    "error": "Errore",
    "cancelled": "Annullato",
}


def _status_chip(status: str):
    value = (status or "queued").strip().lower()
    cls = _STATUS_CLASSES.get(value, _STATUS_CLASSES["queued"])
    label = _STATUS_LABELS.get(value, value.title())
    return Span(label, cls=f"{cls} text-[11px] tracking-wide")


def _availability_chip(available: bool):
    if available:
        return Span("Disponibile", cls="app-chip app-chip-success text-[11px] tracking-wide")
    return Span("In arrivo", cls="app-chip app-chip-warning text-[11px] tracking-wide")


def render_export_jobs_panel(
    jobs: list[dict],
    *,
    polling: bool = True,
    hx_url: str = "/api/export/jobs",
    panel_id: str = "export-jobs-panel",
    has_active_jobs: bool | None = None,
) -> Div:
    """Render export jobs list and controls."""
    if has_active_jobs is None:
        has_active_jobs = any(str(job.get("status") or "").lower() in {"queued", "running"} for job in jobs)

    attrs = {}
    if polling and has_active_jobs:
        attrs = {
            "hx_get": hx_url,
            "hx_trigger": "load, every 4s",
            "hx_swap": "outerHTML",
        }

    cards = []
    for job in jobs:
        job_id = str(job.get("job_id") or "")
        status = str(job.get("status") or "queued").strip().lower()
        current = int(job.get("current_step") or 0)
        total = int(job.get("total_steps") or 0)
        fmt = str(job.get("export_format") or "-")
        destination = str(job.get("destination") or "local_filesystem")
        output_path = str(job.get("output_path") or "")
        error_text = str(job.get("error_message") or "")

        progress_text = f"{current}/{total}" if total > 0 else "0/0"
        can_cancel = status in {"queued", "running"}
        can_download = status == "completed" and bool(output_path)
        progress_tone = "app-chip-primary"
        if status == "completed":
            progress_tone = "app-chip-success"
        elif status == "error":
            progress_tone = "app-chip-danger"
        elif status == "cancelled":
            progress_tone = "app-chip-neutral"

        actions = []
        if can_download:
            actions.append(
                A(
                    "Scarica",
                    href=f"/api/export/download/{job_id}",
                    cls="app-btn app-btn-accent",
                )
            )
        if can_cancel:
            actions.append(
                Button(
                    "Annulla",
                    hx_post=f"/api/export/cancel/{job_id}",
                    hx_target=f"#{panel_id}",
                    hx_swap="outerHTML",
                    cls="app-btn app-btn-danger",
                )
            )
        else:
            actions.append(
                Button(
                    "Rimuovi",
                    hx_post=f"/api/export/remove/{job_id}",
                    hx_target=f"#{panel_id}",
                    hx_swap="outerHTML",
                    cls="app-btn app-btn-neutral",
                )
            )

        cards.append(
            Div(
                Div(
                    Div(
                        Span(job_id, cls="font-mono text-[11px] text-slate-600 dark:text-slate-300 break-all"),
                        _status_chip(status),
                        Span(f"Progress {progress_text}", cls=f"app-chip {progress_tone} text-[11px] tracking-wide"),
                        cls="flex flex-wrap items-center gap-2",
                    ),
                    Div(
                        Div(
                            Span(
                                "Formato", cls="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400"
                            ),
                            Span(fmt, cls="text-sm font-medium text-slate-800 dark:text-slate-100"),
                            cls="flex flex-col",
                        ),
                        Div(
                            Span(
                                "Destinazione",
                                cls="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400",
                            ),
                            Span(destination, cls="text-sm font-medium text-slate-800 dark:text-slate-100"),
                            cls="flex flex-col",
                        ),
                        cls="grid grid-cols-1 sm:grid-cols-2 gap-3",
                    ),
                    cls="flex flex-col gap-2",
                ),
                (
                    Div(
                        Span("Output", cls="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400"),
                        Span(output_path, cls="text-xs text-slate-600 dark:text-slate-300 break-all"),
                        cls="space-y-1",
                    )
                    if output_path
                    else ""
                ),
                (
                    Div(
                        Span(error_text, cls="text-xs text-rose-700 dark:text-rose-300"),
                        cls=(
                            "rounded-lg border border-rose-200 dark:border-rose-700/60 "
                            "bg-rose-50 dark:bg-rose-950/30 p-2"
                        ),
                    )
                    if error_text
                    else ""
                ),
                Div(*actions, cls="flex items-center gap-2"),
                cls=(
                    "border border-slate-200 dark:border-slate-700 rounded-2xl p-4 "
                    "bg-white dark:bg-slate-900/60 shadow-sm space-y-3"
                ),
            )
        )

    if not cards:
        cards = [
            Div(
                "Nessun job export presente.",
                cls=(
                    "text-sm text-slate-600 dark:text-slate-300 p-4 border border-dashed "
                    "border-slate-300 dark:border-slate-700 rounded-2xl bg-white/70 dark:bg-slate-900/30"
                ),
            )
        ]

    header_right = Div(
        Span(
            "Aggiornamento automatico ogni 4s" if has_active_jobs else "Aggiornamento automatico in pausa",
            cls="app-chip app-chip-neutral text-[11px] tracking-wide",
        ),
        Button(
            "Aggiorna ora",
            type="button",
            hx_get=hx_url,
            hx_target=f"#{panel_id}",
            hx_swap="outerHTML",
            cls="app-btn app-btn-primary",
        ),
        cls="flex items-center gap-2",
    )

    return Div(
        Div(
            Div(
                H3("Job Export", cls="text-lg font-semibold text-slate-900 dark:text-slate-100 leading-tight"),
                P(
                    f"{len(jobs)} job registrati",
                    cls="text-xs text-slate-500 dark:text-slate-400 mt-0.5",
                ),
                cls="min-w-0",
            ),
            header_right,
            cls="flex flex-wrap items-start justify-between gap-3 mb-3",
        ),
        (
            Div(
                "Nessun job attivo: polling in pausa.",
                cls="text-xs text-slate-500 dark:text-slate-400 mb-2",
            )
            if not has_active_jobs
            else ""
        ),
        Div(*cards, cls="space-y-2"),
        cls=("rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50/80 dark:bg-slate-900/35 p-4"),
        id=panel_id,
        **attrs,
    )


def render_export_page(jobs: list[dict], capabilities: dict[str, list[dict]]) -> Div:
    """Render monitor-only Export page."""
    formats = capabilities.get("formats") or []
    destinations = capabilities.get("destinations") or []
    has_active_jobs = any(str(job.get("status") or "").lower() in {"queued", "running"} for job in jobs)
    active_jobs = sum(1 for job in jobs if str(job.get("status") or "").lower() in {"queued", "running"})

    format_rows = []
    for item in formats:
        label = str(item.get("label") or item.get("key") or "-")
        available = bool(item.get("available"))
        format_rows.append(
            Div(
                Span(label, cls="text-sm text-slate-700 dark:text-slate-200"),
                _availability_chip(available),
                cls=(
                    "flex justify-between items-center gap-2 py-2 px-3 rounded-xl "
                    "border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/45"
                ),
            )
        )

    destination_rows = []
    for item in destinations:
        label = str(item.get("label") or item.get("key") or "-")
        available = bool(item.get("available"))
        destination_rows.append(
            Div(
                Span(label, cls="text-sm text-slate-700 dark:text-slate-200"),
                _availability_chip(available),
                cls=(
                    "flex justify-between items-center gap-2 py-2 px-3 rounded-xl "
                    "border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/45"
                ),
            )
        )

    return Div(
        Div(
            Div(
                H2("Export", cls="text-2xl font-bold text-slate-900 dark:text-slate-100"),
                P(
                    "Monitor della coda e dello storico esportazioni, "
                    "con avvio dei job dal tab Studio del singolo item.",
                    cls="text-sm text-slate-600 dark:text-slate-300",
                ),
                cls="space-y-1",
            ),
            Span(
                f"Job attivi: {active_jobs}",
                cls=("app-chip app-chip-primary text-xs" if active_jobs > 0 else "app-chip app-chip-neutral text-xs"),
            ),
            cls="flex flex-wrap items-start justify-between gap-3 mb-6",
        ),
        Div(
            Div(
                H3("Capacità Export", cls="text-base font-semibold text-slate-900 dark:text-slate-100 mb-2"),
                Div(
                    Span("Formati", cls="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase"),
                    *format_rows,
                    cls="space-y-2",
                ),
                Div(
                    Span("Destinazioni", cls="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase"),
                    *destination_rows,
                    cls="space-y-2 mt-4",
                ),
                cls=(
                    "bg-slate-50/85 dark:bg-slate-900/35 border border-slate-200 dark:border-slate-700 rounded-2xl p-4"
                ),
            ),
            Div(render_export_jobs_panel(jobs, polling=True, has_active_jobs=has_active_jobs), cls="space-y-4"),
            cls="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start",
        ),
        cls="p-6 max-w-7xl mx-auto",
        id="export-page",
    )
