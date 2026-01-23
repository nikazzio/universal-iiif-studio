# 📜 Universal IIIF Downloader & Studio (v0.5.1)

Uno strumento **professionale** e modulare per scaricare, organizzare e studiare manoscritti digitali. Supporta biblioteche IIIF (Vaticana, Bodleian, Gallica), importazione di PDF locali e offre un ambiente di studio avanzato con **OCR/HTR integrato** e **workflow di correzione manuale**.

## 📚 Documentazione

- Guida/feature (bozza iniziale): [docs/DOCUMENTAZIONE.md](docs/DOCUMENTAZIONE.md)
- Architettura del progetto: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Changelog completo: [CHANGELOG.md](CHANGELOG.md)

## 🚀 Nuove Funzionalità (v0.5.1)

- **📝 Rich Text Editor**: Nuovo editor di trascrizione con supporto per **grassetto**, *corsivo*, elenchi puntati/numerati, apici/pedici e formattazione avanzata.
- **✂️ Sistema Snippet**: Ritaglia e annota porzioni di immagini direttamente nello Studio:
  - Strumento di ritaglio interattivo con anteprima live
  - 8 categorie predefinite (Capolettera, Glossa, Abbreviazione, Dubbio, Illustrazione, Decorazione, Nota Marginale, Altro)
  - Trascrizione rapida e note per ogni snippet
  - Galleria filtrata per pagina con visualizzazione miniature
  - Database SQLite per gestione metadati
- **🗄️ Database Vault**: Nuovo sistema di persistenza centralizzato per snippet e metadati utente (SQLite)
- **🛡️ Stabilità & Logging**: Refactoring completo del sistema di logging per un debug più pulito e gestione errori migliorata.
- **🤖 OCR Ottimizzato**: Migliore integrazione con i modelli OCR e gestione più robusta dei risultati.

### Versioni Precedenti (v0.4.0)

- **🖥️ UI Rimasterizzata**: Nuova navigazione moderna con sidebar "Pro", temi chiari/scuri e layout responsivo.
- **📥 Import PDF Locale**: Carica i tuoi documenti PDF nello Studio, estrai automaticamente le immagini e trattali come manoscritti IIIF.
- **🔍 Ricerca Globale**: Cerca parole o frasi in *tutti* i testi trascritti nella tua libreria locale.

## 📋 Requisiti

- **Python 3.10+**
- Nessuna dipendenza di sistema per l'import PDF (usa **PyMuPDF**)

## 🔧 Installazione Rapida

```bash
# 1. Clona e entra
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

Lancia l'applicazione Web (metodo raccomandato):

```bash
streamlit run app.py
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
downloads/          # Manoscritti scaricati
├── Vaticana/
│   └── MSS_Urb.lat.1779/
├── Local/
│   └── My_Research_Paper/
└── ...

assets/             # Risorse generate dall'utente
└── snippets/       # Ritagli immagini salvati (PNG)

data/               # Database e storage
└── vault.db        # SQLite: metadati snippet

logs/               # File di log applicazione
models/             # Modelli OCR/HTR (Kraken)
temp_images/        # Cache temporanea
```

### Database Vault (`data/vault.db`)

Database SQLite che contiene:

- **Tabella `snippets`**: metadati dei ritagli immagine (categoria, trascrizione, note, coordinate, timestamp)
- **Tabella `manuscripts`**: riferimenti ai manoscritti nella libreria

I file fisici degli snippet sono salvati in `assets/snippets/` con formato: `{ms_name}_p{page:04d}_{timestamp}.png`

## 🛠️ Stack Tecnologico

- **Frontend**: Streamlit + `streamlit-antd-components` + `streamlit-quill` (RTF editor) + `streamlit-cropper` (ritaglio immagini).
- **Backend IO**: `requests`, **PyMuPDF (fitz)**, Pillow.
- **Database**: SQLite3 (via `iiif_downloader.storage.VaultManager`).
- **OCR/AI**: `kraken` (locale), `openai`, `anthropic`, Google Vision, HuggingFace.

## 🤝 Contribuire

Il progetto è open-source. Le Pull Request per nuovi resolver di biblioteche sono benvenute!

## 📄 Licenza

MIT License.
