"""Discovery download manager and status panel renderers."""

from urllib.parse import quote

from fasthtml.common import H3, A, Button, Div, P, Span

from studio_ui.common.polling import (
    build_every_seconds_trigger,
    get_download_manager_interval_seconds,
    get_download_status_interval_seconds,
)
from studio_ui.common.title_utils import resolve_preferred_title, truncate_title
from studio_ui.components.discovery_results import render_error_message


def render_download_status(download_id: str, doc_id: str, library: str, status_data: dict) -> Div:
    """Render download status polling fragment."""
    percent = status_data.get("percent", 0)
    status = status_data.get("status", "running")
    current = status_data.get("current", 0)
    total = status_data.get("total", 0)
    error = status_data.get("error")
    title = status_data.get("title") or doc_id

    card_cls = "bg-slate-800/60 p-6 rounded-lg border border-slate-700 shadow-sm"
    header_title_cls = "text-lg font-bold text-slate-100"
    badge_cls = "text-xs bg-indigo-900/50 text-indigo-300 px-2 py-1 rounded ml-2"
    subtext_cls = "text-sm text-slate-400 mt-1"
    percent_cls = "text-3xl font-extrabold text-indigo-400"
    progress_bg_cls = "w-full bg-slate-700 rounded-full h-2.5 mb-2"
    progress_bar_cls = "bg-indigo-500 h-2.5 rounded-full transition-all duration-500 ease-out"
    status_poll_trigger = build_every_seconds_trigger(get_download_status_interval_seconds())

    if status in {"cancelling", "pausing"}:
        header = Div(
            Div(
                H3(title, cls=header_title_cls),
                Span(library, cls=badge_cls),
                cls="flex items-center justify-between",
            ),
            P(f"{current}/{total} pagine", cls=subtext_cls),
            cls="mb-4",
        )

        percent_block = Div(
            Div(f"{percent}%", cls=percent_cls),
            P(
                "Annullamento..." if status == "cancelling" else "Messa in pausa...",
                cls="text-sm text-red-400" if status == "cancelling" else "text-sm text-amber-300",
            ),
            cls="flex items-center gap-4 mb-4",
        )

        progress_bar = Div(Div(Div(cls=progress_bar_cls, style=f"width: {percent}%"), cls=progress_bg_cls))

        body = Div(
            header,
            percent_block,
            progress_bar,
            P(
                "Annullamento in corso..." if status == "cancelling" else "Pausa in corso...",
                cls="text-xs text-slate-500 italic",
            ),
        )

        return Div(
            body,
            hx_get=f"/api/download_status/{download_id}?doc_id={doc_id}&library={library}",
            hx_trigger=status_poll_trigger,
            hx_swap="outerHTML",
            cls=card_cls,
        )

    if status in {"error", "failed"}:
        return render_error_message("Errore durante il download", str(error or status))

    if status in {"paused", "cancelled"}:
        icon = "⏸️" if status == "paused" else "🛑"
        title_text = "Download in pausa" if status == "paused" else "Download annullato"
        detail_text = (
            f"Il download di '{doc_id}' è in pausa. Puoi riprenderlo dal Download Manager."
            if status == "paused"
            else f"Il download di '{doc_id}' è stato annullato."
        )
        return Div(
            Div(
                Span(icon, cls="text-4xl mb-4 block"),
                H3(title_text, cls="text-xl font-bold text-slate-100 mb-2"),
                P(detail_text, cls="text-slate-400 mb-2"),
                P(f"Stato finale: {status.upper()}", cls="text-xs text-slate-500"),
                cls="text-center",
            ),
            cls="bg-slate-900/40 border border-slate-700 p-8 rounded-lg shadow-sm",
        )

    if percent >= 100 or status == "completed":
        encoded_lib = quote(library)
        encoded_doc = quote(doc_id)
        return Div(
            Div(
                Span("✅", cls="text-4xl mb-4 block"),
                H3("Download Completato!", cls="text-xl font-bold text-green-400 mb-2"),
                P(
                    f"Il manoscritto '{doc_id}' è stato salvato correttamente.",
                    cls="text-slate-400 mb-6",
                ),
                A(
                    Button(
                        "📖 Apri nello Studio",
                        cls=(
                            "bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg shadow-md "
                            "transition-transform hover:scale-105"
                        ),
                    ),
                    href=f"/studio?library={encoded_lib}&doc_id={encoded_doc}",
                    cls="inline-block",
                ),
                cls="text-center",
            ),
            cls=("bg-green-900/20 border border-green-800 p-8 rounded-lg shadow-sm animate-in zoom-in duration-300"),
        )

    controls = Div(
        Button(
            "⛔ Annulla",
            cls="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded-lg shadow-sm transition-all",
            hx_post=f"/api/cancel_download/{download_id}?doc_id={doc_id}&library={library}",
            hx_target="#discovery-preview",
            hx_swap="outerHTML",
        ),
        cls="mt-4 flex justify-end",
    )
    header = Div(
        Div(
            H3(title, cls=header_title_cls),
            Span(library, cls=badge_cls),
            cls="flex items-center justify-between",
        ),
        P(f"{current}/{total} pagine", cls=subtext_cls),
        cls="mb-4",
    )
    percent_block = Div(
        Div(f"{percent}%", cls=percent_cls),
        P("Scaricamento in corso...", cls="text-sm text-slate-500"),
        cls="flex items-center gap-4 mb-4",
    )
    progress_bar = Div(Div(Div(cls=progress_bar_cls, style=f"width: {percent}%"), cls=progress_bg_cls))
    body = Div(
        header,
        percent_block,
        progress_bar,
        P("Ottimizzazione immagini e salvataggio...", cls="text-xs text-slate-500 italic animate-pulse"),
    )

    return Div(
        body,
        controls,
        hx_get=f"/api/download_status/{download_id}?doc_id={doc_id}&library={library}",
        hx_trigger=status_poll_trigger,
        hx_swap="outerHTML",
        cls=card_cls,
    )


