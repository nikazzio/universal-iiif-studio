# 📜 Universal IIIF Downloader & Studio (v0.6.0)

Uno strumento **professionale** e modulare per scaricare, organizzare e studiare manoscritti digitali. Supporta biblioteche IIIF (Vaticana, Bodleian, Gallica), importazione di PDF locali e offre un ambiente di studio avanzato con **OCR/HTR integrato** e **workflow di correzione manuale**.

## 📚 Documentazione

- **[Guida Utente & Sviluppatore](docs/DOCUMENTAZIONE.md)**: Manuale completo su funzionalità, configurazione e utilizzo.
- **[Architettura](docs/ARCHITECTURE.md)**: Dettagli tecnici su moduli, flusso dati e struttura del codice.
- **[Changelog](CHANGELOG.md)**: Storico delle modifiche.

## 🚀 Funzionalità Principali

### 🏛️ Discovery & Download
- **IIIF Universale**: Scarica da Biblioteca Vaticana, Gallica (BnF), Bodleian e qualsiasi manifest IIIF generico.
- **Import PDF**: Carica PDF personali trattandoli come manoscritti, con estrazione automatica delle immagini.
- **Resilienza**: Download parallelo, gestione rate-limit e **Tile Stitching** automatico per aggirare i blocchi su immagini ad alta risoluzione.

### 🖼️ Studio Digitale
- **Viewer Interattivo**: Deep zoom, pan e navigazione fluida.
- **Editor Trascrizione**: Editor Rich Text (WYSIWYG) con salvataggio automatico e cronologia versionata per pagina.
- **OCR/HTR Ibrido**:
  - **Locale**: Motore Kraken integrato.
  - **Cloud**: Integrazione API con OpenAI (GPT-4o), Anthropic (Claude 3.5), Google Vision e HuggingFace.
- **✂️ Snippet & Annotazioni**: Ritaglia dettagli visivi (capolettera, glosse), categorizzali e salvali nel database interno.

### 🔍 Gestione & Ricerca
- **Ricerca Globale**: Cerca parole chiave in *tutte* le trascrizioni della tua libreria.
- **Database Vault**: SQLite integrato per la gestione strutturata di metadati e ritagli.
- **Export**: Generazione PDF delle immagini scaricate.

## 📋 Requisiti

- **Python 3.10+**
- Nessuna dipendenza di sistema complessa (usa `PyMuPDF` e librerie pure-python dove possibile).

## 🔧 Installazione Rapida

```bash
# 1. Clona il repository
git clone https://github.com/yourusername/universal-iiif-downloader.git
cd universal-iiif-downloader

# 2. Crea ambiente virtuale
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Installa dipendenze
pip install -r requirements.txt
```

## 💻 Utilizzo

Lancia l'applicazione Web:

```bash
streamlit run app.py
```

### Configurazione
Al primo avvio viene generato un `config.json`. Puoi modificarlo dalla UI (**⚙️ Impostazioni**) o manualmente per inserire le API Key dei provider OCR. Vedi la [Documentazione](docs/DOCUMENTAZIONE.md#2-configurazione-dettagliata-configjson) per i dettagli.
## 🧬 Versioning & Release

Il progetto usa **Semantic Versioning** con **python-semantic-release**.

- I rilasci vengono generati automaticamente su `main` in base ai commit **Conventional Commits**.
- Il tag è nel formato `vX.Y.Z`.
- La versione runtime è esposta in `iiif_downloader.__version__` e mostrata in UI.

Esempi di commit:

```
feat: aggiungi export snippet
fix: gestisci manifest vuoto
feat!: cambia layout dati (breaking)
```

## 🧭 Funzionalità principali

- **Discovery & Download**: risoluzione segnature/URL → anteprima manifest → download in parallelo.
- **Import PDF locale**: salva PDF nella libreria, con estrazione opzionale delle immagini pagina-per-pagina.
- **Studio**: viewer interattivo, editor trascrizione RTF, stato "verificato", cronologia e ripristino.
- **✂️ Snippet & Annotazioni**: ritaglia porzioni di immagini, categorizza, trascrivi e annota per studio dettagliato.
- **OCR/HTR**: Kraken (locale) + provider API (OpenAI/Anthropic/Google/HuggingFace) su singola pagina o batch in background.
- **Ricerca globale**: ricerca full-text nelle trascrizioni locali.
- **Gestione risorse**: limite RAM per stitching IIIF, pulizia automatica cache/temporanei.

Nota importante: il download via immagini **non genera PDF automaticamente**. L'export PDF da immagini avviene solo tramite pulsante nello Studio (o via CLI con flag dedicato). Se il manifest IIIF fornisce un PDF ufficiale, l'app può **scaricarlo come file aggiuntivo**.

## ⚙️ Configurazione (config.json)

L'app usa **una sola fonte di configurazione**: `config.json` (creato automaticamente al primo avvio con valori di default).

- Template: `config.example.json` (versionato)
- Config locale: `config.json` (**non** versionato, è in `.gitignore`)

Puoi modificare tutto direttamente dalla UI in **⚙️ Impostazioni** oppure copiando il template:

```bash
cp config.example.json config.json
```

### Navigazione

- **🛰️ Discovery**: Cerca per segnatura (es. `Urb.lat.1779`) o nel catalogo Gallica; importa PDF locali.
- **🏛️ Studio**: Ambiente di lettura; OCR (singola pagina o intero volume); correzione e validazione trascrizioni.
- **🔍 Ricerca Globale**: Trova occorrenze di testo in tutti i documenti scaricati.

### CLI (Command Line)

Per automazioni batch:

```bash
python3 main.py "Urb.lat.1779" --ocr "kraken"
```

> Nota: la CLI usa `--ocr` per Kraken post-download. I provider OpenAI/Anthropic/Google/HF sono selezionabili dalla UI nello Studio.

## 📁 Struttura Cartelle

```text
downloads/          # Archivio Manoscritti (Immagini, JSON, PDF)
assets/snippets/    # Ritagli salvati
data/vault.db       # Database SQLite
models/             # Modelli OCR Kraken
config.json         # Configurazione locale (non committare!)
```

## 🤝 Contribuire

Il progetto è modulare e pensato per essere esteso. Vedi [ARCHITECTURE.md](docs/ARCHITECTURE.md) per capire come aggiungere nuovi Resolver o Provider OCR.

## 📄 Licenza

MIT License.
