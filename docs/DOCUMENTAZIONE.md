# 📘 Universal IIIF Downloader & Studio – Guida Completa

## 1. Introduzione

Universal IIIF Downloader & Studio è una piattaforma modulare per lo studio di materiali IIIF (manoscritti e libri a stampa).
L'architettura separa nettamente il backend (Python core) dall'interfaccia (FastHTML/HTMX).
L'esperienza utente è quella di una SPA (Single Page Application): `Libreria` è il punto di accesso ai documenti locali e `Studio` è il workspace con Mirador a sinistra e pannelli operativi (Trascrizione, Snippets, History, Visual) a destra.

## 2. Configurazione Dettagliata (`config.json`)

Il file `config.json` è la singola fonte di verità.

### ⚙️ Sistema e Download

Parametri **sempre globali** (valgono per tutte le biblioteche):
* `settings.network.global.max_concurrent_download_jobs`: Numero massimo di download documento in esecuzione contemporanea (default: 2). Gli altri job restano in coda.
* `settings.network.global.connect_timeout_s`: timeout apertura connessione HTTP.
* `settings.network.global.read_timeout_s`: timeout lettura risposta HTTP.
* `settings.network.global.transport_retries`: retry trasporto lato client HTTP.

Parametri **override per biblioteca** (attivi solo con `settings.network.libraries.<lib>.use_custom_policy=true`):
* `workers_per_job`, `min_delay_s`, `max_delay_s`, `retry_max_attempts`, `backoff_base_s`, `backoff_cap_s`, `respect_retry_after`.

* `settings.images.tile_stitch_max_ram_gb`: Limite RAM per l'assemblaggio di immagini IIIF giganti (Tile Stitching).
* `settings.images.probe_remote_max_resolution`: Abilita il probing automatico della risoluzione massima online per pagina.
* `settings.images.download_strategy_mode`: Preset operativo (`balanced`, `quality_first`, `fast`, `archival`, `custom`) che definisce l'ordine dei tentativi size IIIF.
* `settings.images.download_strategy_custom`: Strategia custom (lista size, es. `3000,1740,max`) usata solo quando `mode=custom`.
* `settings.images.iiif_quality`: Segmento quality nelle URL IIIF (`.../quality.jpg`). In generale lasciare `default`; usare `gray/bitonal` solo per casi specifici.
* `settings.images.local_optimize.max_long_edge_px`: lato lungo massimo usato da `Ottimizza scans locali`.
* `settings.images.local_optimize.jpeg_quality`: qualità JPEG usata da `Ottimizza scans locali`.

### 📄 Opzioni PDF (Core + UI Config)

* `settings.pdf.prefer_native_pdf` (default: `true`): se il manifest IIIF espone un PDF nativo (`rendering`), il downloader lo usa come sorgente primaria.
* `settings.pdf.create_pdf_from_images` (default: `false`): se non viene usato un PDF nativo, crea un PDF compilato dalle immagini scaricate.
* `settings.pdf.viewer_dpi` (default: `150`): DPI usati per estrarre le immagini JPG dal PDF nativo per il viewer.
* `settings.pdf.profiles`: catalogo preset PDF avanzati (`balanced`, `high_quality`, `archival_highres`, `lightweight`) con supporto custom globale.
* `settings.pdf.profiles.catalog.<profilo>.image_source_mode`: definisce la sorgente immagini del profilo (`local_balanced`, `local_highres`, `remote_highres_temp`).
* `settings.pdf.profiles.catalog.<profilo>.max_parallel_page_fetch`: limite di fetch parallelo quando il profilo usa il remoto high-res temporaneo.
* `settings.storage.highres_temp_retention_hours`: retention dei file high-res temporanei usati per export avanzati.
* `settings.storage.exports_retention_days`: retention globale degli export PDF salvati.
* `settings.storage.thumbnails_retention_days`: retention della cache miniature usata nel tab Output.
* `settings.storage.auto_prune_on_startup`: se attivo, applica pruning retention all'avvio (export + temp high-res).
* `settings.storage.partial_promotion_mode`: gestione promozione pagine validate da `temp_images` a `scans` (`never` oppure `on_pause`).
* `settings.storage.remote_cache.max_bytes`, `retention_hours`, `max_items`: limiti cache persistente risoluzioni remote.
* `settings.viewer.source_policy.saved_mode`: policy sorgente Studio per item `saved` (`remote_first|local_first`).

