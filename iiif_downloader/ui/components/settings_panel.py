from __future__ import annotations

from typing import Any

import streamlit as st


def _init_state(key: str, value: Any) -> None:
    if key not in st.session_state:
        st.session_state[key] = value


def _read_int(cm: Any, dotted: str, default: int) -> int:
    try:
        return int(cm.get_setting(dotted, default) or default)
    except (TypeError, ValueError):
        return default


def _read_float(cm: Any, dotted: str, default: float) -> float:
    try:
        return float(cm.get_setting(dotted, default) or default)
    except (TypeError, ValueError):
        return default


def _state_int(key: str, default: int) -> int:
    try:
        return int(st.session_state.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _state_float(key: str, default: float) -> float:
    try:
        return float(st.session_state.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _apply_and_save(cm: Any) -> None:
    cm.set_downloads_dir(st.session_state.get("cfg_downloads_dir", "downloads"))
    cm.set_temp_dir(st.session_state.get("cfg_temp_dir", "temp_images"))
    cm.data.setdefault("paths", {})["models_dir"] = (
        st.session_state.get("cfg_models_dir", "models") or "models"
    ).strip()
    cm.data.setdefault("paths", {})["logs_dir"] = (st.session_state.get("cfg_logs_dir", "logs") or "logs").strip()

    cm.set_setting("system.download_workers", _state_int("cfg_download_workers", 4))
    cm.set_setting("system.ocr_concurrency", _state_int("cfg_ocr_concurrency", 1))
    cm.set_setting("system.request_timeout", _state_int("cfg_request_timeout", 30))
    cm.set_setting("ocr.kraken_enabled", bool(st.session_state.get("cfg_kraken_enabled", False)))

    cm.set_setting(
        "defaults.preferred_ocr_engine",
        st.session_state.get("cfg_preferred_ocr_engine", "openai") or "openai",
    )
    cm.set_setting(
        "defaults.auto_generate_pdf",
        bool(st.session_state.get("cfg_auto_generate_pdf", True)),
    )

    cm.set_setting("ui.theme_color", st.session_state.get("cfg_theme_color", "#FF4B4B") or "#FF4B4B")
    cm.set_setting("ui.items_per_page", _state_int("cfg_items_per_page", 12))
    toast_ms = _state_int("cfg_toast_duration", 3000)
    if 0 < toast_ms <= 60:
        toast_ms = toast_ms * 1000
    toast_ms = max(250, min(toast_ms, 60000))
    cm.set_setting("ui.toast_duration", toast_ms)

    cm.set_setting("images.iiif_quality", st.session_state.get("cfg_iiif_quality", "default") or "default")

    strategy_mode = st.session_state.get("cfg_strategy_mode", "Guidata") or "Guidata"
    if strategy_mode == "Avanzata":
        raw_strategy = st.session_state.get("cfg_download_strategy", "max,3000,1740") or "max,3000,1740"
        strategy = [s.strip() for s in str(raw_strategy).split(",") if s.strip()]
    else:
        s1 = (st.session_state.get("cfg_strategy_1") or "").strip()
        s2 = (st.session_state.get("cfg_strategy_2") or "").strip()
        s3 = (st.session_state.get("cfg_strategy_3") or "").strip()
        strategy = [s for s in [s1, s2, s3] if s]

    cm.set_setting("images.download_strategy", strategy or ["max", "3000", "1740"])
    cm.set_setting("images.viewer_quality", _state_int("cfg_viewer_quality", 95))
    cm.set_setting("images.ocr_quality", _state_int("cfg_ocr_quality", 95))
    ram_gb = _state_float("cfg_tile_stitch_max_ram_gb", 2.0)
    ram_gb = max(1.0, min(ram_gb, 64.0))
    cm.set_setting("images.tile_stitch_max_ram_gb", ram_gb)

    cm.set_setting("pdf.viewer_dpi", _state_int("cfg_pdf_viewer_dpi", 150))
    cm.set_setting("pdf.ocr_dpi", _state_int("cfg_pdf_ocr_dpi", 300))

    cm.set_setting("thumbnails.max_long_edge_px", _state_int("cfg_thumb_max_edge", 320))
    cm.set_setting("thumbnails.jpeg_quality", _state_int("cfg_thumb_jpeg_quality", 70))
    cm.set_setting("thumbnails.columns", _state_int("cfg_thumb_columns", 6))
    cm.set_setting("thumbnails.paginate_enabled", bool(st.session_state.get("cfg_thumb_paginate", True)))
    page_size = _state_int("cfg_thumb_page_size", 48)
    page_size = max(12, min(page_size, 500))
    cm.set_setting("thumbnails.page_size", page_size)
    cm.set_setting(
        "thumbnails.default_select_all",
        bool(st.session_state.get("cfg_thumb_default_select_all", True)),
    )

    cleanup_days = _state_int("cfg_temp_cleanup_days", 7)
    cleanup_days = max(1, min(cleanup_days, 30))
    cm.set_setting("housekeeping.temp_cleanup_days", cleanup_days)
    cm.set_setting("logging.level", str(st.session_state.get("cfg_log_level", "INFO") or "INFO").upper())

    cm.set_api_key("openai", st.session_state.get("cfg_openai", ""))
    cm.set_api_key("anthropic", st.session_state.get("cfg_anthropic", ""))
    cm.set_api_key("google_vision", st.session_state.get("cfg_google", ""))
    cm.set_api_key("huggingface", st.session_state.get("cfg_hf", ""))

    cm.save()
    st.toast("Configurazione salvata!", icon="✅")

    try:
        cm.get_downloads_dir().mkdir(parents=True, exist_ok=True)
        cm.get_temp_dir().mkdir(parents=True, exist_ok=True)
        cm.get_models_dir().mkdir(parents=True, exist_ok=True)
        cm.get_logs_dir().mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    st.session_state["cfg_last_saved"] = ""
    if "cfg_snapshot" in st.session_state and "cfg_tracked_keys" in st.session_state:
        st.session_state["cfg_snapshot"] = {
            k: st.session_state.get(k) for k in (st.session_state.get("cfg_tracked_keys") or [])
        }


def _init_defaults(cm: Any) -> None:
    _init_state("cfg_last_saved", "")
    _init_state("cfg_downloads_dir", str(cm.data.get("paths", {}).get("downloads_dir", "downloads")))
    _init_state("cfg_temp_dir", str(cm.data.get("paths", {}).get("temp_dir", "temp_images")))
    _init_state("cfg_models_dir", str(cm.data.get("paths", {}).get("models_dir", "models")))
    _init_state("cfg_logs_dir", str(cm.data.get("paths", {}).get("logs_dir", "logs")))

    _init_state("cfg_download_workers", _read_int(cm, "system.download_workers", 4))
    _init_state("cfg_ocr_concurrency", _read_int(cm, "system.ocr_concurrency", 1))
    _init_state("cfg_request_timeout", _read_int(cm, "system.request_timeout", 30))
    _init_state("cfg_kraken_enabled", bool(cm.get_setting("ocr.kraken_enabled", False)))

    _init_state("cfg_preferred_ocr_engine", str(cm.get_setting("defaults.preferred_ocr_engine", "openai")))
    _init_state("cfg_auto_generate_pdf", bool(cm.get_setting("defaults.auto_generate_pdf", True)))

    _init_state("cfg_theme_color", str(cm.get_setting("ui.theme_color", "#FF4B4B")))
    _init_state("cfg_items_per_page", _read_int(cm, "ui.items_per_page", 12))
    toast_ms_init = _read_int(cm, "ui.toast_duration", 3000)
    if 0 < toast_ms_init <= 60:
        toast_ms_init = toast_ms_init * 1000
    toast_ms_init = max(250, min(toast_ms_init, 60000))
    _init_state("cfg_toast_duration", toast_ms_init)

    _init_state("cfg_iiif_quality", str(cm.get_setting("images.iiif_quality", "default")))
    existing_strategy = [str(x) for x in cm.get_setting("images.download_strategy", ["max", "3000", "1740"]) or []]
    _init_state("cfg_download_strategy", ",".join(existing_strategy))
    _init_state("cfg_strategy_mode", "Guidata")

    guided_default = existing_strategy + ["", ""]
    _init_state("cfg_strategy_1", guided_default[0] if len(guided_default) > 0 else "max")
    _init_state("cfg_strategy_2", guided_default[1] if len(guided_default) > 1 else "3000")
    _init_state("cfg_strategy_3", guided_default[2] if len(guided_default) > 2 else "1740")
    _init_state("cfg_viewer_quality", _read_int(cm, "images.viewer_quality", 95))
    _init_state("cfg_ocr_quality", _read_int(cm, "images.ocr_quality", 95))
    _init_state("cfg_tile_stitch_max_ram_gb", _read_float(cm, "images.tile_stitch_max_ram_gb", 2.0))

    legacy_pdf_dpi = _read_int(cm, "pdf.render_dpi", 300)
    _init_state("cfg_pdf_viewer_dpi", _read_int(cm, "pdf.viewer_dpi", legacy_pdf_dpi))
    _init_state("cfg_pdf_ocr_dpi", _read_int(cm, "pdf.ocr_dpi", legacy_pdf_dpi))

    _init_state("cfg_thumb_max_edge", _read_int(cm, "thumbnails.max_long_edge_px", 320))
    _init_state("cfg_thumb_jpeg_quality", _read_int(cm, "thumbnails.jpeg_quality", 70))
    _init_state("cfg_thumb_columns", _read_int(cm, "thumbnails.columns", 6))
    _init_state("cfg_thumb_paginate", bool(cm.get_setting("thumbnails.paginate_enabled", True)))
    _init_state("cfg_thumb_page_size", _read_int(cm, "thumbnails.page_size", 48))
    _init_state("cfg_thumb_default_select_all", bool(cm.get_setting("thumbnails.default_select_all", True)))

    _init_state("cfg_temp_cleanup_days", _read_int(cm, "housekeeping.temp_cleanup_days", 7))
    _init_state("cfg_log_level", str(cm.get_setting("logging.level", "INFO")).upper())

    _init_state("cfg_openai", cm.get_api_key("openai", ""))
    _init_state("cfg_anthropic", cm.get_api_key("anthropic", ""))
    _init_state("cfg_google", cm.get_api_key("google_vision", ""))
    _init_state("cfg_hf", cm.get_api_key("huggingface", ""))

    tracked_keys = _tracked_keys()
    _init_state("cfg_tracked_keys", tracked_keys)
    if "cfg_snapshot" not in st.session_state:
        st.session_state["cfg_snapshot"] = {k: st.session_state.get(k) for k in tracked_keys}


def _tracked_keys() -> list[str]:
    return [
        "cfg_downloads_dir",
        "cfg_temp_dir",
        "cfg_models_dir",
        "cfg_logs_dir",
        "cfg_download_workers",
        "cfg_ocr_concurrency",
        "cfg_request_timeout",
        "cfg_kraken_enabled",
        "cfg_preferred_ocr_engine",
        "cfg_auto_generate_pdf",
        "cfg_theme_color",
        "cfg_items_per_page",
        "cfg_toast_duration",
        "cfg_iiif_quality",
        "cfg_strategy_mode",
        "cfg_download_strategy",
        "cfg_strategy_1",
        "cfg_strategy_2",
        "cfg_strategy_3",
        "cfg_viewer_quality",
        "cfg_ocr_quality",
        "cfg_tile_stitch_max_ram_gb",
        "cfg_pdf_viewer_dpi",
        "cfg_pdf_ocr_dpi",
        "cfg_thumb_max_edge",
        "cfg_thumb_jpeg_quality",
        "cfg_thumb_columns",
        "cfg_thumb_paginate",
        "cfg_thumb_page_size",
        "cfg_thumb_default_select_all",
        "cfg_temp_cleanup_days",
        "cfg_log_level",
        "cfg_openai",
        "cfg_anthropic",
        "cfg_google",
        "cfg_hf",
    ]


def _render_header(cm: Any) -> None:
    st.title("⚙️ Impostazioni")
    st.caption(f"Salvataggio locale in config.json · {cm.path}")


def _render_actions(cm: Any) -> None:
    tracked_keys = st.session_state.get("cfg_tracked_keys") or _tracked_keys()
    a1, a2, a3 = st.columns([1, 1, 3])
    if a1.button("💾 Salva", width="stretch", type="primary"):
        _apply_and_save(cm)
    if a2.button("🔄 Ricarica", width="stretch"):
        for k in list(st.session_state.keys()):
            if k.startswith("cfg_"):
                del st.session_state[k]
        st.rerun()
    snapshot = st.session_state.get("cfg_snapshot") or {}
    dirty = any(st.session_state.get(k) != snapshot.get(k) for k in tracked_keys)
    if dirty:
        a3.warning("Modifiche non salvate: premi 💾 Salva", icon="⚠️")
    else:
        a3.caption("Suggerimento: salva dopo aver modificato una tab.")


def _render_paths_tab(cm: Any) -> None:
    p1, p2 = st.columns(2)
    p1.text_input(
        "Cartella download",
        key="cfg_downloads_dir",
        help="Percorso relativo o assoluto. Se relativo, viene risolto rispetto alla cartella di esecuzione.",
    )
    p2.text_input(
        "Cartella temporanei",
        key="cfg_temp_dir",
        help="Dove salvare file temporanei/cache (relativa o assoluta).",
    )
    p3, p4 = st.columns(2)
    p3.text_input(
        "Cartella modelli (Kraken)",
        key="cfg_models_dir",
        help="Cartella per modelli OCR/HTR (relativa o assoluta).",
    )
    p4.text_input(
        "Cartella log",
        key="cfg_logs_dir",
        help="Cartella dove scrivere i log (relativa o assoluta).",
    )

    resolved_rows = [
        {"Nome": "downloads", "Percorso reale": str(cm.get_downloads_dir())},
        {"Nome": "temp", "Percorso reale": str(cm.get_temp_dir())},
        {"Nome": "models", "Percorso reale": str(cm.get_models_dir())},
        {"Nome": "logs", "Percorso reale": str(cm.get_logs_dir())},
    ]
    st.dataframe(resolved_rows, width="stretch", hide_index=True)


def _render_system_tab() -> None:
    c1, c2, c3 = st.columns(3)
    c1.slider(
        "Download workers",
        min_value=1,
        max_value=10,
        step=1,
        key="cfg_download_workers",
        help="Quante pagine scaricare in parallelo. Valori più alti = più veloce ma più carico su rete/server.",
    )
    c2.slider(
        "OCR concurrency",
        min_value=1,
        max_value=10,
        step=1,
        key="cfg_ocr_concurrency",
        help="Quante pagine processare OCR in parallelo. Di solito 1–2 è più stabile.",
    )
    c3.slider(
        "Timeout richieste (s)",
        min_value=5,
        max_value=120,
        step=5,
        key="cfg_request_timeout",
        help="Tempo massimo per singola richiesta HTTP. Aumenta se i server sono lenti.",
    )

    d1, d2, d3 = st.columns(3)
    d1.selectbox(
        "Motore OCR predefinito",
        ["openai", "kraken", "anthropic", "google", "huggingface"],
        key="cfg_preferred_ocr_engine",
        help="Provider OCR suggerito di default nelle schermate OCR.",
    )
    d2.checkbox(
        "Scarica PDF nativo (se disponibile)",
        key="cfg_auto_generate_pdf",
        help=(
            "Se abilitato, quando il manifest IIIF fornisce un PDF ufficiale (rendering), "
            "l'app lo scarica come file aggiuntivo. Non crea PDF dalle immagini."
        ),
    )
    d3.checkbox(
        "Abilita Kraken (richiede dipendenze)",
        key="cfg_kraken_enabled",
        help="Disabilitato di default per evitare installazioni pesanti (PyTorch/CUDA).",
    )


def _render_ui_tab() -> None:
    u1, u2, u3 = st.columns(3)
    u1.color_picker("Colore tema", key="cfg_theme_color", help="Colore principale dell'interfaccia.")
    u2.slider(
        "Risultati per pagina",
        min_value=4,
        max_value=200,
        step=1,
        key="cfg_items_per_page",
        help="Numero di elementi mostrati per pagina (Ricerca, Gallica, ecc.).",
    )
    u3.slider(
        "Durata toast (ms)",
        min_value=250,
        max_value=60000,
        step=250,
        key="cfg_toast_duration",
        help="Quanto resta visibile una notifica (toast) prima di sparire.",
    )


def _render_iiif_tab() -> None:
    i1, i2 = st.columns(2)
    i2.selectbox(
        "IIIF quality",
        ["default", "color", "gray", "bitonal"],
        key="cfg_iiif_quality",
        help="Qualità/colore richiesto al server IIIF (dipende dal provider).",
    )

    strategy_mode = i1.radio(
        "Modalità download strategy",
        ["Guidata", "Avanzata"],
        key="cfg_strategy_mode",
        horizontal=True,
        help="Guidata: selezioni 1–3 tentativi. Avanzata: inserisci una lista comma-separated.",
    )

    common_sizes = ["max", "5000", "4000", "3500", "3000", "2500", "2000", "1740", "1500", "1200"]
    if strategy_mode == "Guidata":
        s1, s2, s3 = st.columns(3)
        s1.selectbox(
            "Tentativo 1",
            common_sizes,
            key="cfg_strategy_1",
            help="Primo tentativo. 'max' prova la massima dimensione; numeri = larghezza in px.",
        )
        s2.selectbox(
            "Tentativo 2",
            [""] + common_sizes,
            key="cfg_strategy_2",
            help="Secondo tentativo se il primo fallisce (puoi lasciarlo vuoto).",
        )
        s3.selectbox(
            "Tentativo 3",
            [""] + common_sizes,
            key="cfg_strategy_3",
            help="Terzo tentativo se i precedenti falliscono (puoi lasciarlo vuoto).",
        )
    else:
        st.text_input(
            "Download strategy (comma-separated)",
            key="cfg_download_strategy",
            help="Lista tentativi in ordine. Esempio: max,3000,1740 (max = massima dimensione).",
        )

    q1, q2 = st.columns(2)
    q1.slider(
        "Viewer JPEG quality",
        min_value=50,
        max_value=100,
        key="cfg_viewer_quality",
        help="Qualità JPEG per anteprime/viewer (più alto = più qualità, più peso).",
    )
    q2.slider(
        "OCR JPEG quality",
        min_value=50,
        max_value=100,
        key="cfg_ocr_quality",
        help="Qualità JPEG per immagini inviate all'OCR (più alto = più qualità, più peso).",
    )

    with st.expander("Opzioni avanzate (gestione risorse)", expanded=False):
        st.slider(
            "Limite RAM Stitching (GB)",
            min_value=1,
            max_value=32,
            step=1,
            key="cfg_tile_stitch_max_ram_gb",
            help=(
                "Definisce quanta memoria RAM l'app può usare per unire le immagini IIIF "
                "prima di passare alla modalità disco."
            ),
        )


def _render_thumbnails_tab(cm: Any) -> None:
    st.subheader("🖼️ Thumbnails")
    st.caption("Impostazioni per anteprime pagina (Export Studio).")

    c1, c2, c3 = st.columns(3)
    c1.slider(
        "Dimensione (max lato lungo, px)",
        min_value=64,
        max_value=1024,
        step=16,
        key="cfg_thumb_max_edge",
        help="Thumbnails più piccole = UI più veloce e cache più leggera.",
    )
    c2.slider(
        "Qualità JPEG (0-100)",
        min_value=30,
        max_value=95,
        step=1,
        key="cfg_thumb_jpeg_quality",
        help="Qualità più alta = thumbnails più pesanti.",
    )
    c3.slider(
        "Colonne griglia",
        min_value=3,
        max_value=10,
        step=1,
        key="cfg_thumb_columns",
    )

    st.checkbox(
        "Paginazione thumbnails (consigliato per manoscritti lunghi)",
        key="cfg_thumb_paginate",
    )
    st.slider(
        "Numero pagine per schermata",
        min_value=12,
        max_value=200,
        step=4,
        key="cfg_thumb_page_size",
        help="Usato come default della finestra visibile quando la paginazione è attiva.",
    )
    st.checkbox(
        "Default: esporta tutto il PDF",
        key="cfg_thumb_default_select_all",
    )

    st.markdown("---")
    st.subheader("Cache thumbnails")
    st.caption("Le thumbnails sono salvate sotto `downloads/<lib>/<doc>/data/thumbnails/`.")

    confirm = st.checkbox("Confermo: voglio cancellare tutte le thumbnails cached", value=False)
    if st.button("🧽 Svuota cache thumbnails (globale)", disabled=not confirm):
        removed = 0
        base = cm.get_downloads_dir()
        with st.spinner("Cancellazione thumbnails..."):
            try:
                for thumb in base.glob("**/data/thumbnails/*.jpg"):
                    try:
                        thumb.unlink()
                        removed += 1
                    except OSError:
                        continue
            except OSError:
                pass
        st.success(f"Rimossi {removed} file thumbnails.")


def _render_pdf_tab() -> None:
    st.caption(
        "Queste opzioni controllano come il PDF viene renderizzato in immagine. "
        "La visualizzazione può usare DPI più bassi per essere più veloce; "
        "l'OCR/LLM usa DPI più alti per massimizzare la qualità."
    )

    p1, p2 = st.columns(2)
    p1.slider(
        "DPI PDF (Visualizzazione)",
        min_value=72,
        max_value=400,
        step=1,
        key="cfg_pdf_viewer_dpi",
        help=("Usato per il rendering on-the-fly nello Studio quando mancano le immagini estratte. Default 150."),
    )
    p2.slider(
        "DPI PDF (Import + OCR/LLM)",
        min_value=72,
        max_value=600,
        step=1,
        key="cfg_pdf_ocr_dpi",
        help=(
            "Usato per convertire PDF→immagini durante l'import e (se serve) "
            "per generare l'immagine inviata all'OCR/LLM. Default 300."
        ),
    )


def _render_cleanup_tab(cm: Any) -> None:
    d1, d2 = st.columns([2, 1])
    d1.caption(f"Cartella cache/temporanei: {cm.get_temp_dir()}")
    d2.slider(
        "Giorni cache",
        min_value=1,
        max_value=30,
        step=1,
        key="cfg_temp_cleanup_days",
        help="All'avvio, elimina automaticamente i file temporanei più vecchi di N giorni.",
    )


def _render_logging_tab() -> None:
    st.selectbox(
        "Log level",
        ["DEBUG", "INFO", "WARNING", "ERROR"],
        key="cfg_log_level",
        help="Livello di dettaglio dei log (DEBUG è molto verboso).",
    )


def _render_api_keys_tab() -> None:
    st.caption(
        "Le chiavi API sono salvate localmente in config.json e vengono usate solo "
        "per chiamare i provider selezionati."
    )
    k1, k2, k3, k4 = st.columns(4)
    k1.text_input(
        "OpenAI",
        key="cfg_openai",
        type="password",
        help="API key OpenAI (usata per OCR/LLM quando selezionato).",
    )
    k2.text_input(
        "Anthropic",
        key="cfg_anthropic",
        type="password",
        help="API key Anthropic (usata per OCR/LLM quando selezionato).",
    )
    k3.text_input(
        "Google",
        key="cfg_google",
        type="password",
        help="API key Google Vision (OCR quando selezionato).",
    )
    k4.text_input(
        "HuggingFace",
        key="cfg_hf",
        type="password",
        help="Token Hugging Face (modelli/servizi quando selezionato).",
    )


def render_settings_page(cm: Any) -> None:
    """Render the full Settings page backed by config.json (ConfigManager)."""
    _render_header(cm)
    _init_defaults(cm)
    _render_actions(cm)

    tabs = st.tabs(
        [
            "📁 Percorsi",
            "⚡ Sistema",
            "🎛️ UI",
            "🖼️ IIIF",
            "🖼️ Thumbnails",
            "📄 PDF",
            "🧹 Pulizia",
            "🪵 Logging",
            "🔑 API Keys",
        ]
    )

    with tabs[0]:
        _render_paths_tab(cm)
    with tabs[1]:
        _render_system_tab()
    with tabs[2]:
        _render_ui_tab()
    with tabs[3]:
        _render_iiif_tab()
    with tabs[4]:
        _render_thumbnails_tab(cm)
    with tabs[5]:
        _render_pdf_tab()
    with tabs[6]:
        _render_cleanup_tab(cm)
    with tabs[7]:
        _render_logging_tab()
    with tabs[8]:
        _render_api_keys_tab()
