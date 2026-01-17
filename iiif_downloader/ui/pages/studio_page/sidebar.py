import streamlit as st
import os
from iiif_downloader.pdf_utils import generate_pdf_from_images
from iiif_downloader.jobs import job_manager

def render_sidebar_metadata(meta, stats):
    with st.sidebar.expander("ℹ️ Dettagli Tecnici", expanded=False):
        if stats:
            pages_s = stats.get("pages", [])
            if pages_s:
                avg_w = sum(p["width"] for p in pages_s) // len(pages_s)
                avg_h = sum(p["height"] for p in pages_s) // len(pages_s)
                total_mb = sum(p["size_bytes"] for p in pages_s) / (1024*1024)
                st.write(f"**Risoluzione Media**: {avg_w}x{avg_h} px")
                st.write(f"**Peso Totale**: {total_mb:.1f} MB")
                st.write(f"**Pagine**: {len(pages_s)}")
        
        if meta:
            st.markdown("### 📜 Dati Manifesto")
            st.write(f"**Titolo**: {meta.get('label', 'Senza Titolo')}")
            st.write(f"**Descrizione**: {meta.get('description', '-')}")
            st.write(f"**Attribuzione**: {meta.get('attribution', '-')}")
            st.write(f"**Licenza**: {meta.get('license', '-')}")
            
            if 'metadata' in meta and isinstance(meta['metadata'], list):
                st.markdown("---")
                for entry in meta['metadata']:
                    label = entry.get('label')
                    val = entry.get('value')
                    
                    if isinstance(label, list): label = label[0] if label else "Info"
                    if isinstance(label, dict): label = list(label.values())[0]
                    
                    if isinstance(val, list): val = ", ".join([str(v) for v in val])
                    if isinstance(val, dict): val = list(val.values())[0]

                    st.write(f"**{label}**: {val}")
            
            st.caption(f"Scaricato il: {meta.get('download_date')}")
            st.caption(f"Manifest: {meta.get('manifest_url')}")

def render_sidebar_jobs():
    active_job = job_manager.list_jobs(active_only=True)
    if active_job:
        for jid, job in active_job.items():
            st.sidebar.info(f"⚙️ {job['message']} ({int(job['progress']*100)}%)")

def render_sidebar_export(doc_id, paths):
    st.sidebar.markdown("---")
    st.sidebar.subheader("Esportazione")
    if st.sidebar.button("📄 Crea PDF Completo", use_container_width=True):
         with st.spinner("Generazione PDF in corso..."):
             pages_dir = paths["pages"]
             if os.path.exists(pages_dir):
                 imgs = sorted([os.path.join(pages_dir, f) for f in os.listdir(pages_dir) if f.endswith(".jpg")])
                 if imgs:
                     pdf_out = os.path.join(paths["root"], f"{doc_id}.pdf")
                     success, msg = generate_pdf_from_images(imgs, pdf_out)
                     if success:
                         st.toast("PDF Creato!", icon="✅")
                         st.sidebar.success(f"PDF salvato in: {pdf_out}")
                     else:
                         st.sidebar.error(msg)
                 else:
                     st.sidebar.error("Nessuna immagine trovata.")
             else:
                 st.sidebar.error("Directory pagine non trovata.")
