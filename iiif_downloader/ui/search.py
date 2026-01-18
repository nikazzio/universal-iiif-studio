import math

import streamlit as st

from iiif_downloader.config_manager import get_config_manager
from iiif_downloader.ui.state import get_storage


def render_search_page():
    st.title("🔍 Ricerca Globale")
    st.caption("Cerca parole o frasi in tutte le trascrizioni salvate nel tuo database locale.")

    storage = get_storage()

    # Central Search Bar
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        query = col1.text_input("Parola da cercare", placeholder="es. incarnatio, dante...",
                                label_visibility="collapsed")
        search_btn = col2.button("🔎 Cerca", use_container_width=True, type="primary")

    if query and (search_btn or query):
        with st.spinner(f"Ricerca di '{query}' in corso..."):
            search_results = storage.search_manuscript(query)

        if not search_results:
            st.info(f"Nessun risultato trovato per '{query}'.")
        else:
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
                if p1.button("◀ Prev", use_container_width=True, disabled=page <= 1):
                    st.session_state["search_page"] = page - 1
                    st.rerun()
                p2.caption(f"Pagina {page}/{total_pages}")
                if p3.button("Next ▶", use_container_width=True, disabled=page >= total_pages):
                    st.session_state["search_page"] = page + 1
                    st.rerun()

            st.markdown("---")

            for s_res in search_results[start:end]:
                # Document Header Card
                with st.expander(f"📖 {s_res['library']} / {s_res['doc_id']} — Trovate {len(s_res['matches'])} pagine", expanded=True):

                    # Matches Grid
                    for m in s_res['matches']:
                        c_num, c_txt, c_act = st.columns([1, 6, 1])

                        # Snippet highlighting
                        text = m['full_text']
                        idx = text.lower().find(query.lower())
                        start = max(0, idx-60)
                        end = min(len(text), idx+60)
                        snippet = ("..." if start > 0 else "") + \
                            text[start:end].replace(query, f":red[**{query}**]") + ("..." if end < len(text) else "")

                        c_num.markdown(f"**Pag. {m['page_index']}**")
                        c_txt.markdown(f"_{snippet}_")

                        if c_act.button("Vai ➡️", key=f"go_{s_res['doc_id']}_{m['page_index']}"):
                            # State transfer to Studio
                            st.session_state["nav_override"] = "Studio"  # Matches SAC label
                            st.session_state["studio_doc_id"] = s_res['doc_id']
                            st.session_state["studio_library"] = s_res['library']
                            st.session_state["studio_page"] = m["page_index"]
                            st.rerun()
    else:
        st.markdown("""
        <div style="text-align: center; color: #666; padding: 3rem;">
            <h3>Inserisci una parola per iniziare</h3>
            <p>Il sistema cercherà in tutti i testi OCR salvati.</p>
        </div>
        """, unsafe_allow_html=True)
