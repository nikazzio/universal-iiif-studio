import streamlit as st

from iiif_downloader.ui.state import get_storage


def render_search_page():
    st.title("🔍 Ricerca Globale")
    st.caption("Cerca parole o frasi in tutte le trascrizioni salvate nel tuo database locale.")
    
    storage = get_storage()
    
    # Central Search Bar
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        query = col1.text_input("Parola da cercare", placeholder="es. incarnatio, dante...", label_visibility="collapsed")
        search_btn = col2.button("🔎 Cerca", use_container_width=True, type="primary")

    if query and (search_btn or query):
        with st.spinner(f"Ricerca di '{query}' in corso..."):
            search_results = storage.search_manuscript(query)
            
        if not search_results: 
            st.info(f"Nessun risultato trovato per '{query}'.")
        else:
            st.subheader(f"Risultati ({len(search_results)} documenti)")
            st.markdown("---")
            
            for s_res in search_results:
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
                        snippet = ("..." if start > 0 else "") + text[start:end].replace(query, f":red[**{query}**]") + ("..." if end < len(text) else "")
                        
                        c_num.markdown(f"**Pag. {m['page_index']}**")
                        c_txt.markdown(f"_{snippet}_")
                        
                        if c_act.button("Vai ➡️", key=f"go_{s_res['doc_id']}_{m['page_index']}"):
                            # State transfer to Studio
                            st.session_state["nav_override"] = "Studio" # Matches SAC label
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
