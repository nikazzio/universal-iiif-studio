"""Transcription Editor Component.

Handles the right column of the Studio page: text editing, OCR, and history.
"""

import html
from pathlib import Path

import streamlit as st
from streamlit_ace import st_ace

from iiif_downloader.logger import get_logger
from iiif_downloader.ui.notifications import toast
from iiif_downloader.ui.state import get_storage

from .ocr_utils import run_ocr_sync
from .studio_state import StudioState

logger = get_logger(__name__)


def render_transcription_editor(
    doc_id: str,
    library: str,
    current_page: int,
    ocr_engine: str,
    current_model: str,
    paths: dict = None,
    total_pages: int = 1,
) -> tuple:
    """Render the transcription editor with all controls.

    Args:
        doc_id: Document ID
        library: Library name
        current_page: Current page number (1-indexed)
        ocr_engine: OCR engine name
        current_model: OCR model name
        paths: Document paths dictionary
        total_pages: Number of pages available for this document

    Returns:
        Tuple of (transcription_data, current_text_value)
    """
    storage = get_storage()
    trans = storage.load_transcription(doc_id, current_page, library)
    current_status = trans.get("status", "draft") if trans else "draft"

    st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)

    # TAB SYSTEM: Trascrizione, Cronologia, Snippet, Info
    tabs = st.tabs(["📝 Trascrizione", "📜 Cronologia", "✂️ Snippet", "ℹ️ Info Manoscritto"])

    # TAB 1: TRASCRIZIONE
    with tabs[0]:
        _render_transcription_tab(
            doc_id,
            library,
            current_page,
            trans,
            current_status,
            ocr_engine,
            current_model,
            storage,
        )

    # TAB 2: CRONOLOGIA
    with tabs[1]:
        render_history_sidebar(doc_id, library, current_page, current_data=trans, current_text="")

    # TAB 3: SNIPPET (ritagli della pagina)
    with tabs[2]:
        _render_snippets_tab(doc_id, current_page)

    # TAB 4: INFO MANOSCRITTO
    with tabs[3]:
        _render_manuscript_info(doc_id, library)

    return trans, ""  # Return empty text for now


def _render_transcription_tab(
    doc_id: str, library: str, current_page: int, trans: dict, current_status: str,
    ocr_engine: str, current_model: str, storage
) -> str:
    """Render the main transcription editor tab."""
    _render_transcription_meta(trans)
    _handle_ocr_triggers(doc_id, library, current_page, ocr_engine, current_model, storage)

    edit_key = StudioState.get_editor_key(doc_id, current_page)
    markdown_content = _resolve_markdown_content(trans, doc_id, current_page)

    _render_editor_styles()
    return _render_editor_section(
        doc_id=doc_id,
        library=library,
        current_page=current_page,
        trans=trans,
        current_status=current_status,
        storage=storage,
        markdown_content=markdown_content,
        edit_key=edit_key,
        ocr_engine=ocr_engine,
    )


def _render_transcription_meta(trans: dict | None) -> None:
    if trans:
        is_manual = trans.get("is_manual", False)
        engine = trans.get("engine", "N/A")
        conf = trans.get("average_confidence", "N/A")
        timestamp = trans.get("timestamp", "-")

        meta_parts = [f"Engine: {engine}", f"Conf: {conf}", f"🕒 {timestamp}"]
        if is_manual:
            meta_parts.append("✍️ Modificato Manualmente")

        st.caption(" | ".join(meta_parts))
    else:
        st.caption("Nessuna trascrizione. Scrivi e salva per creare.")


def _resolve_markdown_content(trans: dict | None, doc_id: str, current_page: int) -> str:
    pending_text = StudioState.get_pending_update(doc_id, current_page)
    markdown_content = trans.get("full_text", "") if trans else ""
    return pending_text if pending_text else markdown_content


