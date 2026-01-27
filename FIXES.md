# Fix Applicati - Tailwind & Mirador Loading

## Problema 1: `tailwind is not defined`

**Causa**: Il script di configurazione Tailwind veniva eseguito PRIMA che il CDN caricasse la libreria.

**Fix**:
```html
<!-- PRIMA (errato) -->
<script>
  tailwind.config = { ... }  // ❌ tailwind not defined yet
</script>
<script src="cdn.tailwindcss.com"></script>

<!-- DOPO (corretto) -->
<script src="cdn.tailwindcss.com"></script>
<script>
  if (typeof tailwind !== 'undefined') {
    tailwind.config = { ... }  // ✅ safe check
  }
</script>
```

## Problema 2: Mirador CSS 404

**Causa**: Fallback a `/static/mirador/mirador.min.css` che non esisteva.

**Fix**: Rimosso fallback per ora, usiamo solo CDN:
```html
<!-- Solo CDN, nessun fallback locale -->
<link rel="stylesheet" href="https://unpkg.com/mirador@latest/dist/mirador.min.css">
```

**Nota**: Per production, si può scaricare Mirador in `static/` quando necessario.

## Warning: CDN Tailwind in Production

Il warning è normale in development. Per production:

**Opzione A - Usa Tailwind CLI** (raccomandato):
```bash
npm install -D tailwindcss
npx tailwindcss -i ./input.css -o ./static/tailwind.css --watch
```

**Opzione B - PostCSS Plugin** (più configurazione):
```bash
npm install -D tailwindcss postcss autoprefixer
```

Per ora, il CDN va bene per development! 👍

## Test

Ricarica la pagina - gli errori dovrebbero essere risolti:
- ✅ `tailwind is not defined` → Fixed
- ⚠️ CDN warning → Normale in dev, OK
- ✅ Mirador 404 → Fixed (niente più fallback che non esiste)

React DevTools warning di Mirador è normale e innocuo.
