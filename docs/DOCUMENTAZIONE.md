# 📘 Universal IIIF Downloader & Studio – Guida Completa

## 1. Introduzione

Universal IIIF Downloader & Studio ora espone una SPA-like experience costruita con FastHTML/htmx: `/studio` serve la UI con Mirador a sinistra e i tab (Trascrizione, Snippets, History, Visual, Info) a destra; ogni tab è gestita come un componente HTML ri-renderizzabile tramite HTMX, mantenendo la logica core (download, OCR, storage) nel modulo `iiif_downloader`.

## 2. Configurazione Dettagliata (`config.json`)

### ⚙️ Sistema e Performance
* `settings.system.download_workers`: thread per download paralleli (4-8).
* `settings.images.tile_stitch_max_ram_gb`: controllo RAM per il tile stitching.

### 🤖 Motori OCR
API key settate in `api_keys`: `openai`, `anthropic`, `google_vision`, `huggingface`. Il modulo `ocr.processor` decide il provider in base a `settings.ocr.ocr_engine`.

### 🎨 Preferenze UI
* `settings.ui.theme_color`: colore d’accento usato per bottoni e badge nello Studio.
* `settings.ui.toast_duration`: durata (ms) dei toast floating, usata da `_build_toast` per mostrare salvataggi/errore.

## 3. Funzionalità Studio

### 🖼️ Viewer e layout
* Mirador occupa il 55% sinistro, con configurazione minimale (toolbar disattivata, workspace controls off).
* La parte destra usa tab HTMX per caricare i contenuti senza ricaricare tutta la pagina (`/studio/partial/tabs` + `/studio/partial/history`).

### ✍️ Trascrizione & OCR
* L’editor principale ora usa SimpleMDE: tema scuro, toolbar personalizzate, `forceSync` e `text-area` in readOnly quando OCR è in corso.
* `hx-post="/api/run_ocr_async"` avvia un worker Python; `/api/check_ocr_status` mantiene l’overlay (“AI in ascolto”) visibile fino a esito.
* I toast flottanti (`#studio-toast-holder`) mostrano messaggi success/info/error tramite `_build_toast` e si auto-dismettono dopo qualche secondo.
* `/api/save_transcription` verifica se il testo è cambiato (solo salva se diverso), invia un toast flottante e include un trigger HTMX nascosto che rifà il GET a `/studio/partial/history` (con messaggio informativo quando non serve salvare) per mantenere la scheda History aggiornato senza refresh manuale.

### 📜 History
* I record mostrano badge engine/status, timestamp formattato e snippet di 220 caratteri con diff di caratteri aggiunti/rimossi (+ verde, – rosso).
* Ogni entry ha un pulsante `↺ Ripristina versione` che chiama `/api/restore_transcription`; un history-message/banner conferma l’operazione.

## 4. Snippets e utilities

* La creazione di snippet salva metadata + ritaglio nel vault SQLite e permette di ritrovarli rapidamente nella tab Snippets.
* Lo storage mantiene `transcription.json`, `history/` e `vault.db` per auditing e ripristino.

## 5. Troubleshooting

* **Overlay “AI in ascolto” non sparisce**: controlla i log `fasthtml_ui/routes/studio.py` e la console browser per eventuali errori HTMX; l’overlay si disfa quando `/api/check_ocr_status` risponde con la trascrizione aggiornata.
* **Toast non appaiono**: verifica che `hx-swap-oob` riceva il `Div` con `id="studio-toast-stack"` e che HTMX non filtrino gli script; eventuali errori di script vengono loggati nella console del browser.
* **History non aggiornata**: il trigger nascosto dopo il salvataggio fa una request GET a `/studio/partial/history`; se la tab non cambia, controllare `logs/app.log` per errori o per `info_message` malformato.

## 6. Developer Notes

* Per comprare la guida Architettura aggiornata, leggi `docs/ARCHITECTURE.md`.
* Per aggiungere nuovi tool all’editor, aggiorna `fasthtml_ui/components/studio/transcription.py` (SimpleMDE) e considera di esporre ulteriori toolbar/shortcuts qui.
* Il core OCR resta in `iiif_downloader/ocr`; tutto ciò che riguarda la UI (toasts, overlay, htmx) è in `fasthtml_ui/`.