def _render_editor_styles() -> None:
    st.markdown("""
        <style>
        /* Streamlit ACE Editor Customization - DARK MODE */
        .ace_editor {
            border: 2px solid #3d3d3d !important;
            border-radius: 8px !important;
            font-family: 'Georgia', serif !important;
            font-size: 15px !important;
            line-height: 1.7 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.4) !important;
            background: #1e1e1e !important;
        }
        .ace_editor.ace_focus {
            border-color: #4CAF50 !important;
            box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.2) !important;
        }
        .ace_scroller {
            background-color: #1e1e1e !important;
        }
        .ace_gutter {
            background: #252526 !important;
            color: #858585 !important;
        }
        .ace_marker-layer .ace_active-line {
            background: rgba(76, 175, 80, 0.1) !important;
        }
        /* Text colors for dark theme */
        .ace_content {
            color: #d4d4d4 !important;
        }
        /* Helper tooltip inline */
        .md-help-tooltip {
            position: relative;
            display: inline-block;
            cursor: help;
        }
        .md-help-tooltip .tooltiptext {
            visibility: hidden;
            width: 350px;
            background-color: #1e1e1e;
            color: #d4d4d4;
            text-align: left;
            border-radius: 6px;
            padding: 14px;
            position: absolute;
            z-index: 9999;
            bottom: 125%;
            right: 0;
            opacity: 0;
            transition: opacity 0.3s;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.6;
            box-shadow: 0 6px 16px rgba(0,0,0,0.4);
        }
        .md-help-tooltip .tooltiptext code {
            color: #4ec9b0;
            background: #2d2d2d;
            padding: 2px 4px;
            border-radius: 3px;
        }
        .md-help-tooltip .tooltiptext strong {
            color: #569cd6;
        }
        .md-help-tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        /* Preview styling - DARK MODE identico all'editor */
        .markdown-preview {
            border: 2px solid #3d3d3d;
            border-radius: 8px;
            padding: 20px;
            background: #1e1e1e;
            color: #d4d4d4;
            font-family: Georgia, serif;
            font-size: 15px;
            line-height: 1.7;
            height: 800px;
            overflow-y: auto;
            box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        }
        .markdown-preview:focus-within {
            border-color: #4CAF50;
            box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.2);
        }
        /* Markdown elements styling in preview */
        .markdown-preview h1, .markdown-preview h2, .markdown-preview h3 {
            color: #ffffff;
            margin-top: 1.2em;
            margin-bottom: 0.6em;
        }
        .markdown-preview h1 { border-bottom: 2px solid #3d3d3d; padding-bottom: 0.3em; }
        .markdown-preview a { color: #4CAF50; text-decoration: none; }
        .markdown-preview a:hover { text-decoration: underline; }
        .markdown-preview code {
            background: #2d2d2d;
            color: #4ec9b0;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', monospace;
        }
        .markdown-preview pre {
            background: #2d2d2d;
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
        }
        .markdown-preview blockquote {
            border-left: 4px solid #4CAF50;
            padding-left: 16px;
            margin-left: 0;
            color: #b0b0b0;
        }
        .markdown-preview ul, .markdown-preview ol {
            padding-left: 24px;
        }
        .markdown-preview hr {
            border: none;
            border-top: 1px solid #3d3d3d;
            margin: 1.5em 0;
        }
        /* COMPATTAMENTO AGGRESSIVO - Riduce tutti gli spazi verticali */
        /* Riduce il gap in TUTTI i blocchi verticali */
        [data-testid="stVerticalBlock"] {
            gap: 0.2rem !important;
        }
        /* Compatta tutti gli stElementContainer */
        .stElementContainer {
            margin-top: 0 !important;
            margin-bottom: 0.3rem !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        /* Compatta i layout wrapper */
        [data-testid="stLayoutWrapper"] {
            margin-top: 0 !important;
            margin-bottom: 0.3rem !important;
            padding: 0 !important;
        }
        /* Rimuove gap tra caption e CSS style block */
        .stElementContainer:has([data-testid="stCaptionContainer"]) {
            margin-bottom: 0 !important;
        }
        /* Rimuove gap tra CSS block e toggle */
        .stElementContainer:has(style) {
            margin-bottom: 0 !important;
        }
        /* Compatta il wrapper del toggle */
        [data-testid="stLayoutWrapper"]:has(.stCheckbox) {
            margin-top: -0.5rem !important;
            margin-bottom: 0.2rem !important;
        }
        /* Compatta spazio sotto toggle/helper */
        [data-testid="stHorizontalBlock"]:has(.stCheckbox) {
            margin-bottom: 0 !important;
        }
        /* Rimuove padding sui widget streamlit */
        [data-testid="stVerticalBlock"] > div:has(.stToggle) {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            margin: 0 !important;
        }
        /* Sposta il container dell'editor/preview verso il BASSO per allineamento */
        [data-testid="stLayoutWrapper"]:has(.stVerticalBlock > .stElementContainer[class*="trans_editor"]) {
            margin-top: 15px !important;
        }
        /* Alternativa: targetizza direttamente il container dell'editor */
        .stElementContainer[class*="trans_editor"],
        .stElementContainer:has(iframe) {
            margin-top: -5px !important;
        }
        </style>
    """, unsafe_allow_html=True)



