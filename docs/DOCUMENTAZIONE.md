# 📘 Universal IIIF Downloader & Studio - Guida Completa

## 1. Introduzione

Universal IIIF Downloader & Studio è una piattaforma per Digital Humanities che combina la capacità di scaricare manoscritti ad alta risoluzione (via IIIF) con un ambiente di studio ("Studio") per trascrizione e analisi.

Questa guida approfondisce le funzionalità descritte nel README e fornisce dettagli operativi.

## 2. Configurazione Dettagliata (`config.json`)

Mentre `config.example.json` fornisce i default, ecco il significato delle chiavi principali nel tuo `config.json` personale:

### ⚙️ Sistema e Performance
*   `settings.system.download_workers`: Numero di thread paralleli per il download delle immagini (default: 4-8).
*   `settings.images.tile_stitch_max_ram_gb`: Limite RAM (es. 1.0 GB) per l'assemblaggio di immagini enormi. Se superato, il sistema usa la memoria su disco (mmap).

### 🤖 Motori OCR
Le chiavi API devono essere inserite qui. Non committare mai questo file!
*   `api_keys.openai`: Per GPT-4o ("gpt-4o", "gpt-4-turbo").
*   `api_keys.anthropic`: Per Claude 3.5 Sonnet (eccellente per paleografia).
*   `api_keys.google_vision`: Richiede il JSON del service account path o la stringa JSON.

### 🎨 Preferenze UI
*   `settings.ui.theme_color`: Colore accento Streamlit (default `#FF4B4B`).
*   `settings.ui.toast_duration`: Durata notifiche (ms).

## 3. Funzionalità Studio

### 🖼️ Viewer Interattivo
Il viewer supporta deep zoom e pan.
*   **Controlli**: Rotella mouse per zoom, clic e trascina per pan.
*   **Reset**: Doppio click o pulsante reset.

### ✂️ Sistema Snippet (Ritagli)
Nuova funzionalità v0.5+. Permette di creare un database di dettagli visivi.
1.  **Attiva Ritaglio**: Clicca la checkbox omonima nella sidebar.
2.  **Seleziona**: Disegna un rettangolo sull'immagine.
3.  **Salva**: Appare un pannello sotto la canvas.
    *   **Categoria**: Scegli tra Capolettera, Glossa, Decorazione, ecc.
    *   **Trascrizione**: Campo rapido per il contenuto del ritaglio.
    *   **Note**: Annotazioni paleografiche o stilistiche.
4.  **Galleria**: I ritagli salvati appaiono sotto l'editor di testo, filtrabili per pagina.

### 📝 Editor e OCR
*   **Editor**: WYSIWYG (Rich Text). Salva automaticamente in un formato duale (HTML per visualizzazione, Text per ricerca).
*   **OCR**:
    *   **Singola Pagina**: Pulsante nella sidebar. Aggiorna l'editor in tempo reale.
    *   **Batch**: "Esegui OCR su tutto il manoscritto" lancia un job in background. Segui il progresso nella sidebar "Jobs".

## 4. Importazione PDF (Local Library)
Puoi creare una collezione "Locale" dai tuoi PDF.
1.  Vai in **Discovery** -> **Importa PDF**.
2.  Carica il file.
3.  Il sistema crea una cartella in `downloads/Local/NomeFile/`.
4.  Opzionalmente estrae le immagini (`scans/`) per abilitare lo Studio completo.

## 5. Struttura Dati Avanzata

### Il Vault (`data/vault.db`)
Database SQLite centrale.
*   Non modificare manualmente a meno che tu non sappia usare SQL.
*   Contiene tutti i metadati degli snippet e l'indice dei manoscritti.
*   Backup consigliato: copia periodica del file `data/vault.db`.

### Cartelle Manoscritto
Ogni cartella in `downloads/` è autoconsistente.
*   **`history/`**: Contiene il backup incrementale delle trascrizioni. Utile per recuperare lavoro perso.
*   **`data/transcription.json`**: Il "master file" delle tue trascrizioni. Può essere letto da script esterni per analisi testuale.

## 6. Troubleshooting

### ⚠️ "Memory Error" durante il download
Il server IIIF sta inviando immagini troppo grandi per la RAM.
*   **Soluzione**: Riduci `settings.system.download_workers` a 1 o 2.
*   Il sistema di *tiling* dovrebbe subentrare automaticamente. Verificare i log.

### ⚠️ OCR fallito / Risultati vuoti
*   Verifica la API Key in `config.json`.
*   Controlla i log in `logs/app.log` per messaggi di errore specifici dal provider.

### ⚠️ "Streamlit Session Warning"
Se vedi warning su ID duplicati, è solitamente un glitch benigno durante il ricaricamento a caldo dello sviluppo. Un refresh della pagina risolve.

## 7. Developer Notes

Vedi [ARCHITECTURE.md](ARCHITECTURE.md) per i dettagli interni.
*   Per aggiungere una libreria: `iiif_downloader/resolvers/`.
*   Per modificare il DB: `iiif_downloader/storage/vault_manager.py`.
