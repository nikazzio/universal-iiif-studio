import streamlit as st
import os
import time
from PIL import Image as PILImage
from iiif_downloader.pdf_utils import load_pdf_page
from iiif_downloader.ui.components.viewer import interactive_viewer
from iiif_downloader.ui.state import get_storage
from .ocr_utils import run_ocr_sync

@st.cache_data(ttl=3600)
def get_manifest_thumbnails(manifest_url):
    """Fetch manifest and map canvas index to thumbnail URL."""
    try:
        from iiif_downloader.utils import get_json
        manifest = get_json(manifest_url)
        
        canvases = []
        if "sequences" in manifest and manifest["sequences"]:
             canvases = manifest["sequences"][0].get("canvases", [])
        elif "items" in manifest:
             canvases = manifest["items"]
             
        thumb_map = {}
        for i, c in enumerate(canvases):
            t = c.get("thumbnail")
            url = None
            if t:
                if isinstance(t, list): t = t[0]
                if isinstance(t, dict): url = t.get("@id") or t.get("id")
                elif isinstance(t, str): url = t
            thumb_map[i] = url
        return thumb_map
    except Exception:
        return {}

def render_main_canvas(doc_id, library, paths, stats=None, ocr_engine="openai", current_model="gpt-5"):
    st.title(f"🏛️ {doc_id}")
    
    storage = get_storage()
    meta = storage.load_metadata(doc_id, library)
    
    # Robust Page Counting
    total_pages = 100
    if meta and meta.get("pages"):
        total_pages = int(meta.get("pages"))
    else:
        pages_dir = paths["pages"]
        if os.path.exists(pages_dir):
            files = [f for f in os.listdir(pages_dir) if f.endswith(".jpg")]
            if files:
                total_pages = len(files)
    
    total_pages = max(1, total_pages)
    
    # --- PAGE NAVIGATION STATE ---
    if "current_page" not in st.session_state: st.session_state["current_page"] = 1
    
    # QUERY PARAM NAVIGATION (Handle before rendering components)
    q_page = st.query_params.get("page_nav")
    if q_page:
        try:
            target_p = int(q_page)
            if 1 <= target_p <= total_pages:
                st.session_state["current_page"] = target_p
                # Do NOT clear immediately if we want browser's back button to work naturally, 
                # but for Streamlit state management, we can clear to prevent sticky params.
                st.query_params.clear()
        except: pass

    # HOVER SCRUBBER (Below Title)
    has_pages = (stats and stats.get("pages")) or (meta and meta.get("pages")) or (paths.get("pages") and os.path.exists(paths["pages"]))
    if has_pages:
        thumb_source = {}
        # 1. Stats source (prioritize cached thumbnails)
        if stats and stats.get("pages"):
            for p in stats["pages"]:
                 url = p.get("thumbnail_url")
                 if not url and p.get("original_url"):
                     orig = p.get("original_url")
                     if "/full/" in orig:
                         parts = orig.split("/full/")
                         if len(parts) >= 2:
                             base = parts[0]
                             rest = parts[1].split("/", 1)[-1]
                             url = f"{base}/full/150,/{rest}"
                 if url: thumb_source[p["page_index"]-1] = url
        
        # 2. Manifest Fallback (Local then Live)
        if len(thumb_source) < total_pages: 
             local_manifest_path = os.path.join(paths["root"], "manifest.json")
             if os.path.exists(local_manifest_path):
                 try:
                     from iiif_downloader.utils import load_json
                     local_m = load_json(local_manifest_path)
                     canvases = []
                     if "sequences" in local_m and local_m["sequences"]: canvases = local_m["sequences"][0].get("canvases", [])
                     elif "items" in local_m: canvases = local_m["items"]
                     for idx, c in enumerate(canvases):
                        t = c.get("thumbnail")
                        url = None
                        if t:
                            if isinstance(t, list): t = t[0]
                            if isinstance(t, dict): url = t.get("@id") or t.get("id")
                            elif isinstance(t, str): url = t
                        if url and idx not in thumb_source: thumb_source[idx] = url
                 except: pass
             
             if not thumb_source and meta and meta.get("manifest_url"):
                 live_thumbs = get_manifest_thumbnails(meta.get("manifest_url"))
                 for idx, url in live_thumbs.items():
                     if idx not in thumb_source and url: thumb_source[idx] = url

    # --- CONTENT AREA ---
    col_img, col_txt = st.columns([1, 1])
    current_p = st.session_state["current_page"]
    
    with col_img:
        page_img_path = os.path.join(paths["root"], "pages", f"pag_{current_p-1:04d}.jpg")
        img_obj = None
        if os.path.exists(page_img_path):
            img_obj = PILImage.open(page_img_path)
        elif os.path.exists(paths["pdf"]):
            img_obj = load_pdf_page(paths["pdf"], current_p)

        # Calculate stats for the header
        stats_str = ""
        if img_obj:
            p_stat = None
            if stats:
                p_stat = next((p for p in stats.get("pages", []) if p.get("page_index") == current_p-1), None)
            
            if not p_stat:
                w, h = img_obj.size
                file_size = os.path.getsize(page_img_path) if os.path.exists(page_img_path) else 0
                p_stat = {"width": w, "height": h, "size_bytes": file_size}

            mb_size = p_stat['size_bytes'] / (1024*1024)
            stats_str = f"<span style='color: #888; font-size: 0.9rem; margin-left: 15px;'>📏 {p_stat['width']}×{p_stat['height']} px | 💾 {mb_size:.2f} MB</span>"

        st.markdown(f"### Scansione ({current_p}/{total_pages}) {stats_str}", unsafe_allow_html=True)
            
        if img_obj:
            interactive_viewer(img_obj, zoom_percent=100)
        else:
            st.error("Immagine non trovata.")

        # --- NAVIGATION BUTTONS (Experiment: below image) ---
        c_nav1, c_nav2, c_nav3 = st.columns([1, 2, 1])
        with c_nav1:
            if st.button("PREV ◀", use_container_width=True, key="btn_prev_sub"): 
                st.session_state["current_page"] = max(1, st.session_state["current_page"] - 1)
                st.rerun()
        with c_nav2:
             st.markdown(f"""
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;">
                    <span style="font-size: 1.4rem; font-weight: 800; color: #FF4B4B; line-height: 1;">{current_p} <span style="color: #444; font-weight: 300;">/ {total_pages}</span></span>
                </div>
            """, unsafe_allow_html=True)
        with c_nav3:
            if st.button("▶ NEXT", use_container_width=True, key="btn_next_sub"):
                st.session_state["current_page"] = min(total_pages, st.session_state["current_page"] + 1)
                st.rerun()

    with col_txt:
        render_transcription_editor(doc_id, library, current_p, ocr_engine, current_model)

    # --- NATIVE TIMELINE SLIDER (Bottom) ---
    st.markdown("<br>", unsafe_allow_html=True)
    c_line = st.slider("Timeline", 1, total_pages, value=st.session_state["current_page"], key="timeline_bottom")
    if c_line != st.session_state["current_page"]:
        st.session_state["current_page"] = c_line
        st.rerun()