def _render_editor_section(
    *,
    doc_id: str,
    library: str,
    current_page: int,
    trans: dict | None,
    current_status: str,
    storage,
    markdown_content: str,
    edit_key: str,
    ocr_engine: str,
) -> str:
    preview_mode = _render_preview_toggle(doc_id, current_page)
    text_val = _render_editor_body(markdown_content, edit_key, preview_mode)
    _render_save_and_actions(
        text_val=text_val,
        doc_id=doc_id,
        library=library,
        current_page=current_page,
        trans=trans,
        current_status=current_status,
        storage=storage,
        ocr_engine=ocr_engine,
    )
    return text_val


def _render_preview_toggle(doc_id: str, current_page: int) -> bool:
    col_toggle, col_help = st.columns([10, 1])
    with col_toggle:
        preview_mode = st.toggle("👁️ Anteprima Markdown", key=f"preview_{doc_id}_{current_page}", value=False)
    with col_help:
        st.markdown("""
            <div class="md-help-tooltip">
                <span style="font-size: 20px; cursor: help;">ℹ️</span>
                <div class="tooltiptext">
                    <strong>Markdown Syntax:</strong><br><br>
                    <code># Titolo</code> <code>## Sotto</code><br>
                    <code>**grassetto**</code> <code>*corsivo*</code><br>
                    <code>- item lista</code><br>
                    <code>1. item numerata</code><br>
                    <code>[testo](url)</code><br>
                    <code>![img](url)</code><br>
                    <code>`codice inline`</code><br>
                    <code>&gt; citazione</code><br>
                    <code>---</code> linea divisoria
                </div>
            </div>
        """, unsafe_allow_html=True)
    return preview_mode


def _render_editor_body(markdown_content: str, edit_key: str, preview_mode: bool) -> str:
    editor_container = st.container()
    with editor_container:
        if preview_mode:
            html_content = _render_preview_content(markdown_content)
            st.markdown(f'<div class="markdown-preview">{html_content}</div>', unsafe_allow_html=True)
            return markdown_content
        return st_ace(
            value=markdown_content,
            placeholder="Inizia a scrivere la trascrizione...",
            language="markdown",
            theme="monokai",
            keybinding="vscode",
            height=800,
            font_size=15,
            tab_size=2,
            wrap=True,
            auto_update=True,
            readonly=False,
            show_gutter=True,
            show_print_margin=False,
            key=edit_key,
        )


def _render_preview_content(markdown_content: str) -> str:
    if markdown_content and markdown_content.strip():
        html_lines = []
        for line in markdown_content.split("\n"):
            line = line.strip()
            if not line:
                html_lines.append("<br>")
            elif line.startswith("### "):
                html_lines.append(f"<h3>{html.escape(line[4:])}</h3>")
            elif line.startswith("## "):
                html_lines.append(f"<h2>{html.escape(line[3:])}</h2>")
            elif line.startswith("# "):
                html_lines.append(f"<h1>{html.escape(line[2:])}</h1>")
            elif line.startswith("- "):
                html_lines.append(f"<li>{html.escape(line[2:])}</li>")
            elif line.startswith("> "):
                html_lines.append(f"<blockquote>{html.escape(line[2:])}</blockquote>")
            elif line == "---":
                html_lines.append("<hr>")
            else:
                escaped = html.escape(line)
                escaped = escaped.replace("**", "<b>").replace("*", "<i>")
                html_lines.append(f"<p>{escaped}</p>")
        return "".join(html_lines)
    return (
        "<p style='color: #858585; text-align: center; padding-top: 2rem;'>"
        "📄 Nessun contenuto da visualizzare</p>"
    )


def _render_save_and_actions(
    *,
    text_val: str,
    doc_id: str,
    library: str,
    current_page: int,
    trans: dict | None,
    current_status: str,
    storage,
    ocr_engine: str,
) -> None:
    save_btn = st.button(
        "💾 Salva Modifiche",
        use_container_width=True,
        type="primary",
        key=f"save_trans_{doc_id}_{current_page}",
    )
    if save_btn:
        _save_transcription(text_val, doc_id, library, current_page, trans, current_status, storage)

    btn_col2, btn_col3 = st.columns(2)
    with btn_col2:
        _render_verification_button(doc_id, library, current_page, current_status, trans, storage)
    with btn_col3:
        _render_ocr_button(doc_id, library, current_page, ocr_engine, storage)


