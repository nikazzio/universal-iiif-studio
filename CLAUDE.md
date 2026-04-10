@AGENTS.md

## Claude Code — Note Aggiuntive

### Fonti di riferimento

- **Procedura e regole operative**: `AGENTS.md` (sopra)
- **Rationale architetturale**: `docs/ARCHITECTURE.md` — leggere prima di qualsiasi cambiamento strutturale
- **Priorità correnti**: `PRIORITIES.md` — consultare per contestualizzare il lavoro richiesto
- **Config schema**: `docs/CONFIG_REFERENCE.md`

### Vincoli architetturali critici

- `studio_ui/` dipende da `universal_iiif_core/`, mai il contrario — verificare ogni import cross-layer
- Le route in `studio_ui/routes/` orchestrano, non implementano logica — logica va in `universal_iiif_core/`
- Prima di modificare un resolver: leggere `src/universal_iiif_core/resolvers/base.py` e `discovery/contracts.py`
- HTTPClient centralizzato: usare `universal_iiif_core.http_client`, non creare sessioni requests ad hoc

### Memoria persistente

I file in `~/.claude/projects/-home-niki-work-personal-universal-iiif-downloader/memory/` vengono caricati automaticamente all'inizio di ogni sessione. Aggiornare quei file quando si apprendono decisioni o preferenze non evidenti dal codice.
