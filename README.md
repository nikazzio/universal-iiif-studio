# Vatican Manuscript Downloader

Uno strumento Python semplice e veloce per scaricare manoscritti digitalizzati dalla Biblioteca Apostolica Vaticana (DigiVatLib) e convertirli automaticamente in PDF.

## 🚀 Funzionalità

- **Download Parallelo**: Scarica più pagine contemporaneamente per massimizzare la velocità.
- **Alta Qualità**: Tenta di scaricare sempre la migliore risoluzione disponibile.
- **Ottimizzazione PDF**: Utilizza `img2pdf` per creare PDF senza perdita di qualità e con un basso consumo di RAM.
- **Resilienza**: Sistema di "retry" automatico per gestire eventuali errori di rete momentanei.
- **CLI**: Interfaccia a riga di comando flessibile.

## 📋 Requisiti

- Python 3.7+
- Pip

## 🛠️ Installazione

1. Clona il repository o scarica i file.
2. Crea un virtual environment (consigliato):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Su Linux/Mac
   # oppure
   venv\Scripts\activate     # Su Windows
   ```
3. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```

## 💻 Utilizzo

Il comando base richiede solo l'URL del visualizzatore del manoscritto:

```bash
python3 downloader.py https://digi.vatlib.it/view/MSS_Urb.lat.1779
```

### Opzioni Avanzate

```bash
python3 downloader.py [URL] [OPZIONI]
```

| Opzione | Descrizione | Default |
|Ordinamento|---|---|
| `-o`, `--output` | Nome del file PDF di output | `manuscript.pdf` |
| `-w`, `--workers` | Numero di download simultanei | `4` |
| `-k`, `--keep-temp` | Mantiene la cartella delle immagini scaricate (in `temp_images/<ID>`) | `False` |
| `--clean-cache` | Rimuove completamente la cartella `temp_images` e il suo contenuto | `False` |

## ℹ️ Metadati Automatici
Ogni volta che scarichi un manoscritto, verrà creato automaticamente un file `_metadata.json` (es. `manuscript_metadata.json`) contenente le informazioni principali estratte dalla biblioteca (Titolo, Attribuzione, Data, Link Manifest).

### Esempio Completo

Scarica il manoscritto `Urb.lat.1779`, salvalo come `urbinat_latino.pdf` usando 8 thread per il download:

```bash
python3 downloader.py https://digi.vatlib.it/view/MSS_Urb.lat.1779 -o urbinat_latino.pdf -w 8
```

## ⚠️ Nota
Questo script è stato creato a scopo educativo e di studio personale. Rispettare sempre i termini di servizio della Biblioteca Apostolica Vaticana.