def _render_snippets_tab(doc_id: str, current_page: int):
    """Render the snippets tab showing image crops for current page."""
    logger.debug(f"Render tab snippet - doc={doc_id}, page={current_page}")

    try:
        from iiif_downloader.storage import VaultManager

        vault = VaultManager()
        snippets = vault.get_snippets(doc_id, page_num=current_page)

        if not snippets:
            logger.debug(f"Nessuno snippet trovato per {doc_id} pagina {current_page}")
            st.info("📭 Nessun snippet salvato per questa pagina.")
            st.caption("✂️ Usa il pulsante 'Taglia' nella toolbar dell'immagine per creare snippet.")
            return

        st.markdown(f"### 🖼️ Galleria Snippet ({len(snippets)})")
        st.caption(f"Pagina {current_page} - {doc_id}")
        st.markdown("---")

        # Container scrollabile per molti snippet
        st.markdown("""
            <style>
            .snippet-container {
                max-height: 600px;
                overflow-y: auto;
                padding-right: 10px;
            }
            </style>
        """, unsafe_allow_html=True)

        # Wrapper scrollabile
        with st.container():
            st.markdown('<div class="snippet-container">', unsafe_allow_html=True)

            # Mostra ogni snippet
            for snippet in snippets:
                with st.container():
                    # Colonne per layout
                    img_col, info_col = st.columns([1, 2])

                    with img_col:
                        # Mostra miniatura
                        img_path = Path(snippet['image_path'])

                        if img_path.exists():
                            st.image(snippet['image_path'], width="stretch")
                        else:
                            st.warning("⚠️ File non trovato")
                            logger.warning(f"File snippet non trovato: {img_path}")

                    with info_col:
                        # Tag categoria
                        category_colors = {
                            "Capolettera": "#FF6B6B",
                            "Glossa": "#4ECDC4",
                            "Abbreviazione": "#95E1D3",
                            "Dubbio": "#FFE66D",
                            "Illustrazione": "#A8E6CF",
                            "Decorazione": "#FF8B94",
                            "Nota Marginale": "#C7CEEA",
                            "Altro": "#B0B0B0",
                        }

                        cat_color = category_colors.get(snippet.get('category'), "#999")
                        st.markdown(
                            (
                                f"<span style='background: {cat_color}; padding: 4px 12px; "
                                "border-radius: 12px; color: white; font-weight: bold; "
                                "font-size: 0.85rem;'>{snippet.get('category', 'N/A')}</span>"
                            ),
                            unsafe_allow_html=True
                        )

                        st.caption(f"🕖 {snippet['timestamp']}")

                        # Espandi per vedere dettagli
                        with st.expander("🔍 Espandi dettagli"):
                            if snippet.get('transcription'):
                                st.markdown("**✍️ Trascrizione:**")
                                st.text(snippet['transcription'])

                            if snippet.get('notes'):
                                st.markdown("**📝 Note:**")
                                st.text_area(
                                    "Note",
                                    value=snippet['notes'],
                                    disabled=True,
                                    key=f"notes_view_{snippet['id']}",
                                    label_visibility="collapsed",
                                    height=100,
                                )

                            if snippet.get('coords_json'):
                                coords = snippet['coords_json']
                                st.caption(f"📐 Dimensioni: {coords[2]}x{coords[3]} px")

                        # Pulsante elimina
                        if st.button("🗑️ Elimina", key=f"del_snippet_{snippet['id']}", type="secondary"):
                            vault.delete_snippet(snippet['id'])
                            toast("✅ Snippet eliminato!", icon="🗑️")
                            st.rerun()

                    st.markdown("<hr style='margin: 1rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"❌ Errore nel caricamento snippet: {e}")


def _handle_ocr_triggers(doc_id, library, current_page, ocr_engine, current_model, storage):
    """Handle OCR confirmation and execution triggers."""
    # Confirmation dialog
    if StudioState.get(StudioState.CONFIRM_OCR_SYNC) == current_page:
        st.warning("⚠️ Testo esistente! Sovrascrivere?", icon="⚠️")
        c1, c2 = st.columns(2)
        if c1.button("Sì, Sovrascrivi", width="stretch", type="primary"):
            StudioState.set(StudioState.TRIGGER_OCR_SYNC, current_page)
            StudioState.set(StudioState.CONFIRM_OCR_SYNC, None)
            st.rerun()
        if c2.button("No, Annulla", width="stretch"):
            StudioState.set(StudioState.CONFIRM_OCR_SYNC, None)
            st.rerun()

    # Execute OCR
    if StudioState.get(StudioState.TRIGGER_OCR_SYNC) == current_page:
        run_ocr_sync(doc_id, library, current_page, ocr_engine, current_model)
        StudioState.set(StudioState.TRIGGER_OCR_SYNC, None)
        st.rerun()


def _save_transcription(text_val, doc_id, library, current_page, trans, current_status, storage):
    """Save transcription to storage."""
    # Text_val is now plain Markdown text, no need to parse HTML
    clean_text = text_val if text_val else ""

    new_data = {
        "full_text": clean_text,
        "rich_text": "",  # No longer using HTML rich text
        "engine": trans.get("engine", "manual") if trans else "manual",
        "is_manual": True,
        "status": current_status,
        "average_confidence": 1.0,
    }
    storage.save_transcription(doc_id, current_page, new_data, library)

    # Feedback senza rerun completo
    toast("✅ Modifiche salvate!", icon="💾")
    # Non facciamo più rerun per migliorare UX


def _render_verification_button(doc_id, library, current_page, current_status, trans, storage):
    """Render the verification toggle button."""
    is_verified = current_status == "verified"
    btn_label = "⚪ Segna come da Verificare" if is_verified else "✅ Segna come Verificato"

    if st.button(btn_label, width="stretch", key=f"btn_verify_{current_page}"):
        new_status = "draft" if is_verified else "verified"
        data_to_save = trans if trans else {"full_text": "", "lines": [], "engine": "manual"}

        # Save snapshot to history
        storage.save_history(doc_id, current_page, data_to_save, library)

        data_to_save["status"] = new_status
        data_to_save["is_manual"] = True
        storage.save_transcription(doc_id, current_page, data_to_save, library)
        st.rerun()


def _render_ocr_button(doc_id, library, current_page, ocr_engine, storage):
    """Render the OCR execution button."""
    if st.button(
        f"🤖 Nuova Chiamata {ocr_engine}",
        width="stretch",
        key=f"btn_ocr_{current_page}",
    ):
        existing = storage.load_transcription(doc_id, current_page, library)
        if existing:
            StudioState.set(StudioState.CONFIRM_OCR_SYNC, current_page)
        else:
            StudioState.set(StudioState.TRIGGER_OCR_SYNC, current_page)
        st.rerun()


def render_history_sidebar(doc_id, library, current_page, current_data=None, current_text=""):
    """Render the history list in a vertical side column."""
    storage = get_storage()

    history = storage.load_history(doc_id, current_page, library)

    if not history:
        st.info("📭 Nessuna versione salvata")
        return

    # Header compatto con count
    col1, col2 = st.columns([2, 1])
    with col1:
        st.caption(f"**{len(history)} versioni**")
    with col2:
        if st.button("🗑️", key=f"clear_{current_page}", help="Svuota cronologia", width="stretch"):
            if st.session_state.get(f"confirm_clear_{current_page}"):
                storage.clear_history(doc_id, current_page, library)
                del st.session_state[f"confirm_clear_{current_page}"]
                st.rerun()
            else:
                st.session_state[f"confirm_clear_{current_page}"] = True
                st.rerun()

    if st.session_state.get(f"confirm_clear_{current_page}"):
        st.warning("⚠️ Conferma eliminazione")
        if st.button("Annulla", key=f"cancel_{current_page}", width="stretch"):
            del st.session_state[f"confirm_clear_{current_page}"]
            st.rerun()

    st.divider()

    edit_key = StudioState.get_editor_key(doc_id, current_page)

    # Versioni in container scrollabile
    for i in range(len(history)):
        idx = len(history) - 1 - i
        entry = history[idx]
        prev_entry = history[idx - 1] if idx > 0 else None

        _render_history_entry(
            entry,
            prev_entry,
            idx,
            i,
            len(history),
            doc_id,
            library,
            current_page,
            current_data,
            current_text,
            edit_key,
            storage,
        )


def _render_history_entry(
    entry,
    prev_entry,
    idx,
    i,
    total_entries,
    doc_id,
    library,
    current_page,
    current_data,
    current_text,
    edit_key,
    storage,
):
    """Render a single history entry."""
    ts = entry.get("timestamp", "-").split(" ")[1]  # Time only
    eng = entry.get("engine", "manual")
    status = entry.get("status", "draft")
    chars = len(entry.get("full_text", ""))
    is_manual_entry = entry.get("is_manual", False)

    icon = "✍️" if is_manual_entry else "🤖"
    v_label = " 📌" if idx == 0 else ""

    diff = 0
    if prev_entry:
        diff = chars - len(prev_entry.get("full_text", ""))

    diff_str = f"{diff:+d}" if diff != 0 else "="
    diff_color = "#28a745" if diff > 0 else "#dc3545" if diff < 0 else "#6c757d"
    status_icon = " ✅" if status == "verified" else ""

    with st.container():
        # Header compatto: tempo + icone + chars in una riga
        col1, col2 = st.columns([3, 1])
        with col1:
            metadata_html = (
                "<div style='line-height:1.2;'>"
                f"<span style='font-weight:600; font-size:0.9rem;'>{ts}</span>"
                f"<span style='margin-left:4px;'>{icon}</span>"
                f"{v_label}{status_icon}"
                "<br>"
                "<span style='color:#666; font-size:0.75rem;'>"
                f"{eng} • {chars} ch "
                f"<span style='color:{diff_color}'>({diff_str})</span>"
                "</span>"
                "</div>"
            )
            st.markdown(metadata_html, unsafe_allow_html=True)
        with col2:
            if st.button(
                "↩",
                key=f"restore_side_{current_page}_{idx}",
                width="stretch",
                help="Ripristina",
            ):
                _restore_history_version(
                    entry, current_text, current_data, doc_id, library, current_page, edit_key, storage
                )

    if i < total_entries - 1:
        st.markdown("<hr style='margin: 0.2rem 0; opacity: 0.3;'>", unsafe_allow_html=True)


def _restore_history_version(entry, current_text, current_data, doc_id, library, current_page, edit_key, storage):
    """Restore a previous version from history."""
    # Verifica: se current_text è vuoto ma abbiamo current_data, usiamo quello
    if not current_text and current_data:
        current_text = current_data.get("full_text", "")

    # Save current state as backup (solo se c'è contenuto)
    if current_text and current_text.strip():
        snap = {
            "full_text": current_text,
            "rich_text": "",  # Non usiamo più rich_text
            "engine": current_data.get("engine", "manual") if current_data else "manual",
            "is_manual": True,
            "status": current_data.get("status", "draft") if current_data else "draft",
        }
        storage.save_history(doc_id, current_page, snap, library)

    # Restore selected version
    storage.save_transcription(doc_id, current_page, entry, library)

    # Clear editor state to force refresh
    StudioState.clear_editor_state(doc_id, current_page)

    # Update editor with restored content (sempre full_text per Markdown)
    restored_plain = entry.get("full_text", "")
    if edit_key in st.session_state:
        st.session_state[edit_key] = restored_plain

    toast("✅ Versione ripristinata!", icon="↩")
    st.rerun()

def _render_manuscript_info(doc_id: str, library: str):
    """Render manuscript metadata and details in Info tab."""
    storage = get_storage()
    meta = storage.load_metadata(doc_id, library)
    stats = storage.load_image_stats(doc_id, library)

    st.markdown("### 📜 Informazioni Manoscritto")

    if meta:
        st.markdown(f"**Titolo**: {meta.get('label', 'Senza Titolo')}")

        desc = meta.get("description", "-")
        st.markdown(f"**Descrizione**: {desc}")

        st.markdown(f"**Attribuzione**: {meta.get('attribution', '-')}")
        st.markdown(f"**Licenza**: {meta.get('license', '-')}")

        if "metadata" in meta and isinstance(meta["metadata"], list):
            st.markdown("---")
            st.markdown("#### 🏷️ Metadati Aggiuntivi")
            for item in meta["metadata"]:
                if isinstance(item, dict):
                    label = item.get("label", "Campo")
                    value = item.get("value", "-")
                    st.markdown(f"**{label}**: {value}")

    if stats:
        st.markdown("---")
        st.markdown("#### 📊 Statistiche Tecniche")

        pages_s = stats.get("pages", [])
        if pages_s:
            avg_w = sum(p["width"] for p in pages_s) // len(pages_s)
            avg_h = sum(p["height"] for p in pages_s) // len(pages_s)
            total_mb = sum(p["size_bytes"] for p in pages_s) / (1024 * 1024)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Pagine", len(pages_s))
            with col2:
                st.metric("Risoluzione", f"{avg_w}×{avg_h}")
            with col3:
                st.metric("Peso", f"{total_mb:.1f} MB")
