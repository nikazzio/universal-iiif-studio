import os
import time

import streamlit as st
from PIL import Image as PILImage
from requests import RequestException

from iiif_downloader.logger import get_logger
from iiif_downloader.pdf_utils import load_pdf_page
from iiif_downloader.ui.components.viewer import interactive_viewer
from iiif_downloader.ui.state import get_storage
from iiif_downloader.ui.notifications import toast

from .ocr_utils import run_ocr_sync

logger = get_logger(__name__)


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
                if isinstance(t, list):
                    t = t[0]
                if isinstance(t, dict):
                    url = t.get("@id") or t.get("id")
                elif isinstance(t, str):
                    url = t
            thumb_map[i] = url
        return thumb_map
    except (RequestException, ValueError, KeyError, IndexError, TypeError):
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
        scans_dir = paths["scans"]
        if os.path.exists(scans_dir):
            files = [f for f in os.listdir(scans_dir) if f.endswith(".jpg")]
            if files:
                total_pages = len(files)

    total_pages = max(1, total_pages)

    # --- PAGE NAVIGATION STATE (Document-Specific) ---
    page_key = f"page_{doc_id}"

    # Initialize per-document state if missing
    if page_key not in st.session_state:
        # Default to 1 for new documents to prevent "leaking" page from previous doc
        st.session_state[page_key] = 1

    # QUERY PARAM NAVIGATION (Handles direct links/bookmarks)
    q_page = st.query_params.get("page_nav")
    if q_page:
        try:
            target_p = int(q_page)
            if 1 <= target_p <= total_pages:
                st.session_state[page_key] = target_p
                st.session_state["current_page"] = target_p
                # Clear all query params to prevent sticky behavior on saves/reruns
                for k in list(st.query_params.keys()):
                    del st.query_params[k]
        except (TypeError, ValueError):
            logger.debug("Invalid page_nav query param: %r", q_page)

    current_p = st.session_state[page_key]

    # HOVER SCRUBBER (Below Title)
    has_pages = (
        (stats and stats.get("pages"))
        or (meta and meta.get("pages"))
        or (paths.get("scans") and os.path.exists(paths["scans"]))
    )
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
                if url:
                    thumb_source[p["page_index"] - 1] = url

        # 2. Manifest Fallback (Local then Live)
        if len(thumb_source) < total_pages:
            from pathlib import Path

            local_manifest_path = Path(paths["root"]) / "manifest.json"
            if local_manifest_path.exists():
                try:
                    from iiif_downloader.utils import load_json

                    local_m = load_json(local_manifest_path)
                    canvases = []
                    if "sequences" in local_m and local_m["sequences"]:
                        canvases = local_m["sequences"][0].get("canvases", [])
                    elif "items" in local_m:
                        canvases = local_m["items"]

                    for idx, c in enumerate(canvases):
                        t = c.get("thumbnail")
                        url = None
                        if t:
                            if isinstance(t, list):
                                t = t[0]
                            if isinstance(t, dict):
                                url = t.get("@id") or t.get("id")
                            elif isinstance(t, str):
                                url = t
                        if url and idx not in thumb_source:
                            thumb_source[idx] = url
                except (OSError, ValueError, KeyError, IndexError, TypeError):
                    logger.exception("Failed to load local manifest thumbnails")

            if not thumb_source and meta and meta.get("manifest_url"):
                live_thumbs = get_manifest_thumbnails(meta.get("manifest_url"))
                for idx, url in live_thumbs.items():
                    if idx not in thumb_source and url:
                        thumb_source[idx] = url

    # --- CONTENT AREA ---
    # --- CONTENT AREA ---
    show_history = st.session_state.get("show_history", False)

    if show_history:
        col_img, col_txt, col_hist = st.columns([1, 1, 0.4])
    else:
        col_img, col_txt = st.columns([1, 1])
        col_hist = None
    # Use current_p defined above

    with col_img:
        from pathlib import Path

        page_img_path = Path(paths["scans"]) / f"pag_{current_p-1:04d}.jpg"
        img_obj = None
        if page_img_path.exists():
            img_obj = PILImage.open(str(page_img_path))
        elif Path(paths["pdf"]).exists():
            img_obj = load_pdf_page(paths["pdf"], current_p)

        # Calculate stats for the header
        stats_str = ""
        if img_obj:
            p_stat = None
            if stats:
                p_stat = next((p for p in stats.get("pages", []) if p.get("page_index") == current_p-1), None)

            if not p_stat:
                w, h = img_obj.size
                file_size = page_img_path.stat().st_size if page_img_path.exists() else 0
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
                st.session_state[page_key] = max(1, current_p - 1)
                st.session_state["current_page"] = st.session_state[page_key]
                st.rerun()
        with c_nav2:
            st.markdown(f"""
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;">
                    <span style="font-size: 1.4rem; font-weight: 800; color: #FF4B4B; line-height: 1;">{current_p} <span style="color: #444; font-weight: 300;">/ {total_pages}</span></span>
                </div>
            """, unsafe_allow_html=True)
        with c_nav3:
            if st.button("▶ NEXT", use_container_width=True, key="btn_next_sub"):
                st.session_state[page_key] = min(total_pages, current_p + 1)
                st.session_state["current_page"] = st.session_state[page_key]
                st.rerun()

    with col_txt:
        trans, text_val = render_transcription_editor(doc_id, library, current_p, ocr_engine, current_model)

    if col_hist:
        with col_hist:
            render_history_sidebar(doc_id, library, current_p, current_data=trans, current_text=text_val)

    # --- NATIVE TIMELINE SLIDER (Bottom) ---
    st.markdown("<br>", unsafe_allow_html=True)
    # Removing 'key' to prevent Streamlit widget state from overriding our manual state (page_key).
    # This specifically fixes the 'jump back' issue during reruns.
    c_line = st.slider("Timeline", 1, total_pages, value=current_p)
    if c_line != current_p:
        st.session_state[page_key] = c_line
        st.session_state["current_page"] = c_line
        st.rerun()