def render_download_manager(jobs: list[dict]) -> Div:
    """Render the full download manager panel."""
    active_statuses = {"queued", "running", "cancelling", "pausing", "pending", "starting"}
    should_poll = any(str(job.get("status") or "").lower() in active_statuses for job in jobs)
    manager_poll_trigger = build_every_seconds_trigger(get_download_manager_interval_seconds())
    library_jobs = [job for job in jobs if str(job.get("job_origin") or "library_download") != "studio_export_page"]
    studio_jobs = [job for job in jobs if str(job.get("job_origin") or "") == "studio_export_page"]

    sections: list = []
    if not library_jobs:
        sections.append(
            Div(
                P("Nessun download in coda.", cls="text-sm text-slate-400"),
                P(
                    "Puoi continuare a cercare mentre i download vengono eseguiti qui.",
                    cls="text-xs text-slate-500 mt-1",
                ),
                cls="bg-slate-900/40 border border-slate-700 rounded-lg p-4",
            )
        )
    else:
        sections.append(Div(*[render_download_job_card(job) for job in library_jobs], cls="space-y-3"))

    if studio_jobs:
        compact_rows = [render_studio_export_job_row(job) for job in studio_jobs]
        sections.append(
            Div(
                Div(
                    H3("Attività Immagini Studio", cls="text-sm font-semibold text-slate-100"),
                    P("Job generati dai pulsanti pagina dello Studio Export.", cls="text-[11px] text-slate-400 mt-1"),
                    cls="mb-2",
                ),
                Div(*compact_rows, cls="space-y-2"),
                cls="bg-slate-900/40 border border-slate-700 rounded-lg p-4",
            )
        )

    attrs = {"id": "download-manager-area", "cls": "space-y-2"}
    if should_poll:
        attrs.update({"hx_get": "/api/download_manager", "hx_trigger": manager_poll_trigger, "hx_swap": "outerHTML"})
    return Div(*sections, **attrs)


