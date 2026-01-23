import time

import streamlit as st
from requests import RequestException

from iiif_downloader.config_manager import get_config_manager
from iiif_downloader.logic import IIIFDownloader
from iiif_downloader.pdf_utils import convert_pdf_to_images
from iiif_downloader.resolvers.discovery import (
    resolve_shelfmark,
)
from iiif_downloader.storage.vault_manager import VaultManager
from iiif_downloader.ui.notifications import toast
from iiif_downloader.utils import ensure_dir, get_json, save_json


def render_discovery_page():
    """Render the Discovery & Download page."""
    st.title("🛰️ Discovery & Download")

    # --- Sidebar Controls ---
    st.sidebar.subheader("Modalità")

    mode_options = ["Segnatura / URL", "Importa PDF"]

    # Check if we should auto-open a specific tab (from Search page redirect)
    default_mode = "Segnatura / URL"
    if st.session_state.get("discovery_active_tab"):
        # Actually we handled this via preview state, so the tab selection is purely visual here.
        pass

    # Try st.pills (Streamlit 1.40+)
    try:
        disc_mode = st.sidebar.pills(
            "Metodo",
            mode_options,
            default=default_mode,
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

    # --- PREVIEW AREA ---
    preview = st.session_state.get("discovery_preview")
    if preview:
        render_preview(preview)


def render_url_search_panel():
    """Render the URL / Shelfmark search panel."""
    st.markdown("### 🔎 Ricerca per Segnatura")
    st.caption("Inserisci l'ID, la segnatura o l'URL del manifesto per analizzare il documento.")

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

        if (
            st.button(
                "🔍 Analizza Documento",
                width="stretch",
                type="primary",
            )
            and shelf_input
        ):
            with st.spinner("Analisi in corso..."):
                manifest_url, doc_id_hint = resolve_shelfmark(
                    lib_choice,
                    shelf_input,
                )
                if manifest_url:
                    analyze_manifest(manifest_url, doc_id_hint, active_lib)
                else:
                    toast(
                        doc_id_hint or "ID non risolvibile",
                        icon="⚠️",
                    )


def analyze_manifest(manifest_url, doc_id, library):
    """Analyze a IIIF manifest and store preview info in session state."""
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
        toast("Manifest analizzato con successo!", icon="✅")
    except (
        RequestException,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
    ) as e:
        st.error(f"Errore analisi: {e}")


def get_viewer_url(lib, doc_id, manifest_url):
    """Get the official viewer URL for a given library and document ID."""
    if lib == "Vaticana":
        return f"https://digi.vatlib.it/view/{doc_id}"
    if lib == "Gallica":
        ark = manifest_url.split("/iiif/")[1].replace("/manifest.json", "")
        return f"https://gallica.bnf.fr/{ark}"
    if lib == "Bodleian":
        return f"https://digital.bodleian.ox.ac.uk/objects/{doc_id}/"
    return manifest_url


def render_preview(preview):
    """Render the preview and download actions for a resolved manifest."""
    st.markdown("---")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown(f"### 📖 {preview['label']}")

        st.caption(f"ID: {preview['id']} | Library: {preview['library']} | Pages: {preview['pages']}")
        if preview.get("description"):
            st.info(preview["description"])
        if preview.get("viewer_url"):
            st.link_button(
                "🌐 Apri Viewer Ufficiale",
                preview["viewer_url"],
            )

    with c2:
        st.markdown("#### Azioni")
        if st.button(
            "🚀 Avvia Download",
            type="primary",
            width="stretch",
        ):
            start_download_process(preview)

        if st.button("🗑️ Reset", width="stretch"):
            st.session_state["discovery_preview"] = None
            st.rerun()


def start_download_process(preview):
    """Start the download process for the given preview manifest."""
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
        workers=int(get_config_manager().get_setting("system.download_workers", 4)),
    )

    with st.spinner("Connessione e Download..."):
        try:
            downloader.run()
            toast(f"Completato! {preview['id']} scaricato.", icon="🎉")
            time.sleep(1)
            st.session_state["discovery_preview"] = None
            st.rerun()
        except (RequestException, OSError, ValueError, RuntimeError) as e:
            st.error(f"Errore download: {e}")


def render_pdf_import():
    """Render the PDF import panel."""
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
        help=("Se attivo, converte le pagine in JPG per uno scorrimento più fluido."),
    )

    if uploaded_file is not None and st.button(
        "📥 Importa Documento",
        type="primary",
        width="stretch",
    ):
        try:
            _handle_pdf_import(
                uploaded_file=uploaded_file,
                title=title,
                author=author,
                year=year,
                provenance=provenance,
                extract_images=extract_images,
            )
        except (OSError, ValueError) as e:
            st.error(f"Errore durante importazione: {e}")