def render_transcription_editor(doc_id, library, current_p, ocr_engine, current_model):
    storage = get_storage()
    trans = storage.load_transcription(doc_id, current_p, library)
    initial_text = trans.get("full_text", "") if trans else ""
    current_status = trans.get("status", "draft") if trans else "draft"
    is_manual = trans.get("is_manual", False) if trans else False
    # NOTE: original_ocr_text is currently not displayed/used in this UI.

    # INFO MESSAGE NEXT TO HEADER
    info_msg = ""
    if not trans:
        info_msg = " <span style='color: #888; font-size: 0.9rem; font-weight: normal; margin-left:10px;'>(Nessuna trascrizione: scrivi e salva per creare)</span>"

    # HEADER WITH TOGGLE
    h_c1, h_c2 = st.columns([8, 1])
    with h_c1:
        v_badge = ""
        if current_status == "verified":
            v_badge = '<span style="background-color: #28a745; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; font-weight: bold; margin-left: 10px; vertical-align: middle;">VERIFICATO ✅</span>'
        st.markdown(f"### Trascrizione{v_badge}{info_msg}", unsafe_allow_html=True)
    with h_c2:
        btn_hist = "📂" if st.session_state.get("show_history") else "📜"
        if st.button(btn_hist, help="Apri/Chiudi Cronologia", key=f"toggle_hist_{current_p}"):
            st.session_state["show_history"] = not st.session_state.get("show_history", False)
            st.rerun()

    edit_key = f"trans_editor_{doc_id}_{current_p}"

    # --- STATE INITIALIZATION ---
    # To avoid the "widget with key ... created with a default value but also had its value set via Session State" warning,
    # we initialize the session state and call text_area WITHOUT the 'value' parameter.
    if edit_key not in st.session_state:
        st.session_state[edit_key] = initial_text

    # --- OCR TRIGGERS (Confirmed or Initial) ---
    # We handle OCR calls at the top so the st.status loader is always in a consistent position.
    if st.session_state.get("confirm_ocr_sync") == current_p:
        st.warning("⚠️ Testo esistente! Sovrascrivere?", icon="⚠️")
        c1, c2 = st.columns(2)
        if c1.button("Sì, Sovrascrivi", use_container_width=True, type="primary"):
            st.session_state["trigger_ocr_sync"] = current_p
            st.session_state["confirm_ocr_sync"] = None
            st.rerun()
        if c2.button("No, Annulla", use_container_width=True):
            st.session_state["confirm_ocr_sync"] = None
            st.rerun()

    if st.session_state.get("trigger_ocr_sync") == current_p:
        run_ocr_sync(doc_id, library, current_p, ocr_engine, current_model)
        st.session_state["trigger_ocr_sync"] = None
        st.rerun()

    # --- PRE-RENDER STATE SYNC ---
    pending_key = f"pending_update_{edit_key}"
    if pending_key in st.session_state:
        st.session_state[edit_key] = st.session_state[pending_key]
        del st.session_state[pending_key]

    # --- FORM-BASED EDITOR ---
    with st.form(key=f"editor_form_{doc_id}_{current_p}", clear_on_submit=False):
        # We use the session_state key directly, omitting the 'value' argument.
        text_val = st.text_area("Editor", height=700, key=edit_key, label_visibility="collapsed")

        f_c1, f_c2 = st.columns([2, 5])
        # Compare with the last saved state
        is_dirty = text_val != initial_text

        with f_c1:
            if st.form_submit_button("💾 Salva", use_container_width=True, type="primary" if is_dirty else "secondary"):
                new_data = {"full_text": text_val, "engine": trans.get(
                    "engine", "manual") if trans else "manual", "is_manual": True, "status": current_status, "average_confidence": 1.0}
                storage.save_transcription(doc_id, current_p, new_data, library)

                st.session_state[f"pending_update_{edit_key}"] = text_val
                toast("✅ Modifiche salvate!", icon="💾")
                time.sleep(0.5)
                st.rerun()

        with f_c2:
            if is_dirty:
                st.warning("⚠️ Modifiche non salvate", icon="🖋️")

    # --- OTHER ACTIONS (Outside Form) ---
    t_c1, t_c2 = st.columns([1, 1])

    with t_c1:
        is_verified = current_status == "verified"
        btn_label = "⚪ Segna come da Verificare" if is_verified else "✅ Segna come Verificato"
        if st.button(btn_label, use_container_width=True, key=f"btn_verify_{current_p}"):
            new_status = "draft" if is_verified else "verified"
            data_to_save = trans if trans else {"full_text": "", "lines": [], "engine": "manual"}

            # Save a snapshot to history before status change
            storage.save_history(doc_id, current_p, data_to_save, library)

            data_to_save["status"] = new_status
            data_to_save["is_manual"] = True
            storage.save_transcription(doc_id, current_p, data_to_save, library)
            st.rerun()

    with t_c2:
        if st.button(f"🤖 Nuova Chiamata {ocr_engine}", use_container_width=True, key=f"btn_ocr_{current_p}"):
            existing = storage.load_transcription(doc_id, current_p, library)
            if existing:
                st.session_state["confirm_ocr_sync"] = current_p
            else:
                st.session_state["trigger_ocr_sync"] = current_p
            st.rerun()

    if trans:
        st.caption(
            f"Engine: {trans.get('engine')} | Conf: {trans.get('average_confidence', 'N/A')} | 🕒 {trans.get('timestamp', '-')}")
        if is_manual:
            st.caption("✍️ Modificato Manualmente")

    return trans, text_val


