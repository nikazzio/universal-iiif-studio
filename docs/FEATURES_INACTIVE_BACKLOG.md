# Features Inactive Backlog

Questa lista raccoglie opzioni/feature rimosse dalla UI o marcate come inattive durante il refactor dell'issue #46.
Obiettivo: evitare opzioni fuorvianti nella configurazione corrente e mantenere una roadmap evolutiva chiara.

## Ambito

- Stato del runtime: riferito all'implementazione attuale in `src/`.
- Stato della UI: riferito ai pannelli Settings/Studio attuali.
- Uso previsto: backlog tecnico per future evoluzioni, non guida utente.

## Feature inattive o rimosse dalla UI

- `settings.system.download_workers`
  - Stato attuale: rimosso dalla UI, non operativo nel runtime corrente.
  - Motivo: la concorrenza download documento e gestita dal job queue manager (`max_concurrent_downloads`).
  - Evoluzione proposta: pool separato per download intra-documento con limite dinamico per host.

- `settings.system.request_timeout`
  - Stato attuale: rimosso dalla UI, non usato come chiave globale centralizzata.
  - Motivo: timeout HTTP gestiti in punti specifici della pipeline.
  - Evoluzione proposta: client HTTP centralizzato con policy timeout uniformi e override per provider.

- `settings.system.ocr_concurrency`
  - Stato attuale: rimosso dalla UI, non agganciato allo scheduler OCR corrente.
  - Motivo: concorrenza OCR non esposta come controllo unico.
  - Evoluzione proposta: coda OCR dedicata con `max_workers`, priorita e retry espliciti.

- `settings.pdf.ocr_dpi`
  - Stato attuale: non esposto in UI; non usato come parametro operativo principale.
  - Motivo: pipeline corrente usa `settings.pdf.viewer_dpi` per l'estrazione immagini da PDF nativo.
  - Evoluzione proposta: separare formalmente `viewer_dpi` (viewer) e `ocr_dpi` (preprocessing OCR).

- `settings.images.ocr_quality`
  - Stato attuale: rimosso dalla UI, non utilizzato dalla pipeline OCR effettiva.
  - Motivo: assenza di un profilo OCR strutturato in runtime.
  - Evoluzione proposta: profili OCR dedicati (denoise, sharpen, binarization, target quality).

- `settings.thumbnails.columns`
  - Stato attuale: rimosso dalla UI.
  - Motivo: layout miniature gestito da CSS grid responsive, non da numero colonne statico.
  - Evoluzione proposta: preset di layout (`compact`, `comfortable`, `research`).

- `settings.thumbnails.paginate_enabled`
  - Stato attuale: rimosso dalla UI.
  - Motivo: paginazione sempre attiva nello Studio Export.
  - Evoluzione proposta: toggle tra paginazione e infinite scroll.

- `settings.thumbnails.default_select_all`
  - Stato attuale: rimosso dalla UI.
  - Motivo: selezione iniziale gestita nel flusso Studio Export (inizializzazione lato pannello).
  - Evoluzione proposta: template di selezione iniziale per workflow ripetitivi.

- `settings.thumbnails.actions_apply_to_all_default`
  - Stato attuale: rimosso dalla UI.
  - Motivo: nessuna azione bulk automatica agganciata a questa chiave.
  - Evoluzione proposta: modalita bulk persistente con conferma operativa.

- `settings.thumbnails.hover_preview_*` e `inline_base64_max_tiles`
  - Stato attuale: rimosso dalla UI.
  - Motivo: pipeline hover preview non attiva nella UX corrente.
  - Evoluzione proposta: hover progressive con cache dedicata e budget memoria.

## Feature introdotte in sostituzione

- Profili PDF avanzati con preset default e custom
  - Chiavi: `settings.pdf.profiles.catalog`, `settings.pdf.profiles.default`.
  - UX: catalogo profili centralizzato in `Settings > PDF Export`.

- Gestione risoluzione trasparente per pagina in Studio Export
  - UI: confronto `Locale` vs `Online max` nelle thumbnail card.
  - Scopo: decidere in modo informato se lavorare su locale bilanciato o richiedere high-res.

- High-res on-demand per export
  - UI: azione puntuale `High-Res` per singola pagina.
  - Runtime: `remote_highres_temp` con staging temporaneo e cleanup opzionale post-export.

## Backlog evolutivo raccomandato

- Introdurre versionamento schema config (`settings.schema_version`) con migrazioni guidate.
- Aggiungere endpoint diagnostici storage (`/api/storage/report`, `/api/storage/prune`).
- Valutare cache distribuita `info.json` per ridurre latenza su manoscritti molto lunghi.
