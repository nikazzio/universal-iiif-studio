# Changelog

Tutte le modifiche notevoli a questo progetto saranno documentate in questo file.

## [v0.6.0] - 2026-01-23

### Added

- Feat snippet sqlite (#6)

### Fixed

- Move runtime data directory from `var/` to `data/local/` and serve snippets from `/assets/snippets/` (chore/docs) (#15)

## [v0.5.0] - 2026-01-19

### Added

- **Rich Text Editor**: Sostituito il vecchio editor di testo con un editor RTF avanzato (basato su un wrapper Quill dedicato).
  - Supporto per formattazione (Grassetto, Corsivo, Sottolineato).
  - Elenchi puntati e numerati.
  - Apici e pedici.
  - Salvataggio ibrido (HTML per visualizzazione, Plain Text per indicizzazione).
- **History Restoration**: Migliorato il ripristino dalla cronologia per supportare correttamente il formato RTF.

### Changed

- **Logging**: Refactoring completo del sistema di logging. Ora utilizzo un setup centralizzato (`get_logger`) invece di chiamate dirette, migliorando la leggibilità dei log e il debug.
- **Config**: Migliorata la gestione delle dipendenze e degli import per evitare conflitti circolari.

### Fixed

- Risolti conflitti di merge critici durante l'integrazione del branch `add-rich-text`.
- Corretti bug minori nella gestione degli stati di sessione della UI legacy durante il salvataggio.

## [v0.4.0]

### Added

- **Import PDF Locale**: Funzionalità per importare file PDF direttamente nella cartella `downloads/Local`, con estrazione automatica delle immagini.
- **UI Rimasterizzata**: Nuovo layout per lo Studio Page con sidebar collassabile e navigazione migliorata.
- **Ricerca Globale**: Nuova pagina per cercare stringhe di testo attraverso tutte le trascrizioni salvate.

### Changed

- Migliorato il sistema di notifiche UI.
- Ottimizzazione performance per il caricamento di immagini ad alta risoluzione.
