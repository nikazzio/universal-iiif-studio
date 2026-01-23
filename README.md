# 📜 Universal IIIF Downloader & Studio (v0.5.1)

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
