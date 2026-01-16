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
    st.sidebar.title("🏛️ IIIF Studio")
    st.sidebar.caption("v3.0.0 (Agentic)")
    st.sidebar.markdown("---")
    
    # Handle state-based navigation override (e.g. from Search -> Studio)
    if "nav_override" in st.session_state and st.session_state["nav_override"]:
        default_idx = ["🛰️ Discovery", "🏛️ Studio", "🔍 Ricerca Globale"].index(st.session_state["nav_override"])
        st.session_state["nav_override"] = None # Reset
    else:
        default_idx = 0
        
    app_mode = st.sidebar.radio(
        "Navigazione",
        ["🛰️ Discovery", "🏛️ Studio", "🔍 Ricerca Globale"],
        index=default_idx
    )
    
    st.sidebar.markdown("---")

    # 3. Routing
    if app_mode == "🛰️ Discovery":
        render_discovery_page()
    elif app_mode == "🏛️ Studio":
        render_studio_page()
    elif app_mode == "🔍 Ricerca Globale":
        render_search_page()
    
    # 4. Global Footer / Debug
    with st.sidebar.expander("🛠️ Debug & Config"):
        st.write("Config loaded:", config.config)
        if st.checkbox("Show Session State"):
            st.write(st.session_state)

if __name__ == "__main__":
    main()