Nel pannello **Settings > PDF Export** trovi i controlli con help text esplicativi:
* sub-tab **Predefiniti e copertina**:
  - **Prefer Native PDF**: priorita al PDF della biblioteca se disponibile.
  - **Create PDF from Images**: attiva/disattiva la generazione del PDF compilato in fallback.
  - **PDF Viewer DPI**: qualità estrazione da PDF nativo.
  - **Default PDF Profile**: preset operativo globale.
  - metadati copertina (logo, curatore, descrizione) e default formato/compressione.
* sub-tab **Catalogo Profili**:
  - selettore unico profili con voce `Nuovo profilo...` per creare preset custom;
  - editor completo del profilo (cover/colophon, compression, source mode, lato lungo max, JPEG quality, parallel fetch);
  - toggle **Imposta come default globale**;
  - pulsante rosso **Elimina Profilo**;
  - dopo create/delete/update la pagina viene ricaricata per riallineare subito il catalogo disponibile in Output.

Nel pannello **Settings > Viewer**:
* sub-tab **Zoom**, **Defaults**, **Presets** per separare parametri OpenSeadragon e filtri visivi.

Nel pannello **Settings > Paths & System**:
* sub-tab **Paths & Logging** per directory runtime e logging base;
* sub-tab **Storage & Security** per retention, pruning, test live e CORS.

Nel tab **Studio > Output**:
* in alto visualizzi sempre l'inventario PDF locale gia presente per il documento;
* usi i sub-tab `Crea PDF` / `Job` per separare configurazione e monitoraggio coda;
* nel sub-tab `Crea PDF` il blocco principale e:
  - **Profilo PDF** + pulsante **Gestisci profili** nella stessa riga;
  - pannello override a scomparsa (**Personalizza override per questo job**) da aprire solo quando serve.
* il pulsante finale **Crea PDF** usa:
  - il profilo selezionato;
  - eventuali override compilati nel pannello espanso;
  - lo scope selezionato (`Tutte le pagine` oppure `Solo selezione`).
* la griglia miniature mostra per ogni pagina:
  - risoluzione **Locale** e **Online max** per confronto immediato;
  - azione puntuale **High-Res** per scaricare solo la pagina necessaria.

### 🤖 Motori OCR

Le API key vanno in `api_keys`: `openai`, `anthropic`, `google_vision`, `huggingface`.

* `settings.ocr.ocr_engine`: Seleziona il motore attivo (es. `"openai"` o `"kraken"`).
* `settings.ocr.kraken_enabled`: abilita l'uso esplicito del backend Kraken quando selezionato.

### 🎨 Preferenze UI

* `settings.ui.theme_color`: Colore d’accento per l'interfaccia.
* `settings.ui.toast_duration`: Durata in ms delle notifiche a scomparsa.

## 3. Discovery e Download (Novità v0.7)

Il sistema di download è stato completamente riscritto per essere intelligente e resiliente.

### 🧭 Discovery separata da Download Manager

La pagina Discovery è divisa in due aree:
* **Sinistra**: ricerca/risoluzione manifest e anteprime.
* **Destra**: **Download Manager** con coda, job in esecuzione, errori e retry.

Questo permette di continuare a cercare nuovi manoscritti mentre uno o più download sono in corso.

Prefetch light:
* `Aggiungi item` salva entry DB + `metadata.json` + `manifest.json` locali.
* non avvia il download completo delle scansioni.

### 🔎 Ricerca libera + filtri opzionali

La barra di ricerca Discovery è pensata in stile "standard":
* campo testo ampio (supporta query lunghe, segnature, ID, URL);
* select biblioteca;
* filtro opzionale specifico per Gallica:
  * `Tutti i materiali` (default),
  * `Solo manoscritti`,
  * `Solo libri a stampa`.

Nota: su Gallica i filtri per tipologia vengono applicati localmente sui metadati (`dc:type`) estratti dai record SRU, perché i filtri CQL diretti su `dc.type` non sono sempre affidabili.

### 🛰️ Smart Resolvers

Il campo di ricerca accetta input "sporchi". Il sistema normalizza automaticamente:

* **Vaticana**: `Urb. lat. 123` → `MSS_Urb.lat.123`
* **Gallica**: Accetta Short ID (`bpt6k...`), ARK completi e URL di visualizzazione.
  * Ricerca testuale libera di default.
  * Filtri opzionali per restringere a manoscritti o libri a stampa.
* **Oxford**: Riconosce UUID (case-insensitive) e URL del portale `digital.bodleian`.

### ⚡ Il "Golden Flow" di Download

Quando avvii un download, il sistema decide la strategia migliore:

