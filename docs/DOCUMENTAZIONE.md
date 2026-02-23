# 📘 Universal IIIF Downloader & Studio – Guida Completa

## 1. Introduzione

Universal IIIF Downloader & Studio è una piattaforma modulare per lo studio di manoscritti digitali.
L'architettura separa nettamente il backend (Python core) dall'interfaccia (FastHTML/HTMX).
L'esperienza utente è quella di una SPA (Single Page Application): `/studio` serve la UI con Mirador a sinistra e i pannelli operativi (Trascrizione, Snippets, History, Visual) a destra, aggiornati dinamicamente senza ricaricamenti.

## 2. Configurazione Dettagliata (`config.json`)

Il file `config.json` è la singola fonte di verità.

### ⚙️ Sistema e Download

* `settings.system.download_workers`: Numero di thread per il download parallelo delle immagini (default: 4).
* `settings.images.tile_stitch_max_ram_gb`: Limite RAM per l'assemblaggio di immagini IIIF giganti (Tile Stitching).

### 📄 Opzioni PDF (Core + UI Config)

* `settings.pdf.prefer_native_pdf` (default: `true`): se il manifest IIIF espone un PDF nativo (`rendering`), il downloader lo usa come sorgente primaria.
* `settings.pdf.create_pdf_from_images` (default: `false`): se non viene usato un PDF nativo, crea un PDF compilato dalle immagini scaricate.
* `settings.pdf.viewer_dpi` (default: `150`): DPI usati per estrarre le immagini JPG dal PDF nativo per il viewer.
* `settings.pdf.ocr_dpi` (default: `300`): DPI consigliati per pipeline OCR.

Nel pannello **Settings > OCR & PDF** trovi gli stessi controlli con help text esplicativi:
* **Prefer Native PDF**: priorita al PDF della biblioteca se disponibile.
* **Create PDF from Images**: attiva/disattiva la generazione del PDF compilato in fallback.
* **PDF Viewer DPI** e **PDF OCR DPI**: qualità estrazione/processing.

### 🤖 Motori OCR

Le API key vanno in `api_keys`: `openai`, `anthropic`, `google_vision`, `huggingface`.

* `settings.ocr.ocr_engine`: Seleziona il motore attivo (es. `"openai"` o `"kraken"`).

### 🎨 Preferenze UI

* `settings.ui.theme_color`: Colore d’accento per l'interfaccia.
* `settings.ui.toast_duration`: Durata in ms delle notifiche a scomparsa.

## 3. Discovery e Download (Novità v0.7)

Il sistema di download è stato completamente riscritto per essere intelligente e resiliente.

### 🛰️ Smart Resolvers

Il campo di ricerca accetta input "sporchi". Il sistema normalizza automaticamente:

* **Vaticana**: `Urb. lat. 123` → `MSS_Urb.lat.123`
* **Gallica**: Accetta Short ID (`bpt6k...`), ARK completi e URL di visualizzazione.
* **Oxford**: Riconosce UUID (case-insensitive) e URL del portale `digital.bodleian`.

### ⚡ Il "Golden Flow" di Download

Quando avvii un download, il sistema decide la strategia migliore:

1. **Controllo PDF Nativo**: Cerca se la biblioteca offre un PDF ufficiale.
   * **Se c'è** e `settings.pdf.prefer_native_pdf=true`: lo scarica e **estrae automaticamente** le pagine in immagini JPG ad alta risoluzione (nella cartella `scans/`). Questo garantisce che lo Studio funzioni anche con i PDF.
   * **Se non c'è**: Scarica le immagini dai server IIIF una per una.
2. **Generazione PDF opzionale**: Se (e solo se) il download è avvenuto per immagini sciolte, il sistema genera un PDF compilativo solo con `settings.pdf.create_pdf_from_images=true`.

### 🛡️ Resilienza di Rete

Il downloader ora "imita" un browser reale (Firefox/Chrome) e gestisce le compressioni (Brotli/Gzip) per aggirare i blocchi (WAF) di biblioteche severe come Gallica.

## 4. Funzionalità Studio

### 🖼️ Viewer e Layout