def render_history_sidebar(doc_id, library, current_p, current_data=None, current_text=""):
    """Render the history list in a vertical side column."""
    storage = get_storage()
    st.markdown("### 📜 Cronologia")

    # Deletion logic
    if st.button("🗑️ Svuota Tutto", use_container_width=True, key=f"clear_side_{current_p}"):
        st.session_state[f"confirm_clear_{current_p}"] = True

    if st.session_state.get(f"confirm_clear_{current_p}"):
        st.warning("Sicuro?")
        cc1, cc2 = st.columns(2)
        if cc1.button("Sì", type="primary", use_container_width=True, key=f"c_ok_{current_p}"):
            storage.clear_history(doc_id, current_p, library)
            del st.session_state[f"confirm_clear_{current_p}"]
            st.rerun()
        if cc2.button("No", use_container_width=True, key=f"c_no_{current_p}"):
            del st.session_state[f"confirm_clear_{current_p}"]
            st.rerun()

    st.divider()

    history = storage.load_history(doc_id, current_p, library)
    if not history:
        st.info("Nessuna modifica.")
        return

    edit_key = f"trans_editor_{doc_id}_{current_p}"

    with st.container(height=650):
        # Show latest first
        for i in range(len(history)):
            idx = len(history) - 1 - i
            entry = history[idx]
            prev_entry = history[idx - 1] if idx > 0 else None

            ts = entry.get("timestamp", "-").split(" ")[1]  # Time only
            full_ts = entry.get("timestamp", "-")
            eng = entry.get("engine", "manual")
            status = entry.get("status", "draft")
            chars = len(entry.get("full_text", ""))
            is_manual_entry = entry.get("is_manual", False)

            icon = "✍️" if is_manual_entry else "🤖"
            v_label = " 📌" if idx == 0 else ""

            diff = 0
            if prev_entry:
                diff = chars - len(prev_entry.get("full_text", ""))

            diff_str = f"{diff:+d}" if diff != 0 else "="
            diff_color = "#28a745" if diff > 0 else "#dc3545" if diff < 0 else "#6c757d"
            status_icon = " ✅" if status == "verified" else ""

            with st.container():
                st.markdown(
                    f"<p style='margin-bottom:0px; font-size:0.95rem;'><b>{ts}</b>{v_label}{status_icon}</p><small style='color:#777; font-size:0.85rem;'>{icon} {eng}</small>", unsafe_allow_html=True)
                c1, c2 = st.columns([2, 1])
                c1.markdown(
                    f"<span style='font-size:0.95rem;'><b>{chars} ch</b></span> <span style='color:{diff_color}; font-size:0.8rem; font-family:monospace;'>({diff_str})</span>", unsafe_allow_html=True)
                if c2.button("↩", key=f"restore_side_{current_p}_{idx}", use_container_width=True, help=f"Ripristina versione del {full_ts}"):
                    # Safety snapshot of current text
                    if current_text:
                        snap = {
                            "full_text": current_text,
                            "engine": current_data.get("engine", "manual") if current_data else "manual",
                            "is_manual": True,
                            "status": current_data.get("status", "draft") if current_data else "draft"
                        }
                        storage.save_history(doc_id, current_p, snap, library)

                    storage.save_transcription(doc_id, current_p, entry, library)
                    st.session_state[f"pending_update_{edit_key}"] = entry.get("full_text", "")
                    toast("Versione ripristinata!")
                    st.rerun()

            if i < len(history) - 1:
                st.markdown("<hr style='margin: 0.3rem 0;'>", unsafe_allow_html=True)
