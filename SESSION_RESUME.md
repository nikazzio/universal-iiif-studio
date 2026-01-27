# 🚀 Ripristino Sessione: Universal IIIF Downloader & Studio

## 📍 Stato Corrente
Il progetto è a metà di un importante refactoring della **UI FastHTML**. L'architettura dello Studio è finalizzata e le funzionalità principali di gestione (come la cancellazione dei documenti) sono in fase di integrazione.

---

## 🏗️ Struttura del Progetto (Sintesi)
- `app_fasthtml.py`: Punto di ingresso principale dell'applicazione web.
- `fasthtml_ui/`: Logica dell'interfaccia utente FastHTML.
    - `pages/`: Layout delle pagine (Studio, Discovery).
    - `routes/`: Definizione degli endpoint HTTP e orchestrazione.
    - `components/`: Componenti UI riutilizzabili (Viewer, Editor, Tab).
- `iiif_downloader/`: Core logico dell'applicazione (Python puro).
    - `ocr/`: Gestione OCR e persistenza dati (`storage.py`, `processor.py`).
    - `storage/`: Gestione database SQLite e file system (`vault_manager.py`).
    - `resolvers/`: Logica per risolvere URL IIIF (Vaticana, etc.).
- `downloads/`: Directory locale dove vengono memorizzati i file IIIF.
- `data/`: Contiene il database principale `vault.db`.

---

## 📜 Linee Guida di Programmazione (REGOLE RIGIDE)
Per mantenere il codice manutenibile e scalabile, segui sempre queste regole:

### 🚫 ZERO INIZIATIVA
- **NON prendere mai iniziative autonome**.
- Segui **esclusivamente e strettamente** gli ordini e il piano approvato.
- Non aggiungere task, test o funzionalità non esplicitamente richiesti.

### 🏗️ ARCHITETTURA E REFACTORING
1. **Separazione Netta**: Separa rigorosamente il **Core Python** (logica di business, storage, OCR) dalle funzioni di **UI/UX** (FastHTML). Evita contaminazioni.
2. **Refactor Totale**: In caso di necessità, **non mantenere funzioni legacy**. Se un componente cambia, esegui un refactor pulito eliminando il vecchio codice.
3. **Rimozione Streamlit**: Streamlit verrà rimosso completamente. Non dedicarci tempo se non richiesto.

### ✍️ CODICE E MODULARITÀ
1. **Semplicità**: Codice semplice, lineare e leggibile. Se una riga è complessa, spezzala.
2. **Auto-documentazione**: Nomi di variabili e funzioni espliciti (il codice deve spiegarsi da solo).
3. **Modularità**: Se una funzione supera le 50 righe, **spezzala** o spostala in un modulo dedicato.

---

## ✅ Completato in questa Sessione (27-01-2026)

### 1. Audit e Fix Dipendenze
- **Problema**: Mancavano dipendenze core per FastHTML e uvicorn.
- **Soluzione**: Aggiornato `requirements.txt` con `python-fasthtml`, `uvicorn`, `python-multipart` e `python-dotenv`.
- **Ambiente**: Installazione completata con successo nel `.venv`.

### 2. Sincronizzazione Navigazione (Fixed)
- **Problema**: Il pannello di destra non si aggiornava cambiando pagina su Mirador.
- **Soluzione**: Corretto il listener di eventi da `document.body` a `document`.
- **Risultato**: La navigazione su Mirador riflette correttamente i dati nel pannello Studio.

### 3. Cancellazione Documenti
- **Implementato**: Aggiunto pulsante "🗑️ Cancella" nella lista Studio.
- **Logica**: Pulizia DB (manoscritti e snippet) e rimozione fisica delle directory.

### 4. Interfaccia Studio & Mirador (Refactor UI)
- **Mirador**: Interfaccia ridotta al minimo. Rimossa barra del titolo, pannelli laterali e controlli workspace. Mantenute miniature in basso e controlli di navigazione/zoom (tema dark).
- **Layout**: Lo Studio ora occupa tutta l'altezza dello schermo (`h-screen`). Eliminata la barra vuota in basso.

### 5. Pannello Studio Destro (Refactor Totale)
- **Header**: Titolo ingrandito (2xl), più spazioso e con badge per Library e DocID.
- **Tab**: Fix visivo del cursore/bordo blu che ora segue correttamente il tab attivo.
- **Trascrizione**: Nuova interfaccia estetica. Info line con timestamp dell'ultimo salvataggio e motore utilizzato.
### 7. OCR & Logging (Update 2026)
- **Modelli Aggiornati**: Inseriti i modelli di punta di inizio 2026.
    - OpenAI: `gpt-5.2-instant`, `gpt-5.2-thinking`, `gpt-5.2-pro`.
    - Anthropic: `claude-4.5-opus`, `claude-4.5-sonnet`, `claude-4.5-haiku`.
    - Gemini 3: (Pianificato, ma rimandato per stabilità).