def render_transcription_editor(doc_id, library, current_p, ocr_engine, current_model):
    storage = get_storage()
    trans = storage.load_transcription(doc_id, current_p, library)
    
    # INFO MESSAGE NEXT TO HEADER
    info_msg = ""
    if not trans:
        info_msg = " <span style='color: #888; font-size: 0.9rem; font-weight: normal; margin-left:10px;'>(Nessuna trascrizione: scrivi e salva per creare)</span>"
    
    st.markdown(f"### Trascrizione{info_msg}", unsafe_allow_html=True)
    
    if st.session_state.get("confirm_ocr_sync") == current_p:
         st.warning("⚠️ Testo esistente! Sovrascrivere?", icon="⚠️")
         c1, c2 = st.columns(2)
         if c1.button("Sì, Sovrascrivi", use_container_width=True, type="primary"):
             run_ocr_sync(doc_id, library, current_p, ocr_engine, current_model)
             st.session_state["confirm_ocr_sync"] = None
         if c2.button("No, Annulla", use_container_width=True):
             st.session_state["confirm_ocr_sync"] = None
             st.rerun()

    initial_text = trans.get("full_text", "") if trans else ""
    current_status = trans.get("status", "draft") if trans else "draft"
    is_manual = trans.get("is_manual", False) if trans else False
    original_ocr = trans.get("original_ocr_text") if trans else None
    
    edit_key = f"trans_editor_{doc_id}_{current_p}"
    text_val = st.text_area("Editor", value=initial_text, height=700, key=edit_key, label_visibility="collapsed")
    
    t_c1, t_c2, t_c3, t_c4 = st.columns([2, 2, 2, 1])
    is_dirty = text_val != initial_text
    
    with t_c1:
        if st.button("💾 Salva", use_container_width=True, type="primary" if is_dirty else "secondary"):
            new_data = {"full_text": text_val, "engine": trans.get("engine", "manual") if trans else "manual", "is_manual": True, "status": current_status, "average_confidence": 1.0}
            storage.save_transcription(doc_id, current_p, new_data, library)
            st.toast("✅ Modifiche salvate!", icon="💾")
            time.sleep(0.5)
            st.rerun()

    with t_c2:
        is_verified = current_status == "verified"
        btn_label = "✅ Verificato" if is_verified else "⚪ Da Verificare"
        if st.button(btn_label, use_container_width=True):
            new_status = "draft" if is_verified else "verified"
            data_to_save = trans if trans else {"full_text": "", "lines": [], "engine": "manual"}
            data_to_save["status"] = new_status
            data_to_save["is_manual"] = True 
            storage.save_transcription(doc_id, current_p, data_to_save, library)
            st.rerun()
            
    with t_c3:
        if st.button(f"⚡ {ocr_engine}", use_container_width=True):
             existing = storage.load_transcription(doc_id, current_p, library)
             if existing:
                 st.session_state["confirm_ocr_sync"] = current_p
                 st.rerun()
             else:
                 run_ocr_sync(doc_id, library, current_p, ocr_engine, current_model)

    with t_c4:
        if is_manual and original_ocr:
            if st.button("↩", use_container_width=True):
                revert_data = {"full_text": original_ocr, "engine": trans.get("original_engine", "unknown"), "is_manual": False, "status": "draft", "average_confidence": 0.0}
                storage.save_transcription(doc_id, current_p, revert_data, library)
                st.rerun()

    if trans:
        st.caption(f"Engine: {trans.get('engine')} | Conf: {trans.get('average_confidence', 'N/A')} | 🕒 {trans.get('timestamp', '-')}")
        if is_manual: st.caption("✍️ Modificato Manualmente")
