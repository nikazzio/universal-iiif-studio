from __future__ import annotations

from fasthtml.common import H3, Div, P

from studio_ui.components.settings.controls import setting_number


def _build_discovery_pane(cm, s):
    """Discovery search settings pane."""
    _ = cm
    discovery = s.get("discovery", {})
    if not isinstance(discovery, dict):
        discovery = {}

    return Div(
        Div(
            H3("Discovery", cls="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2"),
            P(
                "Impostazioni per la ricerca nelle biblioteche digitali.",
                cls="text-xs text-slate-500 dark:text-slate-400 mb-3",
            ),
        ),
        Div(
            setting_number(
                "Risultati per provider",
                "settings.discovery.max_results_per_provider",
                discovery.get("max_results_per_provider", 20),
                min_val=1,
                max_val=50,
                step_val=1,
                help_text=(
                    "Numero massimo di risultati restituiti da ciascun provider per ogni ricerca. "
                    "Per i provider con paginazione (Archive.org, Harvard, LOC, Gallica) "
                    "è possibile caricare ulteriori risultati con il pulsante 'Carica altri'."
                ),
            ),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        cls="p-4",
        data_pane="discovery",
    )
