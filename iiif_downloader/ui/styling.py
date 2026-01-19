import streamlit as st

from iiif_downloader.config_manager import get_config_manager


def load_custom_css():
    """Injects premium CSS styles."""
    cm = get_config_manager()
    theme_color = cm.get_setting("ui.theme_color", "#FF4B4B")

    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        /* Clean Sidebar */
        section[data-testid="stSidebar"] {{
            background-color: #1a1a1e;
            border-right: 1px solid #2d2d35;
        }}

        /* Primary Button Style */
        div.stButton > button:first-child {{
            background-color: {theme_color};
            color: white;
            border-radius: 8px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 600;
            transition: all 0.2s ease;
        }}
        div.stButton > button:first-child:hover {{
            opacity: 0.9;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }}

        /* Secondary/Outline Button */
        div.stButton > button:first-child:active {{
            transform: scale(0.98);
        }}

        /* Card Container (for Gallery) */
        .card-container {{
            background: #262730;
            border-radius: 12px;
            padding: 1rem;
            border: 1px solid rgba(255,255,255,0.05);
            transition: transform 0.2s;
            cursor: pointer;
            height: 100%;
        }}
        .card-container:hover {{
            transform: translateY(-4px);
            border-color: {theme_color};
            box-shadow: 0 10px 20px rgba(0,0,0,0.3);
        }}

        /* Metrics */
        [data-testid="stMetricValue"] {{
            font-size: 2rem;
            color: {theme_color};
        }}

        /* Headers */
        h1, h2, h3 {{
            letter-spacing: -0.5px;
        }}

        /* Expander */
        .streamlit-expanderHeader {{
            background-color: #262730;
            border-radius: 8px;
        }}

        /* --- Select / Multiselect dropdown readability (BaseWeb) --- */
        /* Control */
        div[data-baseweb="select"] > div {{
            background-color: var(--st-color-surface, #ffffff) !important;
            color: var(--st-color-text, #111111) !important;
            border: 1px solid var(--st-color-border, rgba(0, 0, 0, 0.2)) !important;
            border-radius: 10px !important;
        }}

        /* Focus ring */
        div[data-baseweb="select"] > div:focus-within {{
            box-shadow: 0 0 0 3px rgba(255, 75, 75, 0.18) !important;
            border-color: {theme_color} !important;
        }}

        /* Dropdown menu container */
        div[role="listbox"] {{
            background-color: var(--st-color-surface, #ffffff) !important;
            color: var(--st-color-text, #111111) !important;
            border: 1px solid var(--st-color-border, rgba(0, 0, 0, 0.2)) !important;
            box-shadow: 0 10px 26px rgba(0,0,0,0.25) !important;
            border-radius: 10px !important;
            overflow: hidden !important;
        }}

        /* Options */
        div[role="option"] {{
            color: var(--st-color-text, #111111) !important;
        }}
        div[role="option"]:hover {{
            background-color: rgba(255, 75, 75, 0.12) !important;
        }}
        div[role="option"][aria-selected="true"] {{
            background-color: rgba(255, 75, 75, 0.18) !important;
        }}

        /* Custom Scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: #1a1a1e;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #444;
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #555;
        }}

    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_gallery_card(title, subtitle, image_url=None, footer=None, key=None):
    """
    Renders a clickable card.
    NOTE: Streamlit doesn't support clickable custom HTML divs that trigger python events easily.
    We use a workaround: The Card is visual, and a transparent button covers it,
    OR we design the container to look like a card and put a "Select" button inside.

    Approach B (Native): Container with styling + Button.
    """
    # These are reserved for future UI variants (overlay button / keyed widgets).
    _ = footer, key
    with st.container():
        st.markdown(
            f"""
        <div class="card-container">
            <div style="height: 140px; background-color: #333; border-radius: 8px; margin-bottom: 12px; display: flex; align-items: center; justify-content: center; overflow: hidden;">
                {f'<img src="{image_url}" style="width: 100%; height: 100%; object-fit: cover;">' if image_url else '<span style="font-size: 3rem;">📜</span>'}
            </div>
            <h4 style="margin: 0; font-size: 1rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{title}</h4>
            <p style="color: #aaa; font-size: 0.8rem; margin: 4px 0 12px 0;">{subtitle}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        # The actual interaction must be a button below or overlay
        # We'll expect the caller to place a button here