* **Mirador**: Configurato per "Deep Zoom" (`maxZoomLevel` aumentato) per analisi paleografiche dettagliate.
* **Sidebar**: Collassabile (tasto ☰), lo stato persiste tra le sessioni.
* **Navigation**: Slider e pulsanti sincronizzati tra Viewer e Editor.

### 🎚️ Visual Tab

* **Filtri Real-time**: Slider per Luminosità, Contrasto, Saturazione, Tonalità e Inversione.
* **Tecnologia**: I filtri sono applicati via CSS direttamente al Canvas di Mirador, senza modificare i file su disco.
* **Preset**: Modalità "Notte", "Contrasto Elevato" e "Default".

### ✍️ Trascrizione & OCR

* **Editor**: SimpleMDE (Markdown) con toolbar personalizzata.
* **OCR Asincrono**:
  * Cliccando "Run OCR", un worker in background elabora l'immagine.
  * L'overlay "AI in ascolto" fa polling sullo stato ogni 2 secondi.
* **Salvataggio Intelligente**:
  * Il tasto Salva (o Ctrl+S) invia il testo al server.
  * Il sistema calcola il "Diff": se il testo non è cambiato, evita scritture inutili nel DB.
  * Feedback visivo immediato tramite Toast.

### 📜 History

* **Versionamento**: Ogni salvataggio crea uno snapshot.
* **Visualizzazione**: Badge colorati indicano il motore usato (es. "OpenAI", "Manual").
* **Ripristino**: Il tasto `↺ Ripristina` riporta l'editor a una versione precedente.

## 5. Snippets e Dati

* **Snippet**: Ritagli salvati in `data/local/snippets` e indicizzati nel DB SQLite.
* **File System**:
  * `downloads/{Lib}/{ID}/scans/`: Immagini JPG (Sorgente di verità).
  * `downloads/{Lib}/{ID}/data/`: Metadati JSON e trascrizioni.
  * `data/vault.db`: Database SQLite per lo stato dei job e ricerche globali.

## 6. Troubleshooting

* **Errore "Connection Reset" o 403 su Gallica**:
  * Il tuo IP potrebbe essere stato bloccato temporaneamente. Il sistema ora include un sistema di "Backoff" (attesa esponenziale), ma se il blocco persiste, prova a cambiare rete (es. Hotspot).
* **Overlay OCR bloccato**:
  * Controlla i log (`logs/app.log`). Se il worker Python crasha, l'overlay potrebbe non ricevere il segnale di stop. Ricarica la pagina.
* **PDF scaricato ma Studio vuoto**:
  * Verifica che l'estrazione delle immagini sia avvenuta. Controlla se la cartella `scans/` contiene file `pag_xxxx.jpg`.

## 7. Developer Notes

* **Architecture**: Vedi `docs/ARCHITECTURE.md` per il diagramma dei moduli.
* **Network Layer**: Tutta la logica HTTP è centralizzata in `src/universal_iiif_core/utils.py` (Session, Headers, Retry).
* **Testing**:
  * Unit test offline: `pytest tests/test_discovery_resolvers_unit.py`
  * Live test (Rete richiesta): `pytest tests/test_live.py` (Abilitare in config).

## 8. Gestione dei dati locali

- I dati runtime (cartelle `downloads/`, `data/local/`, `logs/`, `temp_images/`) sono ritenuti rigenerabili e restano nel `.gitignore`. Il contenuto di `config.json` è invece trattato come fonte primaria e non viene mai cancellato automaticamente.
- Per cancellare in tutta sicurezza i dati rigenerabili, usa lo script `scripts/clean_user_data.py`. Passa `--dry-run` per vedere cosa verrebbe rimosso, `--yes` per confermare la rimozione e `--include-data-local` solo se devi resettare anche `data/local/models`, `data/local/snippets` o altri componenti generati.
- Lo script usa `universal_iiif_core.config_manager` per risolvere i percorsi configurati; se aggiungi nuove directory runtime, registra sempre il path tramite il manager e aggiornane `.gitignore`.
- Come workflow consigliato prima di una PR: (1) `python scripts/clean_user_data.py --dry-run`, (2) `python scripts/clean_user_data.py --yes`, (3) `pytest tests/`, (4) `ruff check . --select C901` + `ruff format .`. Queste istruzioni sono ripetute anche in `AGENTS.md`.