def render_studio_export_job_row(job: dict) -> Div:
    """Render a compact row for page-level Studio Export jobs."""
    status = str(job.get("status") or "queued").strip().lower()
    doc_id = str(job.get("doc_id") or "-")
    library = str(job.get("library") or "-")
    job_id = str(job.get("job_id") or "")
    current = int(job.get("current", 0) or 0)
    total = int(job.get("total", 0) or 0)
    title = truncate_title(resolve_preferred_title(job, fallback_doc_id=doc_id), max_len=60, suffix="[...]")

    status_map = {
        "queued": "In coda",
        "running": "In corso",
        "cancelling": "Annullamento",
        "pausing": "Pausa",
        "paused": "In pausa",
        "completed": "Completato",
        "cancelled": "Annullato",
        "error": "Errore",
    }
    status_text = status_map.get(status, status.upper() or "Sconosciuto")
    progress_text = f"{current}/{total}" if total > 0 else "job pagina"
    details = f"{title} · {library} · {status_text} · {progress_text}"

    if status in {"running", "queued", "cancelling", "pausing"}:
        action = Button(
            "⛔ Annulla",
            cls=(
                "inline-flex items-center gap-1.5 text-xs font-semibold "
                "bg-rose-700 hover:bg-rose-600 text-white px-3 py-1.5 rounded-md "
                "border border-rose-500/60 shadow-sm transition-colors"
            ),
            hx_post=f"/api/download_manager/cancel/{job_id}",
            hx_target="#download-manager-area",
            hx_swap="outerHTML",
        )
    else:
        action = Button(
            "🗑️ Rimuovi",
            cls=(
                "inline-flex items-center gap-1.5 text-xs font-semibold "
                "bg-slate-800 hover:bg-slate-700 text-slate-100 px-3 py-1.5 rounded-md "
                "border border-slate-600 shadow-sm transition-colors"
            ),
            hx_post=f"/api/download_manager/remove/{job_id}",
            hx_target="#download-manager-area",
            hx_swap="outerHTML",
        )

    return Div(
        P(details, cls="text-xs text-slate-300"),
        action,
        cls="flex items-center justify-between gap-3 rounded-lg border border-slate-700 bg-slate-950/40 px-3 py-2",
    )


def _download_job_badge(status: str, queue_position: int) -> tuple[str, str]:
    badge_map = {
        "running": "bg-indigo-800 text-indigo-100",
        "queued": "bg-slate-700 text-slate-100",
        "cancelling": "bg-amber-700 text-amber-100",
        "pausing": "bg-amber-700 text-amber-100",
        "paused": "bg-violet-800 text-violet-100",
        "completed": "bg-emerald-700 text-emerald-100",
        "cancelled": "bg-slate-700 text-slate-200",
        "error": "bg-rose-700 text-rose-100",
    }
    badge_cls = badge_map.get(status, "bg-slate-700 text-slate-100")
    badge_text = status.upper()
    if status == "queued" and queue_position > 0:
        badge_text = f"QUEUED #{queue_position}"
    return badge_cls, badge_text


def _download_job_actions(status: str, job_id: str, doc_id: str, library: str) -> tuple[list, list]:
    left_actions: list = []
    right_actions: list = []
    if status in {"running", "queued"}:
        left_actions.append(
            Button(
                "⏸️ Pausa",
                cls=(
                    "inline-flex items-center gap-1.5 text-xs font-semibold "
                    "bg-amber-700 hover:bg-amber-600 text-white px-3 py-1.5 rounded-md "
                    "border border-amber-500/60 shadow-sm transition-colors"
                ),
                hx_post=f"/api/download_manager/pause/{job_id}",
                hx_target="#download-manager-area",
                hx_swap="outerHTML",
            )
        )
    if status == "queued":
        left_actions.append(
            Button(
                "⬆️ Priorità",
                cls=(
                    "inline-flex items-center gap-1.5 text-xs font-semibold "
                    "bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded-md "
                    "border border-slate-500/60 shadow-sm transition-colors"
                ),
                hx_post=f"/api/download_manager/prioritize/{job_id}",
                hx_target="#download-manager-area",
                hx_swap="outerHTML",
            )
        )
    if status == "paused":
        left_actions.append(
            Button(
                "▶️ Riprendi",
                cls=(
                    "inline-flex items-center gap-1.5 text-xs font-semibold "
                    "bg-emerald-700 hover:bg-emerald-600 text-white px-3 py-1.5 rounded-md "
                    "border border-emerald-500/60 shadow-sm transition-colors"
                ),
                hx_post=f"/api/download_manager/resume/{job_id}",
                hx_target="#download-manager-area",
                hx_swap="outerHTML",
            )
        )
    if status in {"error", "cancelled"}:
        left_actions.append(
            Button(
                "🔁 Retry",
                cls=(
                    "inline-flex items-center gap-1.5 text-xs font-semibold "
                    "bg-emerald-700 hover:bg-emerald-600 text-white px-3 py-1.5 rounded-md "
                    "border border-emerald-500/60 shadow-sm transition-colors"
                ),
                hx_post=f"/api/download_manager/retry/{job_id}",
                hx_target="#download-manager-area",
                hx_swap="outerHTML",
            )
        )
    if status == "completed":
        left_actions.append(
            A(
                Button(
                    "📖 Vai allo Studio",
                    cls=(
                        "inline-flex items-center gap-1.5 text-xs font-semibold "
                        "bg-indigo-700 hover:bg-indigo-600 text-white px-3 py-1.5 rounded-md "
                        "border border-indigo-500/60 shadow-sm transition-colors"
                    ),
                ),
                href=f"/studio?doc_id={quote(doc_id)}&library={quote(library)}",
                cls="inline-block",
            )
        )

    if status in {"running", "queued", "cancelling", "pausing"}:
        right_actions.append(
            Button(
                "⛔ Annulla",
                cls=(
                    "inline-flex items-center gap-1.5 text-xs font-semibold "
                    "bg-rose-700 hover:bg-rose-600 text-white px-3 py-1.5 rounded-md "
                    "border border-rose-500/60 shadow-sm transition-colors"
                ),
                hx_post=f"/api/download_manager/cancel/{job_id}",
                hx_target="#download-manager-area",
                hx_swap="outerHTML",
            )
        )
    if status in {"error", "cancelled", "completed", "paused"}:
        right_actions.append(
            Button(
                "🗑️ Rimuovi",
                cls=(
                    "inline-flex items-center gap-1.5 text-xs font-semibold "
                    "bg-slate-800 hover:bg-slate-700 text-slate-100 px-3 py-1.5 rounded-md "
                    "border border-slate-600 shadow-sm transition-colors"
                ),
                hx_post=f"/api/download_manager/remove/{job_id}",
                hx_target="#download-manager-area",
                hx_swap="outerHTML",
            )
        )
    return left_actions, right_actions


