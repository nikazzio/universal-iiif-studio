import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
import os
import time

# Modular Imports
from iiif_downloader.ocr.model_manager import ModelManager
from iiif_downloader.ocr.processor import OCRProcessor, KRAKEN_AVAILABLE, KRAKEN_IMPORT_ERROR
from iiif_downloader.ocr.storage import OCRStorage
from iiif_downloader.pdf_utils import load_pdf_page
from PIL import Image as PILImage # For direct image loading
from iiif_downloader.ui.components import inject_premium_styles, interactive_viewer
from iiif_downloader.resolvers.discovery import resolve_shelfmark, search_gallica, search_oxford
from iiif_downloader.core import IIIFDownloader

# Load environment variables
load_dotenv()

# --- Configuration & State ---
st.set_page_config(layout="wide", page_title="Universal IIIF Studio", page_icon="📜")
inject_premium_styles()

# Helper accessors
@st.cache_resource
def get_model_manager():
    return ModelManager()

@st.cache_resource
def get_ocr_storage():
    return OCRStorage()

def get_ocr_processor(model_path=None, **keys):
    return OCRProcessor(model_path, **keys)

manager = get_model_manager()
storage = get_ocr_storage()

# Auto-migrate on startup
if "migrated" not in st.session_state:
    storage.migrate_legacy()
    st.session_state["migrated"] = True

if "ocr_result" not in st.session_state:
    st.session_state["ocr_result"] = None
if "last_ocr_page" not in st.session_state:
    st.session_state["last_ocr_page"] = None
if "discovery_preview" not in st.session_state:
    st.session_state["discovery_preview"] = None
if "search_results" not in st.session_state:
    st.session_state["search_results"] = []

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🏛️ IIIF Studio")
st.sidebar.markdown("---")

app_mode = st.sidebar.radio(
    "Navigazione",
    ["🛰️ Discovery", "🏛️ Studio", "🔍 Ricerca Globale"],
)

st.sidebar.markdown("---")

# --- AREA 1: DISCOVERY ---
if app_mode == "🛰️ Discovery":
    st.title("🛰️ Discovery & Download")
    
    col_lib, col_input = st.sidebar.columns([1, 1]) # Keep these small in sidebar if needed, or in main? 
    # User said "tabs in the sidebar menu", let's put the sub-controls in sidebar
    
    st.sidebar.subheader("Configurazione")
    lib_choice = st.sidebar.selectbox("Biblioteca", ["Vaticana (BAV)", "Gallica (BnF)", "Bodleian (Oxford)", "Altro"])
    lib_map = {"Vaticana (BAV)": "Vaticana", "Gallica (BnF)": "Gallica", "Bodleian (Oxford)": "Bodleian", "Altro": "Unknown"}
    active_lib = lib_map.get(lib_choice, "Unknown")

    mode_options = ["Segnatura / URL"]
    # Only Gallica has a working search API
    if lib_choice == "Gallica (BnF)":
        mode_options.append("Cerca nel Catalogo")
    disc_mode = st.sidebar.radio("Metodo", mode_options, horizontal=True)

    if disc_mode == "Segnatura / URL":
        shelf_input = st.sidebar.text_input("ID o URL", placeholder="es. Urb.lat.1779")
        if st.sidebar.button("🔍 Analizza", use_container_width=True):
            if shelf_input:
                with st.spinner("Analisi in corso..."):
                    manifest_url, doc_id_hint = resolve_shelfmark(lib_choice, shelf_input)
                    if manifest_url:
                        from iiif_downloader.utils import get_json
                        try:
                            m = get_json(manifest_url)
                            label = m.get("label", "Senza Titolo")
                            if isinstance(label, list): label = label[0]
                            desc = m.get("description", "")
                            if isinstance(desc, list): desc = desc[0]
                            canvases = m.get("sequences", [{}])[0].get("canvases", []) or m.get("items", [])
                            # Calculate official viewer URL
                            viewer_url = None
                            if active_lib == "Vaticana":
                                viewer_url = f"https://digi.vatlib.it/view/{doc_id_hint}"
                            elif active_lib == "Gallica":
                                ark_id = manifest_url.replace("https://gallica.bnf.fr/iiif/", "").replace("/manifest.json", "")
                                viewer_url = f"https://gallica.bnf.fr/{ark_id}"
                            elif active_lib == "Bodleian":
                                viewer_url = f"https://digital.bodleian.ox.ac.uk/objects/{doc_id_hint}/"

                            st.session_state["discovery_preview"] = {
                                "url": manifest_url, "id": doc_id_hint, "label": str(label),
                                "library": active_lib, "description": str(desc)[:500], "pages": len(canvases),
                                "viewer_url": viewer_url
                            }
                        except Exception as e: st.error(f"Errore analisi: {e}")
                    else: st.warning(doc_id_hint or "ID non risolvibile.")

    else:
        search_query = st.sidebar.text_input("Parola chiave", placeholder="es. Dante")
        if st.sidebar.button("🔎 Cerca", use_container_width=True):
            if search_query:
                with st.spinner("Ricerca in corso..."):
                    # Only Gallica search is currently supported
                    st.session_state["search_results"] = search_gallica(search_query)

    # Main Area for Discovery
    if st.session_state["search_results"]:
        st.subheader("Risultati Ricerca")
        for res in st.session_state["search_results"]:
            with st.container():
                col_t, col_b = st.columns([4, 1])
                col_t.markdown(f"**{res['title']}**")
                col_t.caption(f"ID: {res['id']}")
                if col_b.button("Seleziona", key=f"sel_{res['id']}"):
                    # Logic for search result selection
                    try:
                        from iiif_downloader.utils import get_json
                        m = get_json(res["manifest_url"])
                        canvases = m.get("sequences", [{}])[0].get("canvases", []) or m.get("items", [])
                        
                        viewer_url = None
                        if active_lib == "Gallica": viewer_url = f"https://gallica.bnf.fr/ark:/12148/{res['id']}"
                        elif active_lib == "Bodleian": viewer_url = f"https://digital.bodleian.ox.ac.uk/objects/{res['id']}/"

                        st.session_state["discovery_preview"] = {
                            "url": res["manifest_url"], "id": res["id"], "label": res["title"],
                            "library": active_lib, "description": "", "pages": len(canvases),
                            "viewer_url": viewer_url
                        }
                    except: pass
                    st.session_state["search_results"] = []
                    st.rerun()

    preview = st.session_state.get("discovery_preview")
    if preview:
        st.markdown("---")
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown(f"### 📖 {preview['label']}")
            st.caption(f"ID: {preview['id']} | Library: {preview['library']} | Pages: {preview['pages']}")
            if preview.get('description'): st.info(preview['description'])
            if preview.get('viewer_url'):
                st.link_button("🌐 Apri Viewer Ufficiale", preview['viewer_url'], help="Apri il viewer della biblioteca in una nuova scheda", use_container_width=False)
        with c2:
            st.markdown("#### Azioni")
            if st.button("🚀 Avvia Download", type="primary", use_container_width=True):
                progress_bar = st.progress(0, text="Inizializzazione...")
                def hook(curr, total): progress_bar.progress(curr/total, text=f"Scaricamento: {curr}/{total}")
                downloader = IIIFDownloader(manifest_url=preview["url"], output_name=preview["id"], library=preview["library"], progress_callback=hook, skip_pdf=True)
                with st.spinner("Connessione e Download..."):
                    try:
                        downloader.run()
                        st.success(f"Completato in {preview['library']}/{preview['id']}")
                        st.session_state["discovery_preview"] = None
                        st.rerun()
                    except Exception as e: st.error(f"Errore download: {e}")
            if st.button("🗑️ Reset", use_container_width=True):
                st.session_state["discovery_preview"] = None
                st.session_state["search_results"] = []
                st.rerun()
    elif not st.session_state["search_results"]:
        st.info("Utilizza il menu a sinistra per cercare o inserire un URL IIIF.")

