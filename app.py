import streamlit as st
from dotenv import load_dotenv

# Initialize Config & State first
from iiif_downloader.config import config
from iiif_downloader.ui.state import init_session_state
from iiif_downloader.ui.styling import load_custom_css
from iiif_downloader.logger import get_logger

# Page Modules
from iiif_downloader.ui.discovery import render_discovery_page
from iiif_downloader.ui.studio import render_studio_page
from iiif_downloader.ui.search import render_search_page

def main():
    # 1. Base Setup
    st.set_page_config(
        layout="wide", 
        page_title="Universal IIIF Studio", 
        page_icon="📜",
        initial_sidebar_state="expanded"
    )
    load_dotenv()
    init_session_state()
    load_custom_css()
    
    # 2. Sidebar Navigation
    import streamlit_antd_components as sac
    
    with st.sidebar:
        st.title("🏛️ IIIF Studio")
        st.caption("v3.1.0 (Agentic)")
        
        # Determine default index
        default_idx = 0
        if "nav_override" in st.session_state and st.session_state["nav_override"]:
            mapping = {"Discovery": 0, "Studio": 1, "Ricerca Globale": 2}
            default_idx = mapping.get(st.session_state["nav_override"], 0)
            st.session_state["nav_override"] = None # Reset
            
        app_mode = sac.menu([
            sac.MenuItem('Discovery', icon='compass', description='Cerca e Scarica'),
            sac.MenuItem('Studio', icon='easel', description='Leggi e Correggi'),
            sac.MenuItem('Ricerca Globale', icon='search', description='Cerca nei testi'),
        ], index=default_idx, format_func='title', open_all=True)
        
    st.sidebar.markdown("---")

    # 3. Routing
    if app_mode == 'Discovery':
        render_discovery_page()
    elif app_mode == 'Studio':
        render_studio_page()
    elif app_mode == 'Ricerca Globale':
        render_search_page()
    
    # 4. Global Footer / Debug
    with st.sidebar.expander("🛠️ Debug & Config"):
        st.write("Config loaded:", config.config)
        if st.checkbox("Show Session State"):
            st.write(st.session_state)

if __name__ == "__main__":
    main()