def _handle_pdf_import(*, uploaded_file, title, author, year, provenance, extract_images):
    safe_id = _build_safe_id(uploaded_file, title)
    doc_dirs = _prepare_local_doc_dirs(safe_id)
    if not doc_dirs:
        return
    doc_dir, data_dir, pdf_dir, scans_dir = doc_dirs

    pdf_path = _save_uploaded_pdf(pdf_dir, safe_id, uploaded_file)
    meta_entries = _build_meta_entries(author, year, provenance)

    vault = VaultManager()
    _register_local_doc(vault, safe_id, title, uploaded_file, doc_dir)

    meta = _build_local_metadata(safe_id, title, uploaded_file, provenance, meta_entries)
    save_json(data_dir / "metadata.json", meta)

    page_count = _extract_pdf_images_if_requested(
        extract_images=extract_images,
        pdf_path=pdf_path,
        scans_dir=scans_dir,
        data_dir=data_dir,
        meta=meta,
    )

    vault.upsert_manuscript(id=safe_id, total_canvases=page_count, downloaded_canvases=page_count)

    st.success(f"Documento '{safe_id}' importato con successo!")
    time.sleep(1.5)
    st.session_state["nav_override"] = "Studio"
    st.session_state["studio_doc_id"] = safe_id
    st.rerun()


def _build_safe_id(uploaded_file, title):
    safe_name = uploaded_file.name.replace(".pdf", "").strip()
    if title:
        safe_name = title.replace(" ", "_")
    return "".join(c for c in safe_name if c.isalnum() or c in ("_", "-"))


def _prepare_local_doc_dirs(safe_id):
    base_dir = get_config_manager().get_downloads_dir()
    doc_dir = base_dir / "Local" / safe_id
    if doc_dir.exists():
        st.error(f"Esiste già un documento con ID '{safe_id}'. Cambia titolo o rinomina.")
        return None

    ensure_dir(doc_dir)
    data_dir = doc_dir / "data"
    pdf_dir = doc_dir / "pdf"
    scans_dir = doc_dir / "scans"
    ensure_dir(data_dir)
    ensure_dir(pdf_dir)
    ensure_dir(scans_dir)
    return doc_dir, data_dir, pdf_dir, scans_dir


def _save_uploaded_pdf(pdf_dir, safe_id, uploaded_file):
    pdf_path = pdf_dir / f"{safe_id}.pdf"
    with pdf_path.open("wb") as f:
        f.write(uploaded_file.getbuffer())
    return pdf_path


def _build_meta_entries(author, year, provenance):
    meta_entries = []
    if author:
        meta_entries.append({"label": "Autore", "value": author})
    if year:
        meta_entries.append({"label": "Anno", "value": year})
    if provenance:
        meta_entries.append({"label": "Provenienza", "value": provenance})
    return meta_entries


def _register_local_doc(vault, safe_id, title, uploaded_file, doc_dir):
    vault.upsert_manuscript(
        id=safe_id,
        library="Local",
        label=title or uploaded_file.name,
        status="complete",
        local_path=str(doc_dir),
        total_canvases=0,
    )


def _build_local_metadata(safe_id, title, uploaded_file, provenance, meta_entries):
    return {
        "label": title or uploaded_file.name,
        "description": (f"Importato da PDF locale: {uploaded_file.name}"),
        "attribution": provenance or "Local Import",
        "license": "Copyright User",
        "id": safe_id,
        "manifest_url": "local",
        "download_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metadata": meta_entries,
    }


def _extract_pdf_images_if_requested(*, extract_images, pdf_path, scans_dir, data_dir, meta):
    if not extract_images:
        return 0

    status_text = st.empty()
    prog_bar = st.progress(0)

    def prog(curr, total):
        prog_bar.progress(curr / total)
        status_text.caption(f"Estrazione: {curr}/{total}")

    success, msg = convert_pdf_to_images(
        str(pdf_path),
        str(scans_dir),
        progress_callback=prog,
        dpi=int(get_config_manager().get_setting("pdf.ocr_dpi", 300)),
    )

    if not success:
        st.warning(f"Estrazione fallita (il PDF è comunque salvato): {msg}")
        return 0

    toast("Immagini Estratte!", icon="🖼️")
    files = [p for p in scans_dir.iterdir() if p.suffix.lower() == ".jpg"]
    page_count = len(files)
    meta["pages"] = page_count
    save_json(
        data_dir / "metadata.json",
        meta,
    )
    return page_count
