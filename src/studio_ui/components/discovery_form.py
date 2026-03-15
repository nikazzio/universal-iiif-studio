"""Discovery search form renderer."""

import json

from fasthtml.common import H3, A, Button, Div, Form, Input, Label, Option, P, Script, Select

from studio_ui.library_options import library_options
from universal_iiif_core.providers import iter_providers


def discovery_form() -> Div:
    """Form component for discovery searches."""
    libraries = library_options()
    providers = [provider for provider in iter_providers(ui_only=True) if provider.key != "Unknown"]
    provider_filter_map = {
        provider.key: [provider_filter.key for provider_filter in provider.filters]
        for provider in providers
    }
    provider_placeholder_map = {provider.key: provider.placeholder for provider in providers}
    provider_helper_map = {provider.key: provider.metadata.get("helper_text", "") for provider in providers}
    provider_search_url_map = {provider.key: provider.metadata.get("browser_search_url", "") for provider in providers}
    provider_search_label_map = {
        provider.key: provider.metadata.get("browser_search_label", "Apri ricerca nel browser")
        for provider in providers
    }
    rendered_filters = []
    seen_filters: set[str] = set()
    for provider in providers:
        for provider_filter in provider.filters:
            if provider_filter.key in seen_filters:
                continue
            seen_filters.add(provider_filter.key)
            rendered_filters.append(
                Div(
                    Label(provider_filter.label, for_=provider_filter.key, cls="app-label mb-1"),
                    Select(
                        *[
                            Option(
                                option.label,
                                value=option.value,
                                selected=option.value == provider_filter.options[0].value,
                            )
                            for option in provider_filter.options
                        ],
                        id=provider_filter.key,
                        name=provider_filter.key,
                        cls="app-field",
                    ),
                    data_filter_key=provider_filter.key,
                    cls="col-span-12 md:col-span-6 lg:col-span-4",
                )
            )

    return Div(
        H3("Ricerca", cls="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-1"),
        P(
            "Inserisci testo libero, segnatura, ID o URL. I filtri sono opzionali.",
            cls="text-sm text-slate-600 dark:text-slate-300 mb-4",
        ),
        Form(
            Div(
                Div(
                    Label(
                        "Cerca",
                        for_="shelf-input",
                        cls="app-label mb-1",
                    ),
                    Input(
                        type="text",
                        id="shelf-input",
                        name="shelfmark",
                        placeholder=provider_placeholder_map.get("Vaticana", "Inserisci ID, URL o testo libero"),
                        cls="app-field text-base py-3 px-3.5",
                    ),
                    cls="col-span-12 lg:col-span-8",
                ),
                Div(
                    Button(
                        "Ricerca documento",
                        type="submit",
                        cls="w-full app-btn app-btn-accent font-semibold py-3",
                    ),
                    cls="col-span-12 lg:col-span-4 lg:self-end",
                ),
                Div(
                    P(
                        provider_helper_map.get("Vaticana", ""),
                        id="provider-helper-text",
                        cls="text-xs text-slate-500 dark:text-slate-400 min-h-[1.25rem]",
                    ),
                    A(
                        provider_search_label_map.get("Vaticana", "Apri ricerca nel browser"),
                        id="provider-search-link",
                        href="#",
                        target="_blank",
                        rel="noopener noreferrer",
                        cls="hidden text-xs text-sky-700 dark:text-sky-300 underline inline-block",
                    ),
                    cls="col-span-12 space-y-1",
                ),
                Div(
                    Label(
                        "Biblioteca",
                        for_="lib-select",
                        cls="app-label mb-1",
                    ),
                    Select(
                        *[Option(label, value=value) for label, value in libraries],
                        id="lib-select",
                        name="library",
                        cls="app-field",
                    ),
                    cls="col-span-12 md:col-span-6 lg:col-span-4",
                ),
                *rendered_filters,
                cls="grid grid-cols-12 gap-4",
            ),
            hx_post="/api/resolve_manifest",
            hx_target="#discovery-preview",
            hx_indicator="#resolve-spinner",
        ),
        Script(
            f"""
            (function () {{
                const lib = document.getElementById('lib-select');
                const shelfInput = document.getElementById('shelf-input');
                const helperText = document.getElementById('provider-helper-text');
                const searchLink = document.getElementById('provider-search-link');
                const providerFilters = {json.dumps(provider_filter_map, ensure_ascii=True)};
                const providerPlaceholders = {json.dumps(provider_placeholder_map, ensure_ascii=True)};
                const providerHelpers = {json.dumps(provider_helper_map, ensure_ascii=True)};
                const providerSearchUrls = {json.dumps(provider_search_url_map, ensure_ascii=True)};
                const providerSearchLabels = {json.dumps(provider_search_label_map, ensure_ascii=True)};
                const filterNodes = Array.from(document.querySelectorAll('[data-filter-key],[data_filter_key]'));
                if (!lib) return;
                const sync = () => {{
                    const activeFilters = new Set(providerFilters[lib.value || ''] || []);
                    const placeholder = providerPlaceholders[lib.value || ''] || 'Inserisci ID, URL o testo libero';
                    const helper = providerHelpers[lib.value || ''] || '';
                    const searchUrlTemplate = providerSearchUrls[lib.value || ''] || '';
                    const searchLabel = providerSearchLabels[lib.value || ''] || 'Apri ricerca nel browser';
                    const query = encodeURIComponent((shelfInput && shelfInput.value) || '');
                    filterNodes.forEach((node) => {{
                        const filterKey = node.getAttribute('data-filter-key') || node.getAttribute('data_filter_key');
                        const select = node.querySelector('select');
                        const visible = activeFilters.has(filterKey);
                        node.style.display = visible ? '' : 'none';
                        if (select) {{
                            select.disabled = !visible;
                            if (!visible && select.options.length > 0) {{
                                select.value = select.options[0].value;
                            }}
                        }}
                    }});
                    if (shelfInput) {{
                        shelfInput.placeholder = placeholder;
                    }}
                    if (helperText) {{
                        helperText.textContent = helper;
                    }}
                    if (searchLink) {{
                        if (searchUrlTemplate) {{
                            searchLink.classList.remove('hidden');
                            searchLink.textContent = searchLabel;
                            searchLink.href = searchUrlTemplate.replace('{{query}}', query);
                        }} else {{
                            searchLink.classList.add('hidden');
                            searchLink.href = '#';
                        }}
                    }}
                }};
                lib.addEventListener('change', sync);
                if (shelfInput) {{
                    shelfInput.addEventListener('input', sync);
                }}
                sync();
            }})();
            """
        ),
        Div(
            Div(
                cls=(
                    "inline-block w-8 h-8 border-[3px] border-[rgba(var(--app-accent-rgb),0.55)] "
                    "border-t-transparent rounded-full animate-spin"
                )
            ),
            id="resolve-spinner",
            cls="htmx-indicator flex justify-center mt-6",
        ),
        cls=(
            "rounded-xl border border-slate-200/80 dark:border-slate-700 bg-white/90 dark:bg-slate-900/50 p-5 shadow-sm"
        ),
    )
