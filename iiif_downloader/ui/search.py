import streamlit as st
from iiif_downloader.ui.state import get_storage

def render_search_page():
    st.title("🔍 Ricerca Globale")
    
    storage = get_storage()
    
    st.sidebar.subheader("Parametri Ricerca")
    query = st.sidebar.text_input("Parola da cercare", placeholder="es. incarnatio")
    
    if query:
        search_results = storage.search_manuscript(query)
        if not search_results: 
            st.info(f"Nessun risultato trovato per '{query}'.")
        else:
            st.success(f"Trovate occorrenze in {len(search_results)} manoscritti.")
            
            for s_res in search_results:
                with st.expander(f"📖 {s_res['library']} / {s_res['doc_id']} ({len(s_res['matches'])} occorrenze)"):
                    for m in s_res['matches']:
                        col_m1, col_m2 = st.columns([4, 1])
                        
                        # Snippet highlighting
                        text = m['full_text']
                        idx = text.lower().find(query.lower())
                        start = max(0, idx-50)
                        end = min(len(text), idx+50)
                        snippet = ("..." if start > 0 else "") + text[start:end].replace(query, f"**{query}**") + ("..." if end < len(text) else "")
                        
                        col_m1.markdown(f"**Pagina {m['page_index']}**: {snippet}")
                        
                        if col_m2.button("Vai", key=f"go_{s_res['doc_id']}_{m['page_index']}"):
                            # State transfer to Studio
                            st.session_state["nav_override"] = "🏛️ Studio"
                            st.session_state["studio_doc_id"] = s_res['doc_id']
                            st.session_state["studio_library"] = s_res['library']
                            st.session_state["studio_page"] = m["page_index"]
                            st.rerun()
    else:
        st.markdown("""
        <div style="text-align: center; color: #666; padding: 4rem;">
            <h3>Inserisci una parola per cercare</h3>
            <p>Cerca in tutte le trascrizioni salvate nel database locale.</p>
        </div>
        """, unsafe_allow_html=True)