1. **Controllo PDF Nativo**: Cerca se la biblioteca offre un PDF ufficiale.
   * **Se c'è** e `settings.pdf.prefer_native_pdf=true`: lo scarica e **estrae automaticamente** le pagine in immagini JPG ad alta risoluzione (nella cartella `scans/`). Questo garantisce che lo Studio funzioni anche con i PDF.
   * **Se non c'è**: Scarica le immagini dai server IIIF una per una in area temporanea (`temp_images/{doc_id}`), valida i file e poi li promuove in `scans/` quando la condizione di completezza e soddisfatta.
1. **Generazione PDF opzionale**: Se (e solo se) il download è avvenuto per immagini sciolte, il sistema genera un PDF compilativo solo con `settings.pdf.create_pdf_from_images=true`.

### 🧪 Strategia immagini: come leggere davvero le opzioni

Per ogni pagina, il downloader prova una sequenza di size IIIF e solo in fallback passa al tile stitching:

* `balanced`: `3000 -> 1740 -> max`
* `quality_first`: `max -> 3000 -> 1740`
* `fast`: `1740 -> 1200 -> max`
* `archival`: `max`
* `custom`: usa `settings.images.download_strategy_custom`

La variabile `settings.images.iiif_quality` non cambia la size: cambia il **profilo cromatico richiesto** nel segmento finale URL (`default/color/gray/bitonal/native`).

Indicazioni pratiche:
* usa `default` per la maggior parte dei manoscritti;
* usa `gray` o `bitonal` solo quando serve ridurre peso o forzare B/N per workflow OCR specifici;
* se un server IIIF non supporta una quality, il downloader applica retry/fallback tramite la stessa pipeline di download.

### 🧩 Strategia consigliata per manoscritti molto grandi

Per collezioni con pagine molto pesanti, il flusso consigliato e:
* mantieni nel repository locale una copia **bilanciata** per lavorare veloce in viewer e trascrizione;
* usa il confronto **Locale vs Online max** nel tab `Studio > Output` per capire subito dove manca dettaglio;
* scarica la high-res solo sulle pagine necessarie con il pulsante **High-Res** della miniatura;
* quando serve un PDF finale ad altissima qualita, usa un profilo con `image_source_mode=remote_highres_temp`;
* abilita `cleanup_temp_after_export` nel profilo per eliminare in automatico i temporanei high-res a fine export.

### 🗂️ Staging locale (`temp_images` -> `scans`)

Comportamento runtime attuale:
* le pagine validate possono essere tenute in `temp_images/{doc_id}` finche il documento non e completo;
* i retry segmentati (`Retry missing` / `Retry range`) conteggiano anche le pagine gia validate in temp, quindi il sistema converge correttamente alla promozione finale;
* la policy `settings.storage.partial_promotion_mode` controlla una promozione anticipata:
  - `never` (default): promozione solo quando il gate di completezza e soddisfatto;
  - `on_pause`: quando metti in pausa un job running, le pagine validate vengono promosse in `scans`; le scansioni esistenti vengono sovrascritte solo nei flussi espliciti di refresh/ridownload.

Resume:
* il resume considera sia `scans/` sia `temp_images/{doc_id}` per capire cosa manca davvero;
* questo evita duplicazioni e riparte solo dalle pagine effettivamente mancanti.

### 📚 Libreria Locale (Local Assets)

Nuova sezione `Libreria`:
* vista **Grid/List** degli asset locali;
* raggruppamento per **biblioteca** e **tipologia** (`manoscritto`, `libro a stampa`, `incunabolo`, `periodico`, `altro`);
* stato per item: `Salvato`, `In download`, `Locale parziale`, `Locale completo`, `Errore`;
* conteggio pagine locali/temporanee sempre visibile nelle card.

Azioni principali:
* **Delete** documento locale;
* **Clean partial** per ripulire download incompleti;
* **Ottimizza scans locali** (lossy in-place su `scans/`, parametrizzata da Settings);
* **Retry missing** (riprende solo le pagine mancanti);
* **Retry range** (intervalli specifici, es. `1-10,15,30-35`).

### 🛡️ Resilienza di Rete

Il downloader ora "imita" un browser reale (Firefox/Chrome) e gestisce le compressioni (Brotli/Gzip) per aggirare i blocchi (WAF) di biblioteche severe come Gallica.

## 4. Funzionalità Studio

Accesso consigliato:
* apri un documento dalla pagina **Libreria** tramite "Apri Studio";
* `/studio` senza `doc_id` e `library` apre il mini-hub **Riprendi lavoro** con gli ultimi contesti Studio persistiti lato server.

