# Features Inactive Backlog

Questa lista raccoglie opzioni/feature rimosse dalla UI o marcate come inattive durante il refactor dell'issue #46.
L'obiettivo e' evitare opzioni fuorvianti e tenere tracciata una roadmap evolutiva implementabile.

## Rimosse dalla UI (non operative nel runtime attuale)

1. `settings.system.download_workers`
- Motivo rimozione: non collegata alla pipeline download effettiva (si usa il job queue manager).
- Evoluzione proposta: supporto pool separato per download intra-documento con limite dinamico per host.

2. `settings.system.request_timeout`
- Motivo rimozione: timeout runtime gestiti in punti specifici e non da questa chiave globale.
- Evoluzione proposta: unificare timeout HTTP in un client centralizzato con override per provider.

3. `settings.system.ocr_concurrency`
- Motivo rimozione: non agganciata allo scheduler OCR corrente.
- Evoluzione proposta: coda OCR con massimo worker configurabile e priorita'.

4. `settings.pdf.ocr_dpi`
- Motivo rimozione: pipeline attuale usa `viewer_dpi` per estrazione immagini da PDF.
- Evoluzione proposta: distinguere `viewer_dpi` e `ocr_dpi` in passaggi separati (viewer vs OCR preprocessing).

5. `settings.images.ocr_quality`
- Motivo rimozione: non usata nella pipeline OCR effettiva.
- Evoluzione proposta: quality profile OCR (denoise, sharpen, binarization, quality target).

6. `settings.thumbnails.columns`
- Motivo rimozione: layout thumbnails pilotato da CSS grid responsivo, non da setting numerico.
- Evoluzione proposta: preset layout thumbnails (compact/comfortable/research).

7. `settings.thumbnails.paginate_enabled`
- Motivo rimozione: paginazione sempre attiva nello Studio Export.
- Evoluzione proposta: toggle tra infinite scroll e paginazione.

8. `settings.thumbnails.default_select_all`
- Motivo rimozione: selezione gestita esplicitamente via comandi nel pannello export.
- Evoluzione proposta: template operativi di selezione iniziale per workflow ripetitivi.

9. `settings.thumbnails.actions_apply_to_all_default`
- Motivo rimozione: nessuna azione bulk automatica agganciata a questa chiave.
- Evoluzione proposta: modalita' bulk action persistente.

10. `settings.thumbnails.hover_preview_*` e `inline_base64_max_tiles`
- Motivo rimozione: pipeline hover non attiva nella UX corrente.
- Evoluzione proposta: anteprima hover progressive con cache dedicata e budget memoria.

## Nuove feature introdotte al posto delle opzioni inattive

1. Profili PDF avanzati con preset default e custom:
- globali (`settings.pdf.profiles.catalog`)
- override per documento (`settings.pdf.profiles.document_overrides`)

2. Risoluzione trasparente per pagina:
- confronto `online max` vs `locale` nello Studio Export.

3. High-res on-demand:
- download puntuale pagina high-res da UI export.
- export `remote_highres_temp` con staging temporaneo.

## Note implementative per evoluzioni future

1. Introdurre versionamento schema config (`settings.schema_version`) per migrazioni controllate.
2. Aggiungere endpoint diagnostici storage (`/api/storage/report`, `/api/storage/prune`).
3. Valutare cache distribuita `info.json` per ridurre latency su manoscritti molto lunghi.
