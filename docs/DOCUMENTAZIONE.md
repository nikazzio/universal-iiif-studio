# Documentazione (Bozza)

Questa è una **prima base di documentazione** per Universal IIIF Downloader & Studio. È pensata per essere pratica: descrive **cosa fa l’app**, come sono organizzati i dati su disco, e come funzionano i moduli principali (UI, download IIIF, OCR, ricerca, PDF, configurazione).

> Nota: l’app usa **una sola fonte di configurazione** (`config.json`) tramite `ConfigManager`. Non esistono fallback runtime su variabili ambiente.

---

## 1) Panoramica: cosa fa l’app

Universal IIIF Downloader & Studio è una web-app Streamlit che permette di:

- **Scoprire e scaricare** manoscritti/oggetti IIIF partendo da segnatura/ID/URL (Vaticana, Gallica, Bodleian/Oxford, e URL generici).
- **Importare PDF locali** nella libreria, estrarre immagini pagina-per-pagina e trattarle come documenti “studio-ready”.
- **Studiare un documento** (immagini + trascrizione) con viewer interattivo, editor testo, stato “verificato/draft” e **cronologia** per pagina.
- **Eseguire OCR/HTR** su singola pagina o in batch (in background) usando provider: **Kraken**, **OpenAI**, **Anthropic**, **Google Vision**, **HuggingFace**.
- **Ricercare globalmente** in tutte le trascrizioni locali.
- **Esportare PDF** a partire dalle immagini scaricate.
- **Gestire risorse** (stitching IIIF con limite RAM, pulizia cache) e **logging**.

---

## 2) Avvio rapido

### 2.1 Requisiti

- Python 3.10+
- Dipendenze Python (vedi `requirements.txt`)
- Per import PDF e conversione in immagini: usa **PyMuPDF** (nessuna dipendenza di sistema esterna).

### 2.2 Avvio

- UI:
  - `streamlit run app.py`

- CLI:
  - `python main.py <url_o_id>`

---

## 3) Architettura ad alto livello

### Entry point UI

- `app.py`
  - Configura Streamlit (`st.set_page_config(layout="wide", ...)`).
  - Carica config (`get_config_manager()`).
  - Crea cartelle principali (downloads/temp/models/logs).
  - Esegue housekeeping: pulizia file temporanei più vecchi di N giorni (`cleanup_old_files`).
  - Inizializza lo stato UI (`init_session_state`) e CSS (`load_custom_css`).
  - Gestisce routing via sidebar menu (`streamlit-antd-components`).

### Moduli UI

- `iiif_downloader/ui/discovery.py`: Discovery & Download (segnature/URL, ricerca Gallica, import PDF)
- `iiif_downloader/ui/pages/studio_page/*`: Studio (viewer, editor trascrizione, OCR, cronologia, export)
- `iiif_downloader/ui/search.py`: Ricerca globale nelle trascrizioni
- `iiif_downloader/ui/components/settings_panel.py`: Impostazioni (config.json) con salvataggio e tooltips

### Core Download

- `iiif_downloader/logic/downloader.py`: pipeline di download IIIF (manifest, canvases, immagini, PDF nativo, tile-stitch fallback, stats)
- `iiif_downloader/iiif_tiles.py`: tile stitching IIIF con modalità RAM o disco (mmap) per rispettare un cap memoria

### OCR e Storage

- `iiif_downloader/ocr/processor.py`: engine OCR unificato + provider (Kraken/OpenAI/Anthropic/Google/HF)
- `iiif_downloader/ocr/storage.py`: persistenza su disco di trascrizioni, history, metadata, stats, ricerca testo

### Utility

- `iiif_downloader/config_manager.py`: gestione `config.json`
- `iiif_downloader/logger.py`: logging (console + file rotation)
- `iiif_downloader/pdf_utils.py`: import PDF (convert_pdf_to_images) e export PDF (generate_pdf_from_images)
- `iiif_downloader/utils.py`: HTTP/JSON/filesystem helpers + cleanup cache

---

## 4) Dati su disco: struttura cartelle

La struttura “standard” per un documento scaricato/importato è:

- `downloads/<Library>/<DocID>/`
  - `scans/` → immagini `pag_0000.jpg`, `pag_0001.jpg`, ...
  - `pdf/` → PDF nativo (se presente) e/o PDF generato
  - `data/`
    - `metadata.json` → metadati principali
    - `manifest.json` → manifest IIIF salvato localmente (se download IIIF)
    - `image_stats.json` → statistiche immagine per pagina (dimensioni, bytes, thumb url)
    - `transcription.json` → trascrizioni e metadati OCR
  - `history/` → file per pagina con versioni (es. `p0001_history.json`)

Documenti importati da PDF:

- `downloads/Local/<DocID>/`
  - `pdf/<DocID>.pdf`
  - `scans/` (se estrazione immagini attiva)
  - `data/metadata.json` (con `manifest_url: "local"`)

---

## 5) Configurazione: `config.json`

### 5.1 Dove si trova

`iiif_downloader/config_manager.py` seleziona un percorso “sensato”:

1. `./config.json` se scrivibile
2. altrimenti `~/.universal-iiif-downloader/config.json`

### 5.2 Chiavi principali (sezioni)

- `paths.*`
  - `downloads_dir`, `temp_dir`, `models_dir`, `logs_dir`
- `api_keys.*`
  - `openai`, `anthropic`, `google_vision`, `huggingface`
- `settings.system.*`
  - `download_workers`, `ocr_concurrency`, `request_timeout`
- `settings.defaults.*`
  - `default_library`, `auto_generate_pdf` (scarica PDF nativo se presente nel manifest), `preferred_ocr_engine`
- `settings.ui.*`
  - `theme_color`, `items_per_page`, `toast_duration`
- `settings.images.*`
  - `download_strategy`, `iiif_quality`, `viewer_quality`, `ocr_quality`, `tile_stitch_max_ram_gb`
- `settings.housekeeping.*`
  - `temp_cleanup_days`
- `settings.logging.level`

### 5.3 Impostazioni da UI

Le impostazioni sono gestite in `iiif_downloader/ui/components/settings_panel.py`.

- “Salva” scrive su disco (`cm.save()`) e mostra feedback immediato (`st.toast`).
- Le descrizioni sono nei `help=` dei widget per mantenere la UI pulita.

---

## 6) Discovery & Download

File: `iiif_downloader/ui/discovery.py`

### 6.1 Modalità disponibili

La pagina propone tre modalità:

- **Segnatura / URL**: risolve ID/URL in un manifest IIIF e mostra anteprima + azioni.
- **Importa PDF**: carica un PDF, salva in `downloads/Local/<id>/` e opzionalmente estrae immagini.
- **Cerca nel Catalogo (Gallica)**: usa SRU API BnF per cercare manoscritti e selezionare un risultato.

### 6.2 Funzioni principali

- `render_discovery_page()`
  - Gestisce la scelta modalità e mostra preview se presente in session state.

- `render_url_search_panel()`
  - Input biblioteca + shelfmark/ID/URL; su “Analizza Documento” chiama `resolve_shelfmark()`.

- `render_catalog_search_panel()`
  - Invoca `search_gallica(query)` e mostra risultati a griglia (paginati via `ui.items_per_page`).

- `analyze_manifest(manifest_url, doc_id, library)`
  - Scarica manifest (`get_json`), calcola numero pagine (canvases/items), salva preview in `st.session_state["discovery_preview"]`.

- `start_download_process(preview)`
  - Istanzia `IIIFDownloader(...)` e chiama `run()`.

### 6.3 Risoluzione ID/URL (resolver)

File: `iiif_downloader/resolvers/discovery.py` e `iiif_downloader/resolvers/*.py`

- `resolve_shelfmark(library, shelfmark)`
  - Vaticana: normalizza segnatura → `MSS_...` e genera `https://digi.vatlib.it/iiif/<id>/manifest.json`.
  - Gallica: accetta ARK o btv... e genera manifest `https://gallica.bnf.fr/iiif/ark:/12148/<id>/manifest.json`.
  - Bodleian: richiede UUID e genera `https://iiif.bodleian.ox.ac.uk/iiif/manifest/<uuid>.json`.

- Resolver “classici” usati dalla CLI:
  - `VaticanResolver`, `GallicaResolver`, `OxfordResolver`, `GenericResolver`.

---

## 7) Downloader IIIF

File: `iiif_downloader/logic/downloader.py`

### 7.1 Responsabilità

`IIIFDownloader`:

