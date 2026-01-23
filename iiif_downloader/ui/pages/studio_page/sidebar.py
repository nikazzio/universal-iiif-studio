"""
Sidebar Module - Refactored
Modern sidebar with document selection, navigation, metadata, and export tools.
"""

from pathlib import Path

import streamlit as st

from iiif_downloader.jobs import job_manager
from iiif_downloader.pdf_utils import generate_pdf_from_images
from iiif_downloader.ui.notifications import toast
from iiif_downloader.ui.state import get_storage

from .ocr_utils import render_ocr_controls
from .studio_state import StudioState


def render_studio_sidebar(docs: list, doc_id: str, library: str, paths: dict):
    """
    Render the complete sidebar for Studio page.

    Args:
        docs: List of available documents
        doc_id: Current document ID
        library: Current library name
        paths: Document paths dictionary
    """

    st.sidebar.title("🏛️ Studio")

    # Document selection
    selected_doc = _render_document_selector(docs, doc_id)

    if not selected_doc:
        return None, None

    # Extract info
    new_doc_id = selected_doc["id"]
    new_library = selected_doc["library"]

    # Update state if changed
    if new_doc_id != doc_id:
        StudioState.set(StudioState.CURRENT_DOC_ID, new_doc_id)
        st.rerun()

    st.sidebar.markdown("---")

    # Active jobs
    _render_active_jobs()

    st.sidebar.markdown("---")

    # OCR controls
    ocr_engine, current_model = render_ocr_controls(new_doc_id, new_library)

    st.sidebar.markdown("---")

    # Export tools
    _render_export_panel(new_doc_id, paths)

    return ocr_engine, current_model


def _render_document_selector(docs: list, current_doc_id: str):
    """Render document selection dropdown."""

    st.sidebar.subheader("📚 Selezione Documento")

    default_idx = 0
    for i, d in enumerate(docs):
        if d["id"] == current_doc_id:
            default_idx = i
            break

    doc_labels = [f"{d['library']} / {d['id']}" for d in docs]
    selected_label = st.sidebar.selectbox("Manoscritto", doc_labels, index=default_idx, key="doc_selector")

    selected_doc = next(d for d in docs if f"{d['library']} / {d['id']}" == selected_label)

    return selected_doc


def _render_quick_navigation(doc_id: str, paths: dict):
    """Render quick page navigation controls."""

    st.sidebar.subheader("🧭 Navigazione Rapida")

    current_page = StudioState.get_current_page(doc_id)

    # Quick jump input
    col1, col2 = st.sidebar.columns([3, 1])

    with col1:
        jump_page = st.number_input(
            "Vai a pagina",
            min_value=1,
            value=current_page,
            step=1,
            key=f"jump_input_{doc_id}",
            label_visibility="collapsed",
        )

    with col2:
        if st.button("→", width="stretch", help="Vai"):
            StudioState.set_current_page(doc_id, jump_page)
            st.rerun()

    # Quick page buttons
    st.sidebar.caption("Accesso Rapido:")

    qcol1, qcol2, qcol3 = st.sidebar.columns(3)

    with qcol1:
        if st.button("⏮️ Prima", width="stretch", help="Prima pagina"):
            StudioState.set_current_page(doc_id, 1)
            st.rerun()

    with qcol2:
        if st.button("🔖 Metà", width="stretch", help="Pagina centrale"):
            # Calculate middle page
            scans_dir = paths.get("scans")
            if scans_dir:
                files = [f for f in Path(scans_dir).iterdir() if f.suffix == ".jpg"]
                mid_page = len(files) // 2 if files else 1
                StudioState.set_current_page(doc_id, mid_page)
                st.rerun()

    with qcol3:
        if st.button("⏭️ Ultima", width="stretch", help="Ultima pagina"):
            # Find last page
            scans_dir = paths.get("scans")
            if scans_dir:
                files = [f for f in Path(scans_dir).iterdir() if f.suffix == ".jpg"]
                last_page = len(files) if files else 1
                StudioState.set_current_page(doc_id, last_page)
                st.rerun()


def _render_metadata_panel(meta: dict, stats: dict):
    """Render document metadata in expandable section."""

    with st.sidebar.expander("ℹ️ Dettagli Tecnici", expanded=False):
        if stats:
            pages_s = stats.get("pages", [])
            if pages_s:
                avg_w = sum(p["width"] for p in pages_s) // len(pages_s)
                avg_h = sum(p["height"] for p in pages_s) // len(pages_s)
                total_mb = sum(p["size_bytes"] for p in pages_s) / (1024 * 1024)

                st.metric("Pagine", len(pages_s))
                st.metric("Risoluzione Media", f"{avg_w}×{avg_h} px")
                st.metric("Peso Totale", f"{total_mb:.1f} MB")

        if meta:
            st.markdown("#### 📜 Manifesto")
            st.write(f"**Titolo**: {meta.get('label', 'Senza Titolo')}")

            desc = meta.get("description", "-")
            if len(desc) > 100:
                desc = desc[:100] + "..."
            st.write(f"**Descrizione**: {desc}")

            st.write(f"**Attribuzione**: {meta.get('attribution', '-')}")
            st.write(f"**Licenza**: {meta.get('license', '-')}")

            if "metadata" in meta and isinstance(meta["metadata"], list):
                st.markdown("---")
                for entry in meta["metadata"][:5]:  # Limit to first 5
                    label = entry.get("label")
                    val = entry.get("value")

                    if isinstance(label, (list, dict)):
                        label = str(list(label.values())[0] if isinstance(label, dict) else label[0])
                    if isinstance(val, (list, dict)):
                        val = str(list(val.values())[0] if isinstance(val, dict) else ", ".join(str(v) for v in val))

                    st.caption(f"**{label}**: {val}")

            st.caption(f"🕒 Scaricato: {meta.get('download_date', '-')}")


def _render_active_jobs():
    """Display active background jobs."""

    st.sidebar.subheader("📤 Job Attivi")

    active_jobs = job_manager.list_jobs(active_only=True)

    if active_jobs:
        st.sidebar.subheader("⚙️ Job Attivi")
        for job_id, job in active_jobs.items():
            progress = int(job.get("progress", 0) * 100)
            st.sidebar.progress(progress / 100, text=f"{job['message']} ({progress}%)")


def _render_export_panel(doc_id: str, paths: dict):
    """Render export tools."""

    st.sidebar.subheader("📤 Esportazione")

    if st.sidebar.button("📄 Genera PDF Completo", width="stretch"):
        with st.spinner("Generazione PDF in corso..."):
            scans_dir = Path(paths["scans"])

            if scans_dir.exists():
                imgs = sorted([str(p) for p in scans_dir.iterdir() if p.suffix.lower() == ".jpg"])

                if imgs:
                    pdf_out = str(Path(paths["root"]) / f"{doc_id}.pdf")
                    success, msg = generate_pdf_from_images(imgs, pdf_out)

                    if success:
                        toast("✅ PDF Creato!", icon="📄")
                        st.sidebar.success(f"Salvato: `{Path(pdf_out).name}`")
                    else:
                        st.sidebar.error(msg)
                else:
                    st.sidebar.error("Nessuna immagine trovata.")
            else:
                st.sidebar.error("Directory pagine non trovata.")

    st.sidebar.caption("💡 Il PDF conterrà tutte le pagine del manoscritto in alta qualità.")