def _download_job_progress(status: str, current: int, total: int, percent: int, error: str) -> Div:
    counts_line = P(f"{current}/{total} pagine", cls="text-[11px] text-slate-400 mt-1")
    progress = Div(
        Div(
            Div(cls="h-2 rounded bg-indigo-500", style=f"width: {percent}%"),
            cls="w-full bg-slate-700 rounded h-2",
        ),
        P(f"{current}/{total} ({percent}%)", cls="text-[11px] text-slate-400 mt-1") if total > 0 else counts_line,
        cls="mt-2",
    )
    if status == "queued":
        return Div(counts_line, P("In attesa di uno slot libero...", cls="text-[11px] text-slate-400 mt-2"), cls="mt-1")
    if status == "cancelling":
        return Div(
            counts_line,
            P("Richiesta di arresto in corso...", cls="text-[11px] text-amber-300 mt-2"),
            cls="mt-1",
        )
    if status == "pausing":
        return Div(counts_line, P("Messa in pausa in corso...", cls="text-[11px] text-amber-300 mt-2"), cls="mt-1")
    if status == "paused":
        return Div(counts_line, P("Download in pausa.", cls="text-[11px] text-violet-300 mt-2"), cls="mt-1")
    if status == "cancelled":
        return Div(counts_line, P("Download annullato dall'utente.", cls="text-[11px] text-slate-300 mt-2"), cls="mt-1")
    if status == "error" and error:
        return Div(counts_line, P(error, cls="text-[11px] text-rose-300 mt-2"), cls="mt-1")
    return progress


def render_download_job_card(job: dict) -> Div:
    """Render a single card inside the Download Manager list."""
    status = str(job.get("status") or "queued")
    doc_id = str(job.get("doc_id") or "-")
    library = str(job.get("library") or "-")
    job_id = str(job.get("job_id") or "")
    current = int(job.get("current", 0) or 0)
    total = int(job.get("total", 0) or 0)
    queue_position = int(job.get("queue_position", 0) or 0)
    error = str(job.get("error") or "")
    title = truncate_title(resolve_preferred_title(job, fallback_doc_id=doc_id), max_len=70, suffix="[...]")
    percent = int((current / total * 100) if total > 0 else 0)

    badge_cls, badge_text = _download_job_badge(status, queue_position)
    left_actions, right_actions = _download_job_actions(status, job_id, doc_id, library)
    progress = _download_job_progress(status, current, total, percent, error)

    return Div(
        Div(
            H3(title, cls="text-sm font-bold text-slate-100 truncate"),
            Span(badge_text, cls=f"text-[10px] px-2 py-1 rounded {badge_cls}"),
            cls="flex items-start justify-between gap-2",
        ),
        P(library, cls="text-xs text-slate-400"),
        progress,
        Div(
            Div(*left_actions, cls="flex flex-wrap gap-2"),
            Div(*right_actions, cls="flex flex-wrap gap-2 ml-auto"),
            cls="mt-2 flex items-start gap-2",
        ),
        cls="bg-slate-900/50 border border-slate-700 rounded-lg p-3",
    )