- Scarica e salva manifest e metadati (`extract_metadata`).
- Calcola canvases per IIIF v2/v3 (`get_canvases`).
- Scarica immagini pagina-per-pagina in parallelo (`ThreadPoolExecutor`).
- Salva statistiche per pagina (`image_stats.json`).
- Se il manifest pubblica un PDF (`rendering`), lo scarica come artefatto aggiuntivo (`download_native_pdf`).
- Può generare un PDF dalle immagini (`create_pdf`) su richiesta esplicita.
- Include fallback **tile stitching** quando il server rifiuta immagini `full` a grandi dimensioni.

### 7.2 Download di una pagina

- `download_page(canvas, index, folder)`
  - Estrae `service.@id` (o deduce da URL immagine) per costruire URL IIIF.
  - Applica `images.download_strategy` (es. `max`, `3000`, `1740`) per tentare più dimensioni.
  - Gestisce rate limiting (HTTP 429) con backoff.
  - Se fallisce il download /full, usa `stitch_iiif_tiles_to_jpeg()`.

### 7.3 Fallback tile stitching

- Quando un server “nega” download grandi via `/full/...`, si tenta:
  - richiesta `info.json` e pianificazione tile
  - download tile in sequenza
  - compositing in RAM oppure disco (mmap) rispettando `images.tile_stitch_max_ram_gb`

---

## 8) Stitching IIIF Tiles (RAM-safe)

File: `iiif_downloader/iiif_tiles.py`

### Funzioni principali

- `build_tile_plan(info, base_url) -> IIIFTilePlan | None`
  - Legge `width/height` e tile spec (`tiles[0].width/height/scaleFactors`).
  - Crea un piano per stitchare a **risoluzione piena** (scale_factor=1).

- `stitch_iiif_tiles_to_jpeg(session, base_url, out_path, ...) -> (w,h) | None`
  - Scarica `info.json`.
  - Stima memoria output RGB: `out_w * out_h * 3`.
  - Se supera `max_ram_bytes`, crea un buffer disco `.stitch.raw` + `mmap`.
  - Scrive i tile nel buffer (o su canvas PIL in RAM) e salva JPEG finale.

Obiettivo: evitare crash/memory spike quando l’immagine finale è molto grande.

---

## 9) Studio: viewer, trascrizione, cronologia

File: `iiif_downloader/ui/pages/studio_page/__init__.py` e sotto-moduli.

### 9.1 Selezione documento

- `render_studio_page()`
  - Usa `OCRStorage.list_documents()` per popolare la selectbox.
  - Salva selezione in session state (`studio_doc_id`).
  - Carica paths/metadati/stats e attiva sidebar (metadata, jobs, export, OCR controls).

### 9.2 Viewer immagine

- `iiif_downloader/ui/components/viewer.py` → `interactive_viewer(image, zoom_percent)`
  - Converte in JPEG base64 alla qualità `images.viewer_quality`.
  - Renderizza un iframe HTML/JS con pan/zoom (wheel + pulsanti).

### 9.3 Editor trascrizione

File: `iiif_downloader/ui/pages/studio_page/canvas.py`

- `render_transcription_editor(doc_id, library, current_p, ocr_engine, current_model)`
  - Carica trascrizione pagina da `OCRStorage`.
  - Editor basato su `st.form` con `text_area`.
  - Salva in `transcription.json` con `is_manual=True` e mostra toast.
  - Stato pagina: `draft` / `verified`.
  - “Nuova chiamata OCR” gestisce sovrascrittura con conferma se esiste testo.

### 9.4 Cronologia

- `OCRStorage.save_history(...)` salva snapshot su `history/p####_history.json`.
- UI: `render_history_sidebar(...)`
  - Elenca versioni, differenza caratteri, ripristino (restore) con snapshot di sicurezza.

---

## 10) OCR/HTR

File: `iiif_downloader/ocr/processor.py`

### 10.1 Entry point unificato

- `OCRProcessor.process_page(image, engine, model, status_callback)`
  - Instrada la richiesta al provider selezionato.

### 10.2 Provider

- Kraken (`KrakenProvider`)
  - Binarizzazione → segmentazione → predizione.
  - Restituisce righe con confidence e box quando disponibili.

