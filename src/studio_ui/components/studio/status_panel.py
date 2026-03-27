"""Professional status panel component for Studio interface."""

from __future__ import annotations

from fasthtml.common import Div, Span


def status_badge(label: str, value: str, variant: str = "default") -> Div:
    """Create a status badge with color-coded styling.

    Args:
        label: Badge label text
        value: Badge value text
        variant: Color variant (default, success, warning, danger, info, neutral)
    """
    variant_styles = {
        "default": {
            "bg": "bg-slate-100 dark:bg-slate-800",
            "border": "border-slate-300 dark:border-slate-600",
            "label": "text-slate-600 dark:text-slate-400",
            "value": "text-slate-900 dark:text-slate-100",
        },
        "success": {
            "bg": "bg-emerald-50 dark:bg-emerald-950/30",
            "border": "border-emerald-300 dark:border-emerald-700",
            "label": "text-emerald-700 dark:text-emerald-400",
            "value": "text-emerald-900 dark:text-emerald-200",
        },
        "warning": {
            "bg": "bg-amber-50 dark:bg-amber-950/30",
            "border": "border-amber-300 dark:border-amber-700",
            "label": "text-amber-700 dark:text-amber-400",
            "value": "text-amber-900 dark:text-amber-200",
        },
        "danger": {
            "bg": "bg-red-50 dark:bg-red-950/30",
            "border": "border-red-300 dark:border-red-700",
            "label": "text-red-700 dark:text-red-400",
            "value": "text-red-900 dark:text-red-200",
        },
        "info": {
            "bg": "bg-blue-50 dark:bg-blue-950/30",
            "border": "border-blue-300 dark:border-blue-700",
            "label": "text-blue-700 dark:text-blue-400",
            "value": "text-blue-900 dark:text-blue-200",
        },
        "neutral": {
            "bg": "bg-gray-100 dark:bg-gray-800/50",
            "border": "border-gray-300 dark:border-gray-600",
            "label": "text-gray-600 dark:text-gray-400",
            "value": "text-gray-800 dark:text-gray-200",
        },
    }

    styles = variant_styles.get(variant, variant_styles["default"])

    return Div(
        Span(
            label.upper(),
            cls=f"text-[10px] font-bold tracking-wider {styles['label']}",
        ),
        Span(
            value,
            cls=f"font-mono text-sm font-semibold tracking-tight {styles['value']}",
        ),
        cls=(f"flex flex-col gap-0.5 px-3 py-2 rounded border {styles['bg']} {styles['border']}"),
    )


def get_status_variant(key: str, value: str) -> str:
    """Determine color variant based on status key and value."""
    if key == "read_source":
        return "warning" if value == "remote" else "success"
    elif key == "state":
        return {
            "completed": "success",
            "downloading": "info",
            "paused": "warning",
            "failed": "danger",
            "pending": "neutral",
        }.get(value, "default")
    elif key == "pdf_local":
        return "success" if value == "yes" else "neutral"
    elif key == "pdf_source":
        return "success" if value == "native" else "info" if value == "images" else "neutral"
    return "default"


def technical_status_panel(
    doc_id: str,
    library: str,
    state: str,
    read_source: str,
    scans_local: str,
    staging_pages: str,
    pdf_source: str,
    pdf_local: str,
) -> Div:
    """Render professional technical status panel with badges.

    Args:
        doc_id: Document identifier
        library: Library name
        state: Asset state (completed, downloading, paused, etc.)
        read_source: Read source mode (local or remote)
        scans_local: Local scans count (e.g., "42/425")
        staging_pages: Staging pages count
        pdf_source: PDF source (native, images, unknown)
        pdf_local: PDF local availability (yes, no)
    """
    status_items = [
        ("read_source", read_source),
        ("state", state),
        ("scans_local", scans_local),
        ("staging_pages", staging_pages),
    ]

    secondary_items = [
        ("pdf_source", pdf_source),
        ("pdf_local", pdf_local),
        ("library", library),
        ("id", doc_id),
    ]

    return Div(
        # Primary Status Row (prominent)
        Div(
            *[status_badge(key, value, get_status_variant(key, value)) for key, value in status_items],
            cls="grid grid-cols-2 sm:grid-cols-4 gap-2",
        ),
        # Secondary Status Row (compact)
        Div(
            *[
                Div(
                    Span(
                        f"{key.upper()}:",
                        cls="text-[9px] font-bold text-slate-600 dark:text-slate-400 tracking-wider",
                    ),
                    Span(
                        value if len(value) <= 30 else f"{value[:27]}...",
                        cls="font-mono text-[10px] text-slate-700 dark:text-slate-300",
                        title=value if len(value) > 30 else None,
                    ),
                    cls="flex items-baseline gap-1.5",
                )
                for key, value in secondary_items
            ],
            cls="grid grid-cols-2 sm:grid-cols-4 gap-x-3 gap-y-1 px-2",
        ),
        cls=(
            "flex flex-col gap-3 rounded-lg border-2 "
            "border-slate-200 dark:border-slate-700 "
            "bg-slate-50 dark:bg-slate-900/50 "
            "p-3 shadow-sm"
        ),
    )
