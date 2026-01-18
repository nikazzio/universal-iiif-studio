import os
import time

import streamlit as st
from requests import RequestException

from iiif_downloader.config import config
from iiif_downloader.logic import IIIFDownloader
from iiif_downloader.resolvers.discovery import (
    resolve_shelfmark,
    search_gallica,
)
from iiif_downloader.ui.styling import render_gallery_card
from iiif_downloader.utils import get_json


def render_discovery_page():
    st.title("🛰️ Discovery & Download")

    # --- Sidebar Controls ---
    st.sidebar.subheader("Modalità")

    mode_options = ["Segnatura / URL", "Importa PDF"]
    # Include Gallica catalog search.
    mode_options.append("Cerca nel Catalogo (Gallica)")

    # Try st.pills (Streamlit 1.40+)
    try:
        disc_mode = st.sidebar.pills(
            "Metodo",
            mode_options,
            default="Segnatura / URL",
        )
    except AttributeError:
        disc_mode = st.sidebar.radio("Metodo", mode_options)

    if not disc_mode:
        disc_mode = "Segnatura / URL"

    # --- ACTION AREA ---
    # Spacer
    st.markdown("<br>", unsafe_allow_html=True)

    if disc_mode == "Segnatura / URL":
        render_url_search_panel()
    elif disc_mode == "Importa PDF":
        render_pdf_import()
    elif disc_mode == "Cerca nel Catalogo (Gallica)":
        render_catalog_search_panel()

    # --- PREVIEW AREA ---
    preview = st.session_state.get("discovery_preview")
    if preview:
        render_preview(preview)


def render_url_search_panel():
    st.markdown("### 🔎 Ricerca per Segnatura")
    st.caption(
        "Inserisci l'ID, la segnatura o l'URL del manifesto per analizzare "
        "il documento."
    )

    # Library choices
    lib_map = {
        "Vaticana (BAV)": "Vaticana",
        "Gallica (BnF)": "Gallica",
        "Bodleian (Oxford)": "Bodleian",
        "Altro / URL Diretto": "Unknown",
    }

    with st.container(border=True):
        c1, c2 = st.columns([1, 2])
        lib_choice = c1.selectbox(
            "Biblioteca / Fonte",
            list(lib_map.keys()),
            index=0,
        )
        active_lib = lib_map[lib_choice]

        placeholders = {
            "Vaticana": "es. Urb.lat.1779",
            "Gallica": "es. btv1b10033406t",
            "Bodleian": "es. 080f88f5-7586...",
            "Unknown": "https://.../manifest.json",
        }

        shelf_input = c2.text_input(
            "ID o URL",
            placeholder=placeholders.get(active_lib, "Inserisci ID"),
        )

        if st.button(
            "🔍 Analizza Documento",
            use_container_width=True,
            type="primary",
        ):
            if shelf_input:
                with st.spinner("Analisi in corso..."):
                    manifest_url, doc_id_hint = resolve_shelfmark(
                        lib_choice,
                        shelf_input,
                    )
                    if manifest_url:
                        analyze_manifest(manifest_url, doc_id_hint, active_lib)
                    else:
                        st.toast(
                            doc_id_hint or "ID non risolvibile",
                            icon="⚠️",
                        )


def render_catalog_search_panel():
    st.markdown("### 📚 Ricerca Catalogo (Gallica)")
    st.caption(
        "Cerca direttamente nel catalogo della Biblioteca Nazionale "
        "di Francia."
    )

    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        query = col1.text_input(
            "Parola chiave",
            placeholder="es. Divina Commedia, Dante...",
            label_visibility="collapsed",
        )

        if (
            col2.button("🔎 Cerca", use_container_width=True, type="primary")
            and query
        ):
            with st.spinner("Ricerca in corso..."):
                st.session_state["search_results"] = search_gallica(query)

    # Gallery View
    results = st.session_state.get("search_results", [])
    if results:
        st.subheader(f"Risultati ({len(results)})")
        st.markdown("---")

        cols = st.columns(4)
        for i, res in enumerate(results):
            with cols[i % 4]:
                render_gallery_card(
                    title=res["title"],
                    subtitle=res["id"],
                    image_url=res.get("preview_url"),
                )
                if st.button("Seleziona", key=f"sel_{res['id']}"):
                    analyze_manifest(res["manifest_url"], res["id"], "Gallica")