# --- AREA 2: STUDIO ---
elif app_mode == "🏛️ Studio":
    docs = storage.list_documents()
    if not docs:
        st.title("🏛️ Studio")
        st.info("Nessun documento scaricato. Vai alla sezione 'Discovery' per iniziare.")
    else:
        # Sidebar Controls for Studio
        st.sidebar.subheader("Selezione Documento")
        doc_labels = [f"{d['library']} / {d['id']}" for d in docs]
        selected_label = st.sidebar.selectbox("Manoscritto", doc_labels)
        selected_doc = next(d for d in docs if f"{d['library']} / {d['id']}" == selected_label)
        selected_doc_id, selected_lib = selected_doc["id"], selected_doc["library"]
        paths = storage.get_document_paths(selected_doc_id, selected_lib)
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("Esportazione")
        if os.path.exists(paths["pdf"]):
            st.sidebar.success("✅ PDF Disponibile")
            with open(paths["pdf"], "rb") as f: 
                st.sidebar.download_button("📥 Scarica PDF", f, file_name=f"{selected_doc_id}.pdf", use_container_width=True)
        if st.sidebar.button("📄 Genera/Aggiorna PDF", use_container_width=True):
            from iiif_downloader.core import IIIFDownloader
            with st.status("Generazione PDF...", expanded=True) as status:
                meta = storage.load_metadata(selected_doc_id, selected_lib)
                if meta and meta.get("manifest_url"):
                    d = IIIFDownloader(manifest_url=meta["manifest_url"], output_name=selected_doc_id, library=selected_lib, skip_pdf=False)
                    d.create_pdf()
                    status.update(label="PDF Generato!", state="complete"); st.rerun()
                else: st.error("Metadati mancanti.")
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("OCR Settings")
        ocr_engine = st.sidebar.selectbox("Motore", ["kraken", "openai", "anthropic", "google", "huggingface"])
        current_model = None
        if ocr_engine == "kraken":
            installed = manager.list_installed_models()
            current_model = st.sidebar.selectbox("Modello HTR", installed)
        force_ocr = st.sidebar.checkbox("Riesegui OCR", value=False)
        api_key_env = {"openai": os.getenv("OPENAI_API_KEY", ""), "anthropic": os.getenv("ANTHROPIC_API_KEY", ""), "google": os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""), "huggingface": os.getenv("HF_TOKEN", "")}
        user_key = st.sidebar.text_input(f"Chiave {ocr_engine.capitalize()}", value=api_key_env.get(ocr_engine, ""), type="password") if ocr_engine != "kraken" else ""

        # Main Area for Studio
        st.title(f"🏛️ Studio: {selected_doc_id}")
        meta = storage.load_metadata(selected_doc_id, selected_lib)
        total_pages = int(meta.get("pages", 100)) if meta else 100
        page_default = st.session_state.pop("page_idx_override") if "page_idx_override" in st.session_state else 1
        
        col_p1, col_p2 = st.columns([4, 1])
        page = col_p1.slider("Navigazione Pagine", 1, total_pages, page_default)
        col_p2.metric("Pagina", f"{page} / {total_pages}")
        
        st.markdown("---")
        col_img, col_txt = st.columns([1, 1])
        with col_img:
            page_img_path = os.path.join(paths["root"], "pages", f"pag_{page-1:04d}.jpg")
            page_image, page_err = (PILImage.open(page_img_path), None) if os.path.exists(page_img_path) else load_pdf_page(paths["pdf"], page)
            if page_image:
                interactive_viewer(page_image)
                st.caption("Usa lo slider (se presente) o il mouse per navigare i dettagli.")
            else: st.error(page_err or "Impossibile caricare la pagina.")
        
        with col_txt:
            st.subheader("Trascrizione & Analisi")
            cached_trans = storage.load_transcription(selected_doc_id, page, library=selected_lib)
            if cached_trans and not force_ocr: st.session_state["ocr_result"] = cached_trans
            elif (st.session_state["last_ocr_page"] != (selected_doc_id, page)) or force_ocr:
                if page_image:
                    with st.spinner(f"Elaborazione OCR ({ocr_engine})..."):
                        proc = get_ocr_processor(model_path=manager.get_model_path(current_model) if ocr_engine == "kraken" else None, openai_api_key=user_key if ocr_engine == "openai" else None, anthropic_api_key=user_key if ocr_engine == "anthropic" else None, hf_token=user_key if ocr_engine == "huggingface" else None)
                        result = proc.process_page(page_image, engine=ocr_engine)
                        if "error" not in result:
                            result["engine"] = ocr_engine
                            storage.save_transcription(selected_doc_id, page, result, library=selected_lib)
                            st.session_state["ocr_result"] = result
                            st.session_state["last_ocr_page"] = (selected_doc_id, page)
                        else: st.error(f"Errore OCR: {result['error']}")
            
            if st.session_state["ocr_result"]:
                res = st.session_state["ocr_result"]
                st.text_area("Testo Estratto", res.get("full_text", ""), height=500)
                st.caption(f"Motore: {res.get('engine', 'N/D')} | Aggiornato: {res.get('timestamp', 'N/D')}")

