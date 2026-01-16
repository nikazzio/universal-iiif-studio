# 📜 Universal IIIF Downloader & Studio

Uno strumento **professionale** e modulare per scaricare e studiare manoscritti da qualsiasi biblioteca IIIF (Vaticana, Bodleian, Gallica, ecc.). Il sistema organizza automaticamente i download in una libreria strutturata e offre un'interfaccia di studio avanzata con OCR/HTR integrato.

## 🚀 Funzionalità Principali

- **Discovery & Search**: Cerca direttamente nei cataloghi di **Gallica** (BnF) o risolvi segnature **Vaticana** e **Oxford**
- **Download Intelligente**: Supporto IIIF v2/v3 con retry automatico, rate limiting e stealth mode per BAV
- **Storage Document-Centric**: Organizzazione automatica in `downloads/<Biblioteca>/<ID_Manoscritto>/`
- **Interactive Viewer**: Zoom 400%, drag-to-pan, visualizzazione a schermo intero
- **Multi-Engine OCR/HTR**: Integrazione con Kraken, Claude, GPT e Hugging Face
- **Ricerca Globale**: Full-text search in tutti i manoscritti trascritti
- **Logging Strutturato**: Log organizzati per data in `logs/YYYY-MM-DD/`

## 📋 Requisiti

- **Python 3.10+**
- **Poppler** (per estrazione immagini da PDF): 
  - Ubuntu/Debian: `sudo apt-get install poppler-utils`
  - macOS: `brew install poppler`

## 🔧 Installazione

### 1. Clona il Repository

```bash
git clone https://github.com/yourusername/universal-iiif-downloader.git
cd universal-iiif-downloader
```

### 2. Crea un Virtual Environment (Consigliato)

```bash
# Crea l'ambiente virtuale
python3 -m venv .venv

# Attiva l'ambiente
# Su Linux/macOS:
source .venv/bin/activate
# Su Windows:
# .venv\Scripts\activate
```

### 3. Installa le Dipendenze

```bash
pip install -r requirements.txt
```

### 4. (Opzionale) Configura OCR

Per usare l'OCR con Kraken, installa i modelli:

```bash
# OCR per manoscritti medievali latini
python3 -m iiif_downloader.ocr.model_manager list
python3 -m iiif_downloader.ocr.model_manager install htr-default
```

Per usare Claude/GPT, crea un file `.env` (copia da `.env.example`) e aggiungi le API keys.

## 💻 Utilizzo

### Web UI (Streamlit) - Raccomandato

L'interfaccia grafica per la ricerca, visualizzazione e trascrizione:

```bash
streamlit run app.py
```

Poi apri il browser su `http://localhost:8501`

**Funzioni dello Studio**:
- **Scopri**: Cerca nei cataloghi o risolvi segnature
- **Visualizza**: Viewer interattivo con zoom e pan
- **Trascrivi**: OCR pagina per pagina con modelli AI
- **Ricerca**: Full-text search nei manoscritti trascritti

### CLI (Command Line)

Per download batch o script automatizzati:

```bash
# Download semplice via URL
python3 main.py https://digi.vatlib.it/view/MSS_Urb.lat.1779

# Download via Segnatura Vaticana (normalizzazione automatica)
python3 main.py "Urb. Lat. 1779"

# Download con OCR batch
python3 main.py <URL> --ocr "magistermilitum/tridis_v2_HTR_historical_manuscripts"

# Modalità Wizard (interattiva)
python3 main.py
```

#### Opzioni CLI Principali

```
-o, --output       Nome output (auto-generato se omesso)
-w, --workers      Thread paralleli (default: 4)
--prefer-images    Forza download immagini anche con PDF nativo
--ocr              Modello OCR da usare
--skip-pdf         Scarica solo immagini senza generare PDF
```

## 📁 Struttura della Libreria

Ogni download crea una struttura organizzata:

```text
downloads/
├── Vaticana/
│   └── MSS_Urb.lat.1779/
│       ├── MSS_Urb.lat.1779.pdf
│       ├── metadata.json
│       ├── transcription.json
│       └── pages/
│           ├── pag_0001.jpg
│           ├── pag_0002.jpg
│           └── ...
├── Gallica/
│   └── BnF_Dante_Il_Convito/
│       └── ...
└── Bodleian/
    └── ...
```

## 🔍 Biblioteche Supportate

| Biblioteca | Search API | Risoluzione ID | Note |
|-----------|-----------|---------------|------|
| **Vaticana (BAV)** | ❌ | ✅ | Supporta segnature (es. `Urb.lat.1779`) |
| **Gallica (BnF)** | ✅ | ✅ | API SRU ufficiale, prefissi: `btv`, `bpt`, `cb`, `cc` |
| **Bodleian (Oxford)** | ❌ | ✅ | Solo UUID (API search deprecata Jan 2026) |
| **Altre IIIF** | ❌ | ✅ | Qualsiasi URL manifest IIIF v2/v3 |

## 🐛 Debug e Logging

Il sistema crea log strutturati in `logs/YYYY-MM-DD/`:

```bash
# Abilita logging DEBUG
export IIIF_LOG_LEVEL=DEBUG
streamlit run app.py

# Visualizza log download specifico
cat logs/2026-01-16/download_MSS_Urb_lat_1779_143015.log
```

## 🧪 Test

Esegui i test di robustezza:

```bash
# Test resolver (Gallica, Oxford, Vaticana)
python3 -m tests.test_resolvers_robustness

# Test discovery funzionale
python3 -m tests.test_discovery_resolvers

# Test download live (2-3 pagine per biblioteca)
python3 -m tests.test_live
```

## 📝 Esempi di Uso

### Esempio 1: Scarica un Codice Vaticano

```bash
# Via CLI
python3 main.py "Urb.lat.1779"

# Via Web UI
# 1. Seleziona "Vaticana (BAV)"
# 2. Inserisci "Urb.lat.1779" 
# 3. Click "Analizza" -> "Scarica"
```

### Esempio 2: Cerca e Scarica da Gallica

```bash
# Via Web UI
# 1. Seleziona "Gallica (BnF)"
# 2. Metodo: "Cerca nel Catalogo"
# 3. Cerca "Dante"
# 4. Scegli risultato e scarica
```

### Esempio 3: OCR di un Manoscritto

```bash
# Via CLI con modello Kraken
python3 main.py <URL> --ocr "htr-default"

# Via Web UI: sezione "Trascrizione"
# Carica pagine e seleziona modello OCR
```

## 🤝 Contribuire

I contributi sono benvenuti! Per bug report o feature request, apri una issue su GitHub.

## 📄 Licenza

MIT License - vedi `LICENSE` per dettagli.

---

*Ottimizzato per Digital Humanities e Paleografia.*
