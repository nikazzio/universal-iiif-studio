import streamlit as st

import iiif_downloader

# Initialize Config & State first
from iiif_downloader.config_manager import get_config_manager
from iiif_downloader.ui.components.settings_panel import render_settings_page

# Page Modules
from iiif_downloader.ui.discovery import render_discovery_page
from iiif_downloader.ui.pages.export_studio import render_export_studio_page
from iiif_downloader.ui.pages.studio_page import render_studio_page
from iiif_downloader.ui.search import render_search_page
from iiif_downloader.ui.state import init_session_state
from iiif_downloader.ui.styling import load_custom_css
from iiif_downloader.utils import cleanup_old_files


def main():
    # 1. Base Setup
    st.set_page_config(
        layout="wide",
        page_title="Universal IIIF Studio",
        page_icon="📜",
        initial_sidebar_state="expanded",
    )

    # Load user-local config.json early
    cm = get_config_manager()

    # Ensure key directories exist (portability)
    try:
        cm.get_downloads_dir().mkdir(parents=True, exist_ok=True)
        cm.get_temp_dir().mkdir(parents=True, exist_ok=True)
        cm.get_models_dir().mkdir(parents=True, exist_ok=True)
        cm.get_logs_dir().mkdir(parents=True, exist_ok=True)
    except OSError:
        # If not writable, UI will still run; downloads may fail later.
        pass

    # Housekeeping: remove temp files older than N days (configurable)
    try:
        cleanup_days = int(cm.get_setting("housekeeping.temp_cleanup_days", 7) or 7)
        cleanup_days = max(1, min(cleanup_days, 30))
        cleanup_old_files(cm.get_temp_dir(), older_than_days=cleanup_days)
    except OSError:
        # Never block the UI for cleanup failures.
        pass

    init_session_state()
    load_custom_css()

    # 2. Sidebar Navigation
    import streamlit_antd_components as sac

    with st.sidebar:
        st.title("🏛️ IIIF Studio")
        st.caption(f"v{getattr(iiif_downloader, '__version__', '0.0.0')}")

        # Determine default index
        default_idx = 0
        nav_override = st.session_state.get("nav_override")
        if nav_override:
            mapping = {
                "Discovery": 0,
                "Studio": 1,
                "Export Studio": 2,
                "Ricerca Globale": 3,
                "Impostazioni": 4,
            }
            default_idx = mapping.get(nav_override, 0)
            st.session_state["nav_override"] = None  # Reset

        app_mode = sac.menu(
            [
                sac.MenuItem(
                    "Discovery",
                    icon="compass",
                    description="Cerca e Scarica",
                ),
                sac.MenuItem(
                    "Studio",
                    icon="easel",
                    description="Leggi e Correggi",
                ),
                sac.MenuItem(
                    "Export Studio",
                    icon="filetype-pdf",
                    description="PDF professionali",
                ),
                sac.MenuItem(
                    "Ricerca Globale",
                    icon="search",
                    description="Cerca nei testi",
                ),
                sac.MenuItem(
                    "Impostazioni",
                    icon="gear",
                    description="Configura l'app",
                ),
            ],
            index=default_idx,
            format_func="title",
            open_all=True,
        )

    st.sidebar.markdown("---")

    # 3. Routing
    if app_mode == "Discovery":
        render_discovery_page()
    elif app_mode == "Studio":
        render_studio_page()
    elif app_mode == "Export Studio":
        render_export_studio_page()
    elif app_mode == "Ricerca Globale":
        render_search_page()
    elif app_mode == "Impostazioni":
        render_settings_page(cm)

    # 4. Global Footer / Debug
    with st.sidebar.expander("🛠️ Debug & Config"):
        st.write("Local config (config.json):", cm.data)
        if st.checkbox("Show Session State"):
            st.write(st.session_state)


if __name__ == "__main__":
    main()
