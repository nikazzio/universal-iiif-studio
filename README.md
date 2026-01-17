# 📜 Universal IIIF Downloader & Studio (v3.1)

Uno strumento **professionale** e modulare per scaricare, organizzare e studiare manoscritti digitali. Supporta biblioteche IIIF (Vaticana, Bodleian, Gallica), importazione di PDF locali e offre un ambiente di studio avanzato con **OCR/HTR integrato** e **workflow di correzione manuale**.

## 🚀 Nuove Funzionalità (v3.1)

- **🖥️ UI Rimasterizzata**: Nuova navigazione moderna con sidebar "Pro", temi chiari/scuri e layout responsivo.
- **📥 Import PDF Locale**: Carica i tuoi documenti PDF nello Studio, estrai automaticamente le immagini e trattali come manoscritti IIIF.
- **✍️ Studio & Correzione**:
    - Editor di trascrizione con salvataggio, verifica e revert.
    - Confronto side-by-side immagine/testo.
    - Supporto OCR ibrido (AI + Kraken).
- **🔍 Ricerca Globale**: Cerca parole o frasi in *tutti* i testi trascritti nella tua libreria locale.

## 📋 Requisiti

- **Python 3.10+**
- **Poppler** (per import PDF):
  - Ubuntu/Debian: `sudo apt-get install poppler-utils`
  - macOS: `brew install poppler`

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

### Navigazione
1.  **🛰️ Discovery**:
    *   **Cerca**: Per segnatura (es. `Urb.lat.1779`) o nel catalogo Gallica.
    *   **Importa PDF**: Carica file dal tuo disco.
2.  **🏛️ Studio**:
    *   Ambiente di lettura immersivo.
    *   Esegui OCR (singola pagina o intero volume).
    *   Correggi, salva e valida le trascrizioni.
3.  **🔍 Ricerca Globale**:
    *   Trova occorrenze di testo in tutti i tuoi documenti scaricati.

### CLI (Command Line)
Per automazioni batch:

```bash
python3 main.py "Urb.lat.1779" --ocr "gpt-4o"
```

## 📁 Struttura Cartelle

```text
downloads/
├── Vaticana/
│   └── MSS_Urb.lat.1779/   # Download IIIF
├── Local/
│   └── My_Research_Paper/  # Import PDF
└── ...
```

## 🛠️ Stack Tecnologico
- **Frontend**: Streamlit + `streamlit-antd-components` + `st-theme`.
- **Backend IO**: `requests`, `iiif-prezi`, `pdf2image`.
- **OCR/AI**: `kraken` (locale), `openai`, `anthropic`.

## 🤝 Contribuire
Il progetto è open-source. Le Pull Request per nuovi resolver di biblioteche sono benvenute!

## 📄 Licenza
MIT License.
