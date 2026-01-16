import streamlit as st
import time
from iiif_downloader.resolvers.discovery import resolve_shelfmark, search_gallica, search_oxford
from iiif_downloader.core import IIIFDownloader
from iiif_downloader.utils import get_json
from iiif_downloader.ui.state import init_session_state
from iiif_downloader.ui.styling import render_gallery_card
from iiif_downloader.config import config

def render_discovery_page():
    st.title("🛰️ Discovery & Download")
    
    # --- Sidebar Controls ---
    st.sidebar.subheader("Configurazione Ricerca")
    
    user_default_lib = config.get("defaults", "default_library", "Vaticana (BAV)")
    lib_choice = st.sidebar.selectbox("Biblioteca", ["Vaticana (BAV)", "Gallica (BnF)", "Bodleian (Oxford)", "Altro"], index=0)
    
    lib_map = {"Vaticana (BAV)": "Vaticana", "Gallica (BnF)": "Gallica", "Bodleian (Oxford)": "Bodleian", "Altro": "Unknown"}
    active_lib = lib_map.get(lib_choice, "Unknown")

    mode_options = ["Segnatura / URL"]
    if lib_choice == "Gallica (BnF)":
        mode_options.append("Cerca nel Catalogo")
    
    disc_mode = st.sidebar.radio("Metodo", mode_options, horizontal=True)

    # --- ACTION AREA ---
    if disc_mode == "Segnatura / URL":
        render_url_input(active_lib, lib_choice)
    else:
        render_catalog_search(active_lib)

    # --- PREVIEW AREA ---
    preview = st.session_state.get("discovery_preview")
    if preview:
        render_preview(preview)

def render_url_input(active_lib, lib_choice):
    placeholders = {
        "Vaticana": "es. Urb.lat.1779",
        "Gallica": "es. btv1b10033406t o bpt6k9761787t",
        "Bodleian": "es. 080f88f5-7586-4b8a-8064-63ab3495393c",
        "Unknown": "Inserisci ID o URL"
    }
    
    shelf_input = st.sidebar.text_input("ID o URL", placeholder=placeholders.get(active_lib, "Inserisci ID o URL"))
    
    if st.sidebar.button("🔍 Analizza", use_container_width=True):
        if shelf_input:
            with st.spinner("Analisi in corso..."):
                manifest_url, doc_id_hint = resolve_shelfmark(lib_choice, shelf_input)
                if manifest_url:
                    analyze_manifest(manifest_url, doc_id_hint, active_lib)
                else:
                    st.toast(doc_id_hint or "ID non risolvibile", icon="⚠️")

def render_catalog_search(active_lib):
    query = st.sidebar.text_input("Parola chiave", placeholder="es. Dante")
    if st.sidebar.button("🔎 Cerca", use_container_width=True) and query:
        with st.spinner("Ricerca in corso..."):
            st.session_state["search_results"] = search_gallica(query)

    # Gallery View
    results = st.session_state.get("search_results", [])
    if results:
        st.subheader(f"Risultati Ricerca ({len(results)})")
        
        # Grid Layout
        cols = st.columns(4)
        for i, res in enumerate(results):
            with cols[i % 4]:
                render_gallery_card(
                    title=res['title'], 
                    subtitle=res['id'], 
                    image_url=res.get("preview_url")
                )
                if st.button("Seleziona", key=f"sel_{res['id']}"):
                     analyze_manifest(res["manifest_url"], res["id"], active_lib)

def analyze_manifest(manifest_url, doc_id, library):
    try:
        m = get_json(manifest_url)
        label = m.get("label", "Senza Titolo")
        if isinstance(label, list): label = label[0]
        desc = m.get("description", "")
        if isinstance(desc, list): desc = desc[0]
        
        # IIIF v2/v3 compatibility
        canvases = []
        if 'sequences' in m:
            canvases = m['sequences'][0].get('canvases', [])
        elif 'items' in m:
            canvases = m['items']

        st.session_state["discovery_preview"] = {
            "url": manifest_url, 
            "id": doc_id, 
            "label": str(label),
            "library": library, 
            "description": str(desc)[:500], 
            "pages": len(canvases),
            "viewer_url": get_viewer_url(library, doc_id, manifest_url)
        }
        st.toast("Manifest analizzato con successo!", icon="✅")
    except Exception as e:
        st.error(f"Errore analisi: {e}")

def get_viewer_url(lib, doc_id, manifest_url):
    if lib == "Vaticana": return f"https://digi.vatlib.it/view/{doc_id}"
    if lib == "Gallica": 
        ark = manifest_url.split("/iiif/")[1].replace("/manifest.json", "")
        return f"https://gallica.bnf.fr/{ark}"
    if lib == "Bodleian": return f"https://digital.bodleian.ox.ac.uk/objects/{doc_id}/"
    return manifest_url

def render_preview(preview):
    st.markdown("---")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown(f"### 📖 {preview['label']}")
        st.caption(f"ID: {preview['id']} | Library: {preview['library']} | Pages: {preview['pages']}")
        if preview.get('description'): st.info(preview['description'])
        if preview.get('viewer_url'):
            st.link_button("🌐 Apri Viewer Ufficiale", preview['viewer_url'])
            
    with c2:
        st.markdown("#### Azioni")
        if st.button("🚀 Avvia Download", type="primary", use_container_width=True):
            start_download_process(preview)
            
        if st.button("🗑️ Reset", use_container_width=True):
            st.session_state["discovery_preview"] = None
            st.rerun()

def start_download_process(preview):
    progress_bar = st.progress(0, text="Inizializzazione...")
    status_text = st.empty()
    
    def hook(curr, total): 
        progress_bar.progress(curr/total)
        status_text.text(f"Scaricamento: {curr}/{total}")

    downloader = IIIFDownloader(
        manifest_url=preview["url"], 
        output_name=preview["id"], 
        library=preview["library"], 
        progress_callback=hook, 
        skip_pdf=not config.get("defaults", "auto_generate_pdf", True),
        workers=config.get("system", "download_workers", 4)
    )
    
    with st.spinner("Connessione e Download..."):
        try:
            downloader.run()
            st.toast(f"Completato! {preview['id']} scaricato.", icon="🎉")
            time.sleep(1)
            # Optionally redirect to studio
            st.session_state["discovery_preview"] = None
            st.rerun()
        except Exception as e:
             st.error(f"Errore download: {e}")