def analyze_manifest(manifest_url, doc_id, library):
    try:
        m = get_json(manifest_url)
        label = m.get("label", "Senza Titolo")
        if isinstance(label, list):
            label = label[0]
        desc = m.get("description", "")
        if isinstance(desc, list):
            desc = desc[0]

        # IIIF v2/v3 compatibility
        canvases = []
        if "sequences" in m:
            canvases = m["sequences"][0].get("canvases", [])
        elif "items" in m:
            canvases = m["items"]

        st.session_state["discovery_preview"] = {
            "url": manifest_url,
            "id": doc_id,
            "label": str(label),
            "library": library,
            "description": str(desc)[:500],
            "pages": len(canvases),
            "viewer_url": get_viewer_url(library, doc_id, manifest_url),
        }
        st.toast("Manifest analizzato con successo!", icon="✅")
    except (
        RequestException,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
    ) as e:
        st.error(f"Errore analisi: {e}")


def get_viewer_url(lib, doc_id, manifest_url):
    if lib == "Vaticana":
        return f"https://digi.vatlib.it/view/{doc_id}"
    if lib == "Gallica":
        ark = manifest_url.split("/iiif/")[1].replace("/manifest.json", "")
        return f"https://gallica.bnf.fr/{ark}"
    if lib == "Bodleian":
        return f"https://digital.bodleian.ox.ac.uk/objects/{doc_id}/"
    return manifest_url


def render_preview(preview):
    st.markdown("---")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown(f"### 📖 {preview['label']}")
        st.caption(
            f"ID: {preview['id']} | "
            f"Library: {preview['library']} | "
            f"Pages: {preview['pages']}"
        )
        if preview.get("description"):
            st.info(preview["description"])
        if preview.get('viewer_url'):
            st.link_button(
                "🌐 Apri Viewer Ufficiale",
                preview["viewer_url"],
            )

    with c2:
        st.markdown("#### Azioni")
        if st.button(
            "🚀 Avvia Download",
            type="primary",
            use_container_width=True,
        ):
            start_download_process(preview)

        if st.button("🗑️ Reset", use_container_width=True):
            st.session_state["discovery_preview"] = None
            st.rerun()


def start_download_process(preview):
    progress_bar = st.progress(0, text="Inizializzazione...")
    status_text = st.empty()

    def hook(curr, total):
        progress_bar.progress(curr / total)
        status_text.text(f"Scaricamento: {curr}/{total}")

    downloader = IIIFDownloader(
        manifest_url=preview["url"],
        output_name=preview["id"],
        library=preview["library"],
        progress_callback=hook,
        workers=config.get("system", "download_workers", 4),
    )

    with st.spinner("Connessione e Download..."):
        try:
            downloader.run()
            st.toast(f"Completato! {preview['id']} scaricato.", icon="🎉")
            time.sleep(1)
            # Optionally redirect to studio
            st.session_state["discovery_preview"] = None
            # Redirect to Studio requires nav override
            # st.session_state["nav_override"] = "Studio"
            # Original code just cleared preview (no redirect).
            st.rerun()
        except (RequestException, OSError, ValueError, RuntimeError) as e:
            st.error(f"Errore download: {e}")