### 🖼️ Viewer e Layout

* **Mirador**: Configurato per "Deep Zoom" (`maxZoomLevel` aumentato) per analisi paleografiche dettagliate.
* **Sidebar**: Collassabile (tasto ☰), lo stato persiste tra le sessioni.
* **Navigation**: Slider e pulsanti sincronizzati tra Viewer e Editor.
* **Header stato asset**: in Studio vengono mostrati stato download e badge `Sorgente: Remota/Locale`.

### ℹ️ Tab Info (riordinato)

Il tab `Info` e stato riorganizzato in sub-tab operative:
* **Panoramica**: attributi principali documento (titolo, diritti, pagine, direzione lettura, ecc.).
* **Pagina corrente**: metadati canvas e risorse per la pagina attiva.
* **Metadati e fonti**: provider, `seeAlso`, endpoint manifesto/servizio IIIF.

Dettagli UX attuali:
* i link esterni sono resi con CTA esplicite (`Apri ... ↗`) e non mostrano URL lunghi in chiaro;
* `Canvas ID` e cliccabile in `Pagina corrente` quando il valore e un URL valido;
* `Diritti` in `Panoramica` e cliccabile se il manifest contiene un link licenza;
* i blocchi `Vedi anche` sono responsivi e restano nel viewport anche su schermi stretti.

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
  * `data/local/temp_images/{ID}/`: staging locale delle pagine validate prima della promozione in `scans/`.
  * `data/vault.db`: Database SQLite per lo stato dei job e ricerche globali.

## 6. Troubleshooting

* **Errore "Connection Reset" o 403 su Gallica**:
  * Il tuo IP potrebbe essere stato bloccato temporaneamente. Il sistema ora include un sistema di "Backoff" (attesa esponenziale), ma se il blocco persiste, prova a cambiare rete (es. Hotspot).
* **Overlay OCR bloccato**:
  * Controlla i log (`logs/app.log`). Se il worker Python crasha, l'overlay potrebbe non ricevere il segnale di stop. Ricarica la pagina.
* **PDF scaricato ma Studio vuoto**:
  * Verifica che l'estrazione delle immagini sia avvenuta. Controlla se la cartella `scans/` contiene file `pag_xxxx.jpg`.
* **Pagine presenti solo in `temp_images`**:
  * Comportamento possibile con `partial_promotion_mode=never`: il sistema sta mantenendo staging coerente.
  * Se ti serve disponibilita immediata in Studio dopo pausa, imposta `settings.storage.partial_promotion_mode=on_pause`.
* **`/studio` non apre subito il documento**:
  * È comportamento previsto: senza contesto (`doc_id` + `library`) Studio mostra il mini-hub `Riprendi lavoro`.

## 7. Developer Notes

* **Architecture**: Vedi `docs/ARCHITECTURE.md` per il diagramma dei moduli.
* **Network Layer**: Tutta la logica HTTP è centralizzata in `src/universal_iiif_core/utils.py` (Session, Headers, Retry).
* **Testing**:
  * Unit test offline (Discovery/Gallica): `pytest tests/test_search_gallica_unit.py tests/test_discovery_handlers_resolve_manifest.py`
  * Live test (Rete richiesta): `pytest tests/test_live.py` (Abilitare in config).

## 8. Gestione dei dati locali

- I dati runtime (cartelle `downloads/`, `data/local/`, `logs/`, `temp_images/`) sono ritenuti rigenerabili e restano nel `.gitignore`. Il contenuto di `config.json` è invece trattato come fonte primaria e non viene mai cancellato automaticamente.
- Per cancellare in tutta sicurezza i dati rigenerabili, usa lo script `scripts/clean_user_data.py`. Passa `--dry-run` per vedere cosa verrebbe rimosso, `--yes` per confermare la rimozione e `--include-data-local` solo se devi resettare anche `data/local/models`, `data/local/snippets` o altri componenti generati.
- Lo script usa `universal_iiif_core.config_manager` per risolvere i percorsi configurati; se aggiungi nuove directory runtime, registra sempre il path tramite il manager e aggiornane `.gitignore`.
- Come workflow consigliato prima di una PR: (1) `python scripts/clean_user_data.py --dry-run`, (2) `python scripts/clean_user_data.py --yes`, (3) `pytest tests/`, (4) `ruff check . --select C901` + `ruff format .`. Queste istruzioni sono ripetute anche in `AGENTS.md`.
