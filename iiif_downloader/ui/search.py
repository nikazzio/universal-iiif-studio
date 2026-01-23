import math

import streamlit as st

from iiif_downloader.config_manager import get_config_manager
from iiif_downloader.resolvers.discovery import search_gallica
from iiif_downloader.storage.vault_manager import VaultManager
from iiif_downloader.ui.discovery import analyze_manifest
from iiif_downloader.ui.state import get_storage
from iiif_downloader.ui.styling import render_gallery_card


def render_search_page():
    """Render the unified search page in the Streamlit UI."""
    st.title("🔍 Ricerca Unificata")
    st.caption("Cerca tra i tuoi documenti OCR, i metadati locali o nei cataloghi online.")

    # Tabs for different search scopes
    tab_ocr, tab_meta, tab_online = st.tabs(["📄 OCR (Contenuto)", "💾 Biblioteca (Metadati)", "🌐 Online (Gallica)"])

    with tab_ocr:
        _render_ocr_search()

    with tab_meta:
        _render_metadata_search()

    with tab_online:
        _render_online_search()


def _render_ocr_search():
    storage = get_storage()

    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        query = col1.text_input(
            "Cerca nel testo trascritto (OCR)",
            placeholder="es. incarnatio, dante...",
            label_visibility="collapsed",
            key="search_ocr_query",
        )
        search_btn = col2.button("🔎 Cerca", width="stretch", type="primary", key="search_ocr_btn")

    if query and (search_btn or query):
        with st.spinner(f"Ricerca di '{query}' in corso..."):
            search_results = storage.search_manuscript(query)

        if not search_results:
            st.info(f"Nessun risultato trovato per '{query}' nelle trascrizioni.")
        else:
            _render_ocr_results(search_results, query)


def _render_ocr_results(search_results, query):
    cm = get_config_manager()
    per_page = int(cm.get_setting("ui.items_per_page", 12) or 12)
    per_page = max(4, min(per_page, 200))

    total_docs = len(search_results)
    total_pages = max(1, int(math.ceil(total_docs / per_page)))
    page = int(st.session_state.get("search_page", 1) or 1)
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = min(start + per_page, total_docs)

    st.subheader(f"Risultati ({total_docs} documenti)")
    if total_pages > 1:
        p1, p2, p3 = st.columns([1, 2, 1])
        if p1.button("◀ Prev", width="stretch", disabled=page <= 1, key="ocr_prev"):
            st.session_state["search_page"] = page - 1
            st.rerun()
        p2.caption(f"Pagina {page}/{total_pages}")
        if p3.button("Next ▶", width="stretch", disabled=page >= total_pages, key="ocr_next"):
            st.session_state["search_page"] = page + 1
            st.rerun()

    st.markdown("---")

    for s_res in search_results[start:end]:
        with st.expander(
            f"📖 {s_res['library']} / {s_res['doc_id']} — Trovate {len(s_res['matches'])} pagine", expanded=True
        ):
            for m in s_res["matches"]:
                c_num, c_txt, c_act = st.columns([1, 6, 1])
                text = m["full_text"]
                idx = text.lower().find(query.lower())
                start_hl = max(0, idx - 60)
                end_hl = min(len(text), idx + 60)
                snippet = (
                    ("..." if start_hl > 0 else "")
                    + text[start_hl:end_hl].replace(query, f":red[**{query}**]")
                    + ("..." if end_hl < len(text) else "")
                )

                c_num.markdown(f"**Pag. {m['page_index']}**")
                c_txt.markdown(f"_{snippet}_")

                if c_act.button("Vai ➡️", key=f"go_{s_res['doc_id']}_{m['page_index']}"):
                    st.session_state["nav_override"] = "Studio"
                    st.session_state["studio_doc_id"] = s_res["doc_id"]
                    st.session_state["studio_library"] = s_res["library"]
                    st.session_state["studio_page"] = m["page_index"]
                    st.rerun()


def _render_metadata_search():
    vault = VaultManager()

    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        query = col1.text_input(
            "Cerca nei metadati (Titolo, ID, Autore)",
            placeholder="es. Urb.lat, Divina Commedia...",
            label_visibility="collapsed",
            key="search_meta_query",
        )
        search_btn = col2.button("🔎 Cerca", width="stretch", type="primary", key="search_meta_btn")

    if query and (search_btn or query):
        results = vault.search_manuscripts(query)
        if not results:
            st.info("Nessun manoscritto trovato nel database locale.")
        else:
            st.success(f"Trovati {len(results)} manoscritti.")
            for doc in results:
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f"**{doc['label']}**")
                    c1.caption(f"{doc['library']} | {doc['id']} | {doc['status']}")
                    if c2.button("Apri", key=f"open_meta_{doc['id']}"):
                        st.session_state["nav_override"] = "Studio"
                        st.session_state["studio_doc_id"] = doc["id"]
                        st.session_state["studio_library"] = doc["library"]
                        st.rerun()


def _render_online_search():
    st.info("Cerca nuovi manoscritti nel catalogo Gallica (BnF).")

    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        query = col1.text_input(
            "Parola chiave (Gallica)",
            placeholder="es. Alighieri, Codex...",
            label_visibility="collapsed",
            key="search_online_query",
        )
        search_btn = col2.button("🔎 Cerca", width="stretch", type="primary", key="search_online_btn")

    if search_btn and query:
        with st.spinner("Ricerca online in corso..."):
            st.session_state["gallica_results"] = search_gallica(query)

    results = st.session_state.get("gallica_results", [])
    if results:
        # Use render_gallery_card and logic similar to discovery but simpler here
        cols = st.columns(4)
        for i, res in enumerate(results):
            with cols[i % 4]:
                render_gallery_card(res["title"], res["id"], res.get("preview_url"))
                if st.button("Analizza/Scarica", key=f"dl_gallica_{res['id']}"):
                    # Switch to Discovery context logic
                    st.session_state["nav_override"] = "Discovery"
                    analyze_manifest(res["manifest_url"], res["id"], "Gallica")
                    st.session_state["discovery_active_tab"] = "Segnatura / URL"  # Force UI tab?
                    # Actually analyze_manifest puts it in discovery_preview,
                    # so just rerunning goes to Discovery page if we route it.
                    st.rerun()