- OpenAI (`OpenAIProvider`)
  - Converte immagine in base64 JPEG.
  - Chiama `OpenAI().chat.completions.create` con prompt per trascrizione diplomatica.

- Anthropic (`AnthropicProvider`)
  - Invia immagine base64 come blocco `image` + prompt.

- Google Vision (`GoogleVisionProvider`)
  - Usa endpoint `images:annotate` con DOCUMENT_TEXT_DETECTION.

- HuggingFace (`HFInferenceProvider`)
  - Chiama Inference API; se Kraken disponibile tenta segmentazione per riga.

### 10.3 OCR in Studio

File: `iiif_downloader/ui/pages/studio_page/ocr_utils.py`

- `run_ocr_sync(...)`
  - OCR singola pagina con `st.status` e progress tramite callback.
  - Salvataggio su storage e “pending update” per aggiornare UI senza warning Streamlit.

- `run_ocr_batch_task(...)`
  - OCR di tutte le immagini `pag_*.jpg`.
  - Usato come job background tramite `job_manager`.

---

## 11) Ricerca globale

File: `iiif_downloader/ui/search.py`

- `render_search_page()`
  - Cerca stringa in tutte le trascrizioni (`OCRStorage.search_manuscript`).
  - Paginazione via `ui.items_per_page`.
  - “Vai” imposta `nav_override`, `studio_doc_id`, `studio_library`, `studio_page` per aprire lo Studio sulla pagina trovata.

---

## 12) Import PDF e Export PDF

File: `iiif_downloader/pdf_utils.py` e UI in Discovery/Studio.

- Import:
  - `convert_pdf_to_images(pdf_path, output_dir, progress_callback)`
  - Converte in JPG (chunk da 10 pagine) in `scans/`.

- Viewer PDF:
  - `load_pdf_page(pdf_source, page_idx, dpi)`

- Export:
  - `generate_pdf_from_images(image_paths, output_path)`

---

## 13) Background jobs

File: `iiif_downloader/jobs.py`

- `JobManager.submit_job(task_func, ..., job_type)`
  - Esegue `task_func` in thread daemon.
  - Inietta `progress_callback(current, total, msg)` in `kwargs`.
  - Stato job consultabile via `list_jobs(active_only=True)`.

In Studio, la sidebar mostra job attivi (es. OCR batch).

---

## 14) Logging

File: `iiif_downloader/logger.py`

- `setup_logging()`
  - Handler console + `TimedRotatingFileHandler` (rotazione giornaliera).
  - Livello configurato da `settings.logging.level`.
  - Idempotente: evita duplicare handler su rerun Streamlit.

---

## 15) Housekeeping / Pulizia cache

- A startup (in `app.py`) viene invocato:
  - `cleanup_old_files(temp_dir, older_than_days=housekeeping.temp_cleanup_days)`

Scopo: evitare che la cache cresca indefinitamente.

---

## 16) CLI (uso da terminale)

File: `iiif_downloader/cli.py` e `main.py`.

- `python main.py <url_o_manifest_o_viewer>`
- Argomenti principali:
  - `--workers` (concorrenza download)
  - `--clean-cache` (pulisce temp prima del download)
  - `--prefer-images` (forza immagini anche se PDF ufficiale esiste)
  - `--ocr <kraken_model>` (OCR Kraken dopo download)
  - `--create-pdf` (genera PDF da immagini al termine)

Nota: la CLI usa i resolver “classici” (Vatican/Gallica/Oxford/Generic). La UI Discovery usa `resolve_shelfmark()` (più guidata).

---

## 17) Limiti noti e note operative

- Ricerca automatica Oxford: non disponibile (API pubblica rimossa). Occorre incollare UUID/manifest.
- Import PDF: usa PyMuPDF; la qualità/velocità dipendono dal PDF.
- OCR provider: richiedono API key (eccetto Kraken locale) e possono avere costi/limiti.
- Tile stitching: più lento del download diretto `/full`, ma utile quando il server blocca immagini grandi.

---

## 18) Sviluppo e contribuzione (minimo)

- Aggiungere un resolver:
  - implementare `BaseResolver.can_resolve()` + `get_manifest_url()`.
  - registrarlo nella CLI (`iiif_downloader/cli.py`).

- Test:
  - `pytest` (alcuni test sono “skipped” se live).

---

Fine bozza.
