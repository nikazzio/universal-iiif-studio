import json

from fasthtml.common import H2, Button, Div, Form, NotStr

from studio_ui.theme import THEME_PRESETS, parse_hex_rgb, readable_ink, resolve_ui_theme
from universal_iiif_core.config_manager import get_config_manager

from .controls import raw_file_script, raw_init
from .panes import (
    _build_general_pane,
    _build_images_pane,
    _build_pdf_pane,
    _build_processing_pane,
    _build_system_pane,
    _build_thumbnails_pane,
    _build_viewer_pane,
)


def _theme_preview_script(default_primary: str, default_accent: str) -> str:
    presets_json = json.dumps(THEME_PRESETS, separators=(",", ":"))
    baseline_json = json.dumps({"primary": default_primary, "accent": default_accent}, separators=(",", ":"))
    return (
        "<script>(function(){"
        f"const PRESETS={presets_json};"
        f"const BASELINE={baseline_json};"
        "function requestPath(evt){"
        "try{return (evt&&evt.detail&&evt.detail.pathInfo&&evt.detail.pathInfo.requestPath)||'';}catch(_){return '';}"
        "}"
        "function normalizeHex(value, fallback){"
        "var raw=String(value||'').trim().replace('#','');"
        "if(raw.length===3) raw=raw[0]+raw[0]+raw[1]+raw[1]+raw[2]+raw[2];"
        "if(!/^[0-9a-fA-F]{6}$/.test(raw)) return String(fallback||'#4F46E5').toUpperCase();"
        "return ('#'+raw).toUpperCase();"
        "}"
        "function hexToRgb(hex){"
        "var n=normalizeHex(hex,'#4F46E5').replace('#','');"
        "return [parseInt(n.slice(0,2),16),parseInt(n.slice(2,4),16),parseInt(n.slice(4,6),16)];"
        "}"
        "function inkFor(hex){"
        "var rgb=hexToRgb(hex);"
        "var lum=(0.299*rgb[0])+(0.587*rgb[1])+(0.114*rgb[2]);"
        "return lum>=170?'#0F172A':'#F8FAFC';"
        "}"
        "function updateSwatch(input){"
        "if(!input) return;"
        "var sw=input.nextElementSibling;"
        "if(sw&&sw.tagName==='SPAN') sw.textContent=input.value||'';"
        "}"
        "function applyTheme(primary, accent, settingsRoot){"
        "var p=normalizeHex(primary, BASELINE.primary);"
        "var a=normalizeHex(accent, BASELINE.accent);"
        "var prgb=hexToRgb(p); var argb=hexToRgb(a);"
        "var body=document.body;"
        "if(body&&body.style){"
        "body.style.setProperty('--app-primary', p);"
        "body.style.setProperty('--app-accent', a);"
        "body.style.setProperty('--app-primary-rgb', prgb.join(', '));"
        "body.style.setProperty('--app-accent-rgb', argb.join(', '));"
        "body.style.setProperty('--app-primary-ink', inkFor(p));"
        "body.style.setProperty('--app-accent-ink', inkFor(a));"
        "}"
        "if(settingsRoot&&settingsRoot.style){"
        "settingsRoot.style.setProperty('--settings-accent', a);"
        "settingsRoot.style.setProperty('--settings-accent-rgb', argb.join(', '));"
        "settingsRoot.style.setProperty('--settings-accent-ink', inkFor(a));"
        "}"
        "}"
        "function bind(root){"
        "const settingsRoot=(root&&root.querySelector?root.querySelector('.settings-shell'):null)"
        "||((root&&root.matches&&root.matches('.settings-shell'))?root:null)"
        "||document.querySelector('.settings-shell');"
        "if(!settingsRoot) return;"
        "const form=settingsRoot.querySelector('form.settings-form');"
        "const select=settingsRoot.querySelector('select[name=\"settings.ui.theme_preset\"]');"
        "const primary=settingsRoot.querySelector('input[name=\"settings.ui.theme_primary_color\"]');"
        "const accent=settingsRoot.querySelector('input[name=\"settings.ui.theme_accent_color\"]');"
        "const legacy=settingsRoot.querySelector('input[name=\"settings.ui.theme_color\"]');"
        "if(!select||!primary||!accent||!form) return;"
        "const state=window.__settingsThemePreviewState||{};"
        "state.root=settingsRoot; state.form=form; state.select=select;"
        "state.primary=primary; state.accent=accent; state.legacy=legacy;"
        "state.saved={"
        "primary:normalizeHex(primary.value, BASELINE.primary),"
        "accent:normalizeHex(accent.value, BASELINE.accent)"
        "};"
        "state.dirty=false; state.pendingSave=false;"
        "window.__settingsThemePreviewState=state;"
        "function syncLegacy(){ if(state.legacy) state.legacy.value=state.accent.value||''; }"
        "function syncInputsToSaved(){"
        "state.primary.value=state.saved.primary; state.accent.value=state.saved.accent; syncLegacy();"
        "updateSwatch(state.primary); updateSwatch(state.accent);"
        "}"
        "function markDirty(){"
        "var curP=normalizeHex(state.primary.value, state.saved.primary);"
        "var curA=normalizeHex(state.accent.value, state.saved.accent);"
        "state.dirty = (curP!==state.saved.primary)||(curA!==state.saved.accent);"
        "}"
        "function applyPreview(){"
        "syncLegacy(); updateSwatch(state.primary); updateSwatch(state.accent);"
        "applyTheme(state.primary.value, state.accent.value, state.root);"
        "markDirty();"
        "}"
        "function applyPreset(name){"
        "var preset=PRESETS[name]; if(!preset) return;"
        "state.primary.value=normalizeHex(preset.primary, state.saved.primary);"
        "state.accent.value=normalizeHex(preset.accent, state.saved.accent);"
        "applyPreview();"
        "}"
        "if(!state.primary.value||!state.accent.value){applyPreset(state.select.value);} else {applyPreview();}"
        "if(state.select.dataset.themePresetBound!=='true'){"
        "state.select.addEventListener('change', function(){applyPreset(this.value);});"
        "state.primary.addEventListener('input', applyPreview);"
        "state.accent.addEventListener('input', applyPreview);"
        "state.form.addEventListener('submit', function(){ state.pendingSave=true; });"
        "state.select.dataset.themePresetBound='true';"
        "}"
        "if(window.__settingsThemePreviewGlobalBound!=='true'){"
        "document.body.addEventListener('htmx:beforeRequest', function(evt){"
        "var st=window.__settingsThemePreviewState; if(!st) return;"
        "if(requestPath(evt)==='/settings/save') return;"
        "if(!st.dirty||st.pendingSave) return;"
        "syncInputsToSaved(); applyTheme(st.saved.primary, st.saved.accent, st.root); st.dirty=false;"
        "});"
        "document.body.addEventListener('htmx:afterRequest', function(evt){"
        "var st=window.__settingsThemePreviewState; if(!st) return;"
        "if(requestPath(evt)!=='/settings/save') return;"
        "st.pendingSave=false;"
        "if(evt&&evt.detail&&evt.detail.successful){"
        "st.saved={"
        "primary:normalizeHex(st.primary.value, st.saved.primary),"
        "accent:normalizeHex(st.accent.value, st.saved.accent)"
        "};"
        "syncLegacy(); applyTheme(st.saved.primary, st.saved.accent, st.root); st.dirty=false;"
        "}else{"
        "syncInputsToSaved(); applyTheme(st.saved.primary, st.saved.accent, st.root); st.dirty=false;"
        "}"
        "});"
        "window.addEventListener('beforeunload', function(){"
        "var st=window.__settingsThemePreviewState; if(!st||!st.dirty) return;"
        "applyTheme(st.saved.primary, st.saved.accent, st.root);"
        "});"
        "window.__settingsThemePreviewGlobalBound='true';"
        "}"
        "}"
        "document.addEventListener('DOMContentLoaded', function(){bind(document);});"
        "document.body.addEventListener('htmx:afterSwap', function(evt){"
        "bind(evt.detail&&evt.detail.target?evt.detail.target:document);"
        "});"
        "})();</script>"
    )


