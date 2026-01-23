# 🏗️ Architettura del Progetto

## Overview

Universal IIIF Downloader & Studio è organizzato in moduli logici separati per massimizzare manutenibilità e testabilità.

## 📦 Struttura Moduli

```
iiif_downloader/
├── logic/              # Business Logic
│   └── downloader.py   # Download IIIF tiles/images
├── resolvers/          # Library-Specific Adapters
│   ├── base.py         # Abstract resolver
│   ├── vatican.py      # Biblioteca Vaticana
│   ├── gallica.py      # Gallica BnF
│   ├── oxford.py       # Bodleian Libraries
│   └── generic.py      # Fallback IIIF generico
├── ocr/                # OCR/HTR Engine Layer
│   ├── model_manager.py
│   ├── processor.py
│   └── storage.py
├── storage/            # Persistence Layer
│   └── vault_manager.py # SQLite database (snippet, metadata)
├── ui/                 # Streamlit UI
│   ├── components/     # Reusable widgets
│   ├── pages/          # App pages
│   │   ├── studio_page/     # Studio modularizzato
│   │   │   ├── canvas_refactored.py
│   │   │   ├── sidebar_refactored.py
│   │   │   ├── image_viewer.py
│   │   │   ├── text_editor.py
│   │   │   ├── image_processing.py
│   │   │   └── studio_state.py
│   │   └── export_studio/
│   └── state.py        # Global state management
├── config_manager.py   # Configuration handling
├── logger.py           # Centralized logging
├── pdf_utils.py        # PDF operations
├── iiif_tiles.py       # IIIF tile stitching
└── utils.py            # Shared utilities
```

## 🔄 Data Flow

### 1. Download Workflow

```
User Input (segnatura/URL)
    ↓
Resolver (vatican/gallica/oxford)
    ↓ (manifest IIIF)
Downloader Logic
    ↓ (download parallelo)
Local Storage (downloads/{library}/{manuscript})
```

### 2. Studio Workflow

```
Document Selection
    ↓
State Management (studio_state.py)
    ↓
Image Viewer ← → Text Editor ← → Storage
    ↓                ↓              ↓
Adjustments      History       VaultManager
Cropping         OCR           (SQLite)
Snippets         Verify
```

### 3. OCR/HTR Workflow

```
Page Image
    ↓
OCR Processor
    ↓ (API: OpenAI/Anthropic/Google/HF)
    ↓ (Locale: Kraken)
Transcription JSON
    ↓
Storage (local JSON + rich_text)
    ↓
Text Editor (Quill RTF)
```

## 🗄️ Storage Layer

### VaultManager (`storage/vault_manager.py`)

Gestisce persistenza SQLite per:

**Tabella `snippets`:**

```sql
CREATE TABLE snippets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ms_name TEXT NOT NULL,
    page_num INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    category TEXT,
    transcription TEXT,
    notes TEXT,
    coords_json TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Metodi principali:**

- `save_snippet()` - Salva ritaglio immagine con metadati
- `get_snippets(ms_name, page_num)` - Recupera snippet filtrati
- `delete_snippet(id)` - Elimina snippet (DB + file fisico)

### File Storage

**Trascrizioni**: `downloads/{library}/{manuscript}/data/`

- `transcription.json` - Storico OCR con metadati
- `metadata.json` - Manifest IIIF

**Snippet**: `assets/snippets/`

- Formato: `{ms_name}_p{page:04d}_{timestamp}.png`

**Database**: `data/vault.db`

## 🎨 UI Architecture (Streamlit)

### Separazione Concerns

**Studio Page** è modulare:

1. **canvas_refactored.py** - Orchestrazione layout
2. **image_viewer.py** - Colonna sinistra (immagine + tools)
3. **text_editor.py** - Colonna destra (editor + tabs)
4. **sidebar_refactored.py** - Sidebar (selezione documento + OCR)
5. **studio_state.py** - State management centralizzato
6. **image_processing.py** - Pure functions (brightness/contrast/crop)

### State Management

**Session State** (Streamlit):

- Pagina corrente, documento selezionato
- Regolazioni immagine (brightness/contrast)
- Modalità ritaglio attiva/disattiva

**Persistent State** (VaultManager):

- Snippet salvati
- Metadata manoscritti

## 🔌 Resolver Pattern

Ogni biblioteca ha un resolver dedicato che implementa:

- `resolve(query)` - Converte segnatura → manifest URL
- `get_metadata(manifest_url)` - Estrae info dal manifest
- `get_image_urls(manifest)` - Lista URL immagini

Vantaggi:

- ✅ Aggiungere nuove biblioteche senza toccare core logic
- ✅ Fallback a resolver generico IIIF
- ✅ Testing isolato per ogni resolver

## 🧪 Testing Strategy

```
tests/
├── test_resolvers_robustness.py  # Test resolver per ogni biblioteca
├── test_pdf_generation.py        # Test export PDF
├── test_thumbnails.py             # Test generazione miniature
└── conftest.py                    # Fixtures comuni
```

## 🚀 Estensibilità

### Aggiungere una nuova biblioteca

1. Crea `iiif_downloader/resolvers/new_library.py`
2. Estendi `BaseResolver`
3. Implementa `resolve()` e `get_metadata()`
4. Registra in `discovery.py`

### Aggiungere un provider OCR

1. Estendi `ocr/processor.py`
2. Aggiungi logica API nel metodo dedicato
3. Aggiorna UI in `studio_page/sidebar_refactored.py`

### Aggiungere storage backend

1. Crea nuovo file in `storage/`
2. Implementa interfaccia compatibile con `VaultManager`
3. Aggiorna `storage/__init__.py`

## 📊 Diagramma Dipendenze

```
app.py (entry point)
    ↓
ui/ (Streamlit pages)
    ↓
├── logic/ (download)
├── resolvers/ (IIIF adapters)
├── ocr/ (transcription)
├── storage/ (persistence)
└── utils + config + logger
```

## 🔐 Best Practices

1. **Separazione UI/Logic**: UI chiama logic, mai il contrario
2. **Pure Functions**: `image_processing.py` è stateless
3. **State Centralizzato**: `studio_state.py` incapsula session_state
4. **Logging Strutturato**: `logger.py` con livelli DEBUG/INFO/WARNING/ERROR
5. **Config Singola**: Solo `config.json` (no hardcoded paths)

## 🎯 Future Improvements

- [ ] Migration storage layer a SQLAlchemy ORM
- [ ] API REST per automazioni esterne
- [ ] Plugin system per resolver custom
- [ ] Cache distribuito (Redis) per immagini
- [ ] Export in formati TEI/XML