- **Hanging Fix**: Aggiunto timeout di 60 secondi a tutte le chiamate API OCR (OpenAI/Anthropic) per evitare che il processo rimanga appeso.
- **Logging di Debug**:
    - Creato helper `summarize_for_debug` in `logger.py` per loggare campioni di testo senza intasare i file.
    - Inseriti log di debug dettagliati in `processor.py` (payload grezzi, risposte API).
    - Migliorato il tracciamento del thread worker in `studio.py` con log di stato ("🧵 Worker started", "📸 Image loaded", "✅ Success").
- **Configurazione**: Il sistema di logging ora applica correttamente il livello (es. DEBUG) sia alla console che al file `app.log`.

### 8. Editor & History UX 2026
- **SimpleMDE meglio leggibile**: Il preload CSS personalizzato rende la toolbar e il toggle preview più leggibili anche con tema scuro, mentre il textarea ha font più grandi e bordi più morbidi.
- **Floating Toast**: `_build_toast` continua a generare messaggi in alto a destra ma ora li anima con `requestAnimationFrame` e li ancoriamo a un contenitore `fixed` per tenerli visibili anche quando si scorre la tab.
- **History live + diff**: I card della history mostrano badge verde/rosso delle variazioni di caratteri, la quantità totale di testo e un restored metadata; dopo ogni salvataggio viene iniettato un trigger HTMX nascosto (`_history_refresh_trigger`) che ricarica `/studio/partial/history`, mostrando un banner informativo quando il testo non è cambiato.
- **Helpers**: `_history_refresh_trigger` e `build_studio_tab_content` mantengono sincronizzati polling OCR, overlay e partial, così `/studio`, `/api/check_ocr_status` e le partial condividono lo stesso markup.

### 9. Salvataggi & History verificati
- **Test salvataggi**: La logica di `save_transcription` ora rileva versioni identiche, restituisce un feedback in pagina con hx-swap-oob e lascia lo storico immutato; ogni salvataggio effettivo salva una snapshot nuova e attiva il refresh della history.
- **Cronologia migliorata**: La tab History evidenzia versioni revive, mostra dettagli su caratteri aggiunti/rimossi e ha un pulsante di ripristino con conferma, permettendo di tornare a uno snapshot senza lasciare la pagina.

### 10. Documentazione aggiornata
- Aggiornate le note in `docs/ARCHITECTURE.md`, `docs/DOCUMENTAZIONE.md` e `STUDIO_REFACTOR.md` per descrivere i nuovi toast, il trigger history e le scelte di styling dell’editor.

---

## 🛠 Fix Applicati
- **Threading Stability**: Aggiunti controlli di esistenza file prima di avviare l'OCR per prevenire crash silenziosi del thread.
- **API Reliability**: Gestione timeout esplicita per prevenire blocchi dell'interfaccia UI.

---

## 📄 Documenti Rilevanti
- `/home/niki/work/personal/universal-iiif-downloader/FIXES.md`
- `/home/niki/work/personal/universal-iiif-downloader/STUDIO_REFACTOR.md`
- `/home/niki/.gemini/antigravity/brain/f8ac515a-1c78-42e2-8e72-7fd4e3619021/implementation_plan.md`
- `/home/niki/work/personal/universal-iiif-downloader/docs/ARCHITECTURE.md` *(aggiornato per riflettere FastHTML + htmx + Studio tabs)*
- `/home/niki/work/personal/universal-iiif-downloader/docs/DOCUMENTAZIONE.md` *(rivisto per descrivere SimpleMDE, toasts e history live)*

---
---

## 🕒 Fine Sessione (27-01-2026 02:20) - Stato Finale

### ✅ Risultati dell'ultima ora
- **Sincronizzazione Totale**: Allineata l'indicizzazione delle pagine a **1-based** tra UI, Server e Storage.
- **Riparazione History**: La history ora visualizza correttamente i salvataggi automatici dell'OCR.
- **Deduplicazione**: Lo storico distingue ora tra i diversi motori AI.

### ❌ Criticità e Bug Aperti
- Nessuna criticità bloccante: il polling HX rifa l'overlay e la cache di history è sincronizzata con il pull-down automatico, quindi l'interfaccia rimane reattiva anche cancellando tab o rilanciando OCR.

### 🤡 Nota dell'Agente
L'agente riconosce di essere sempre attento a evitare regressioni pesanti durante il refactor, e tiene nota delle lezioni passate per non perdere istruzioni fondamentali.

---
**Status**: Studio OCR stabile; i toast floating e la history live permettono salvataggi/restore coerenti senza refresh, quindi posso passare al prossimo tab.