# --- AREA 3: RICERCA GLOBALE ---
elif app_mode == "🔍 Ricerca Globale":
    st.title("🔍 Ricerca Globale")
    st.sidebar.subheader("Parametri Ricerca")
    query = st.sidebar.text_input("Parola da cercare", placeholder="es. incarnatio")
    
    if query:
        search_results = storage.search_manuscript(query)
        if not search_results: 
            st.warning(f"Nessun risultato trovato per '{query}'.")
        else:
            st.success(f"Trovate occorrenze in {len(search_results)} manoscritti.")
            for s_res in search_results:
                with st.expander(f"📖 {s_res['library']} / {s_res['doc_id']} ({len(s_res['matches'])} occorrenze)"):
                    for m in s_res['matches']:
                        col_m1, col_m2 = st.columns([4, 1])
                        col_m1.markdown(f"**Pagina {m['page_index']}**")
                        text = m['full_text']; idx = text.lower().find(query.lower())
                        snippet = ("..." if idx > 50 else "") + text[max(0, idx-50):min(len(text), idx+50)] + ("..." if idx+50 < len(text) else "")
                        col_m1.caption(f"Snippet: {snippet}")
                        if col_m2.button("Vai allo Studio", key=f"go_{s_res['doc_id']}_{m['page_index']}"):
                            st.session_state["page_idx_override"] = m["page_index"]
                            st.session_state["doc_selector_id"] = f"{s_res['library']} / {s_res['doc_id']}" # We'd need to sync this with selectbox
                            st.info("Reindirizzamento allo Studio...")
                            # Note: To fully sync the selectbox, we would need to set its default to this in the radio logic
    else:
        st.info("Inserisci una parola nel menu a sinistra per cercare in tutte le tue trascrizioni salvate.")

st.sidebar.markdown("---")
st.sidebar.caption("Universal IIIF Studio v2.6")
st.sidebar.caption("Redesigned Sidebar UX")