def render_pdf_import():
    st.markdown("### 📥 Importa PDF Locale")
    st.caption("Carica un documento PDF esistente per usarlo nello Studio.")

    uploaded_file = st.file_uploader("Seleziona File PDF", type=["pdf"])

    default_title = ""
    if uploaded_file:
        default_title = uploaded_file.name.replace(".pdf", "")

    with st.expander("Metadati Documento", expanded=True):
        c1, c2 = st.columns(2)
        title = c1.text_input(
            "Titolo",
            placeholder="Titolo del documento",
            value=default_title,
        )
        author = c2.text_input("Autore", placeholder="es. Dante Alighieri")

        c3, c4 = st.columns(2)
        year = c3.text_input("Anno", placeholder="es. 1321")
        provenance = c4.text_input(
            "Provenienza / Luogo",
            placeholder="es. Biblioteca Privata",
        )

    extract_images = st.checkbox(
        "Estrai Immagini da PDF (Consigliato per performance)",
        value=True,
        help=(
            "Se attivo, converte le pagine in JPG per uno scorrimento più "
            "fluido."
        ),
    )

    if uploaded_file is not None:
        if st.button(
            "📥 Importa Documento",
            type="primary",
            use_container_width=True,
        ):
            # Prepare paths
            safe_name = uploaded_file.name.replace(".pdf", "").strip()
            if title:
                safe_name = title.replace(" ", "_")

            # Clean generic chars
            safe_id = "".join(
                c for c in safe_name if c.isalnum() or c in ("_", "-")
            )

            from iiif_downloader.pdf_utils import convert_pdf_to_images
            from iiif_downloader.utils import ensure_dir, save_json

            # Use Local library
            base_dir = config.get_download_dir()
            doc_dir = os.path.join(base_dir, "Local", safe_id)

            if os.path.exists(doc_dir):
                st.error(
                    f"Esiste già un documento con ID '{safe_id}'. "
                    "Cambia titolo o rinomina."
                )
                return

            try:
                ensure_dir(doc_dir)
                data_dir = os.path.join(doc_dir, "data")
                pdf_dir = os.path.join(doc_dir, "pdf")
                scans_dir = os.path.join(doc_dir, "scans")
                ensure_dir(data_dir)
                ensure_dir(pdf_dir)
                ensure_dir(scans_dir)

                # Save PDF
                pdf_path = os.path.join(pdf_dir, f"{safe_id}.pdf")
                with open(pdf_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Build Metadata list
                meta_entries = []
                if author:
                    meta_entries.append({"label": "Autore", "value": author})
                if year:
                    meta_entries.append({"label": "Anno", "value": year})
                if provenance:
                    meta_entries.append(
                        {"label": "Provenienza", "value": provenance}
                    )

                # Save Metadata
                meta = {
                    "label": title or uploaded_file.name,
                    "description": (
                        "Importato da PDF locale: "
                        f"{uploaded_file.name}"
                    ),
                    "attribution": provenance or "Local Import",
                    "license": "Copyright User",
                    "id": safe_id,
                    "manifest_url": "local",
                    "download_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "metadata": meta_entries,
                }
                save_json(os.path.join(data_dir, "metadata.json"), meta)

                # Process Images?
                if extract_images:
                    # scans_dir already created above

                    status_text = st.empty()
                    prog_bar = st.progress(0)

                    def prog(curr, total):
                        prog_bar.progress(curr / total)
                        status_text.caption(f"Estrazione: {curr}/{total}")

                    success, msg = convert_pdf_to_images(
                        pdf_path,
                        scans_dir,
                        progress_callback=prog,
                    )

                    if success:
                        st.toast("Immagini Estratte!", icon="🖼️")
                        # Update metadata with page count
                        files = [
                            f
                            for f in os.listdir(scans_dir)
                            if f.endswith(".jpg")
                        ]
                        meta["pages"] = len(files)
                        save_json(
                            os.path.join(data_dir, "metadata.json"),
                            meta,
                        )
                    else:
                        st.warning(
                            "Estrazione fallita (il PDF è comunque salvato): "
                            f"{msg}"
                        )

                st.success(f"Documento '{safe_id}' importato con successo!")
                time.sleep(1.5)
                # Redirect?
                st.session_state["nav_override"] = "Studio"
                st.session_state["studio_doc_id"] = safe_id
                st.rerun()

            except (OSError, ValueError) as e:
                st.error(f"Errore durante importazione: {e}")