def settings_content() -> Div:
    """Renderizza il pannello delle impostazioni completo con tabs and panes."""
    cm = get_config_manager()

    # Read values from config manager
    s = cm.data.get("settings", {})
    theme = resolve_ui_theme(s.get("ui", {}))
    accent_rgb = parse_hex_rgb(theme["accent"])
    accent_ink = readable_ink(theme["accent"])

    # Tab buttons
    tab_buttons = Div(Div("", cls="hidden"), Div("", cls="hidden"), cls="hidden")
    # Build panes via pane builders
    general_pane = _build_general_pane(cm, s)
    processing_pane = _build_processing_pane(cm, s)
    pdf_pane = _build_pdf_pane(cm, s)
    images_pane = _build_images_pane(cm, s)
    thumbnails_pane = _build_thumbnails_pane(cm, s)
    viewer_pane = _build_viewer_pane(cm, s)
    system_pane = _build_system_pane(cm, s)

    # Recreate the real tab buttons for clarity (kept here to allow localization)
    tab_buttons = Div(
        Button("General", type="button", data_tab="general", cls="settings-tab settings-tab-active"),
        Button("Performance", type="button", data_tab="performance", cls="settings-tab"),
        Button("PDF Export", type="button", data_tab="pdf", cls="settings-tab"),
        Button("Images / OCR", type="button", data_tab="images", cls="settings-tab"),
        Button("Thumbnails", type="button", data_tab="thumbnails", cls="settings-tab"),
        Button("Viewer", type="button", data_tab="viewer", cls="settings-tab"),
        Button("Paths & System", type="button", data_tab="system", cls="settings-tab"),
        cls="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-2 mb-4",
    )

    panes = Div(general_pane, processing_pane, pdf_pane, images_pane, thumbnails_pane, viewer_pane, system_pane)

    form = Form(
        tab_buttons,
        panes,
        Div(
            Button(
                "Save Settings",
                type="submit",
                cls="settings-save-btn text-white font-bold py-2.5 px-6 rounded-xl shadow",
            ),
            cls="flex justify-end mt-6",
        ),
        hx_post="/settings/save",
        hx_swap="none",
        cls="settings-form",
    )

    wrapper = Div(
        H2("Settings", cls="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-5"),
        form,
        NotStr(
            """
            <style>
                .settings-shell {
                    --settings-surface: rgba(255, 255, 255, 0.95);
                    --settings-surface-soft: rgba(248, 250, 252, 0.98);
                    --settings-border: rgba(148, 163, 184, 0.52);
                }
                .dark .settings-shell {
                    --settings-surface: rgba(15, 23, 42, 0.92);
                    --settings-surface-soft: rgba(30, 41, 59, 0.92);
                    --settings-border: rgba(100, 116, 139, 0.62);
                }
                .settings-shell .settings-tab {
                    border: 1px solid var(--settings-border);
                    border-radius: 0.8rem;
                    background: var(--settings-surface);
                    color: rgb(51 65 85);
                    font-size: 0.88rem;
                    font-weight: 700;
                    line-height: 1.1;
                    padding: 0.7rem 0.8rem;
                    cursor: pointer !important;
                    user-select: none;
                    transition: all 0.14s ease;
                }
                .dark .settings-shell .settings-tab {
                    background: var(--settings-surface-soft);
                    color: rgb(226 232 240);
                }
                .settings-shell .settings-tab:hover {
                    border-color: var(--settings-accent);
                    color: var(--settings-accent);
                    background: rgba(var(--settings-accent-rgb), 0.10);
                    transform: translateY(-1px);
                }
                .settings-shell .settings-tab.settings-tab-active {
                    background: var(--settings-accent);
                    border-color: var(--settings-accent);
                    color: var(--settings-accent-ink);
                    box-shadow: 0 4px 14px rgba(var(--settings-accent-rgb), 0.36);
                }
                .settings-shell .settings-tab:focus-visible {
                    outline: 3px solid rgba(var(--settings-accent-rgb), 0.34);
                    outline-offset: 2px;
                }
                .settings-shell .settings-field {
                    background: #ffffff;
                    border: 1px solid rgb(148 163 184);
                    color: rgb(30 41 59);
                }
                .dark .settings-shell .settings-field {
                    background: rgba(15, 23, 42, 0.95);
                    border-color: rgb(100 116 139);
                    color: rgb(241 245 249);
                }
                .settings-shell .settings-field::placeholder {
                    color: rgb(71 85 105);
                    opacity: 1;
                }
                .dark .settings-shell .settings-field::placeholder {
                    color: rgb(203 213 225);
                    opacity: 1;
                }
                .settings-shell .settings-field:focus,
                .settings-shell .settings-field:focus-visible {
                    border-color: var(--settings-accent);
                    box-shadow: 0 0 0 3px rgba(var(--settings-accent-rgb), 0.25);
                }
                .settings-shell .settings-range {
                    -webkit-appearance: none;
                    appearance: none;
                    height: 0.46rem;
                    border-radius: 999px;
                    background: rgba(var(--settings-accent-rgb), 0.26);
                    cursor: pointer !important;
                }
                .settings-shell .settings-range::-webkit-slider-runnable-track {
                    height: 0.46rem;
                    border-radius: 999px;
                    background: rgba(var(--settings-accent-rgb), 0.26);
                }
                .settings-shell .settings-range::-webkit-slider-thumb {
                    -webkit-appearance: none;
                    appearance: none;
                    width: 1.05rem;
                    height: 1.05rem;
                    border-radius: 999px;
                    background: var(--settings-accent);
                    border: 2px solid #fff;
                    margin-top: -0.30rem;
                    cursor: pointer !important;
                }
                .settings-shell .settings-range::-moz-range-track {
                    height: 0.46rem;
                    border-radius: 999px;
                    background: rgba(var(--settings-accent-rgb), 0.26);
                }
                .settings-shell .settings-range::-moz-range-thumb {
                    width: 1.05rem;
                    height: 1.05rem;
                    border-radius: 999px;
                    background: var(--settings-accent);
                    border: 2px solid #fff;
                    cursor: pointer !important;
                }
                .settings-shell .settings-checkbox {
                    -webkit-appearance: none;
                    appearance: none;
                    width: 1.35rem;
                    height: 1.35rem;
                    border: 2px solid var(--settings-accent);
                    border-radius: 0.36rem;
                    background: rgba(var(--settings-accent-rgb), 0.10);
                    cursor: pointer !important;
                    display: inline-grid;
                    place-content: center;
                    transition: all 0.12s ease;
                }
                .settings-shell .settings-checkbox::before {
                    content: '';
                    width: 0.42rem;
                    height: 0.72rem;
                    border-right: 2px solid #fff;
                    border-bottom: 2px solid #fff;
                    transform: rotate(45deg) scale(0);
                    transform-origin: center;
                    transition: transform 0.12s ease;
                }
                .settings-shell .settings-checkbox:checked {
                    background: var(--settings-accent);
                    border-color: var(--settings-accent);
                }
                .settings-shell .settings-checkbox:checked::before {
                    transform: rotate(45deg) scale(1);
                }
                .settings-shell .settings-checkbox:focus-visible {
                    outline: 3px solid rgba(var(--settings-accent-rgb), 0.34);
                    outline-offset: 2px;
                }
                .settings-shell .settings-save-btn {
                    background: var(--settings-accent) !important;
                    color: var(--settings-accent-ink) !important;
                    border: 1px solid rgba(var(--settings-accent-rgb), 0.72) !important;
                    cursor: pointer !important;
                }
                .settings-shell .settings-save-btn:hover {
                    filter: brightness(0.94);
                }
                .settings-shell .settings-save-btn:focus-visible {
                    outline: 3px solid rgba(var(--settings-accent-rgb), 0.34);
                    outline-offset: 3px;
                }
                .settings-shell [data-pane], .settings-shell [data_pane] {
                    border: 1px solid var(--settings-border);
                    border-radius: 1rem;
                    background: linear-gradient(180deg, rgba(var(--settings-accent-rgb), 0.07) 0%, transparent 100%);
                    margin-bottom: 0.75rem;
                }
                .dark .settings-shell [data-pane], .dark .settings-shell [data_pane] {
                    border-color: rgba(100, 116, 139, 0.62);
                    background: linear-gradient(
                        180deg,
                        rgba(var(--settings-accent-rgb), 0.16) 0%,
                        rgba(2, 6, 23, 0.74) 100%
                    );
                }
            </style>
            """
        ),
        NotStr(raw_init),
        NotStr(raw_file_script),
        NotStr(_theme_preview_script(theme["primary"], theme["accent"])),
        cls="settings-shell max-w-6xl mx-auto pt-6 md:pt-7 pb-20 px-4 md:px-6",
        style=(
            f"--settings-accent: {theme['accent']};"
            f"--settings-accent-rgb: {accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]};"
            f"--settings-accent-ink: {accent_ink};"
        ),
    )

    return wrapper
