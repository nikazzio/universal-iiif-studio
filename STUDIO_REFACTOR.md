# Studio UI Refactor - Layout 55/45 + Tabs

## Cambiamenti Principali 🎯

### 1. **Layout Ristrutturato**
- ✅ **55% Immagine** (sinistra) + **45% Editor** (destra)
- ✅ Immagine a SINISTRA, editor a DESTRA (invertito rispetto a prima)
- ✅ Navigation **in basso** (non più in alto)

### 2. **Tab System**
- ✅ **Tab Trascrizione**: Editor principale + OCR quick panel
- ✅ **Tab Info**: Metadata manoscritto
- ✅ JavaScript per switch tra tab

### 3. **OCR Semplificato**
- ✅ Solo **OCR pagina singola** (rimosso batch)
- ✅ Engine selector compatto (dropdown + button inline)
- ✅ Nessuna selezione modelli visibile (secondaria)
- ✅ Focus su: **click → OCR → risultato**

### 4. **UI Pulita**
- ✅ Header compatto con titolo + library + page info
- ✅ Textarea grande per trascrizione (focus principale)
- ✅ Feedback inline minimale
- ✅ Bottone "Salva Trascrizione" chiaro

## Struttura HTML

```
┌──────────────────────────────────────────────────────────┐
│  [55% Immagine - Mirador]  │  [45% Tabs]                 │
│  ┌────────────────────────┐ │  ┌─────────────────────────┤
│  │                        │ │  │ Title & Library info    │
│  │    IIIF Viewer         │ │  ├─────────────────────────┤
│  │    (Mirador)           │ │  │ [📝 Trascrizione] [Info]│
│  │                        │ │  ├─────────────────────────┤
│  │                        │ │  │ TAB: Trascrizione       │
│  │                        │ │  │ ┌───────────────────────┤
│  │                        │ │  │ │ OCR: [GPT-4o▼][✨OCR] │
│  │                        │ │  │ ├───────────────────────┤
│  │                        │ │  │ │ <textarea>            │
│  │                        │ │  │ │  Testo...             │
│  │                        │ │  │ │                       │
│  │                        │ │  │ │ </textarea>           │
│  └────────────────────────┘ │  │ │ [💾 Salva]            │
│                              │  │ └───────────────────────┘
├──────────────────────────────────────────────────────────┤
│ NAVIGATION (Bottom)                                      │
│ [← Prev] Pagina 5/100 [Next →]                           │
│ ━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                │
└──────────────────────────────────────────────────────────┘
```

## Files Modificati

### Nuovi:
1. `fasthtml_ui/components/ocr_panel.py` - OCR quick panel semplificato

### Modificati:
1. `fasthtml_ui/routes/studio.py` - Completo rewrite
2. `fasthtml_ui/components/viewer.py` - Semplificato Mirador config

## Mirador Fix

**Problema**: Mirador non si vedeva

**Causa**: Configurazione troppo complessa + container constraints

**Fix**:
```javascript
// Configurazione minimale
{
    id: 'mirador-viewer',
    windows: [{
        manifestId: '/iiif/manifest/...',
        thumbnailNavigationPosition: 'off'  // Disabilitato
    }],
    window: {
        allowFullscreen: false,
        allowMaximize: false,
        defaultView: 'single',
        sideBarOpen: false
    },
    workspaceControlPanel: {
        enabled: false  // Disabilitato per UI pulita
    }
}
```

Container:
```python
Div(
    id="mirador-viewer",
    style="height: 100%; min-height: 500px; position: relative;"
)
```

## Tab System

**JavaScript inline**:
```javascript
function switchTab(tabName) {
    // Hide all
    document.querySelectorAll('.tab-content').forEach(el => 
        el.classList.add('hidden')
    );
    
    // Show selected
    document.getElementById('tab-content-' + tabName)
        .classList.remove('hidden');
    
    // Update button styles
    ...
}
```

**Default**: Tab "Trascrizione" visibile

## OCR Quick Panel

```html
<form hx-post="/api/run_ocr">
  <select>GPT-4o | Claude | Google</select>
  <button>✨ OCR</button>
  <div id="ocr-feedback"></div>
</form>
```

**Feedback**:
- ✅ Success → Auto-reload dopo 1.5s
- ❌ Error → Mostra errore inline
- ⏳ Processing → Spinner

### 5. UI/UX Refinements
- **Editor markdown**: SimpleMDE è ora armato con CSS inline che mette in evidenza pulsanti, toggle preview e la status bar scrivendo font chiari su toolbar leggermente desaturate, quindi l’editor è più leggibile anche con il tema scuro.
- **Toasts flottanti**: `_build_toast` genera messaggi fissi in alto a destra con `requestAnimationFrame` che li anima dentro e poi li dissolve; il contenitore `#studio-toast-holder` è `fixed` per rimanere visibile anche quando si scorre.
- **History live**: La tab storica mostra badge di aggiunte/cancellazioni verdi/rosse, la quantità totale di caratteri e un pulsante di ripristino con conferma; dopo ogni salvataggio viene inserito un trigger HTMX nascosto che ricarica `/studio/partial/history` e può mostrare un banner informativo se il testo non è cambiato.
- **Route helper**: `_history_refresh_trigger` e `build_studio_tab_content` mantengono sincronizzati i polling OCR e i pannelli tab senza script inline dispersivi, potendo così riutilizzare `/studio` e le partials con lo stesso layout.

## Next Steps

Se Mirador ancora non si vede:
1. Controlla console browser per errori JavaScript
2. Verifica che manifest URL sia corretto
3. Testa endpoint `/iiif/manifest/{library}/{doc_id}` manualmente

**Test URL**: `http://localhost:8000/studio?library=Vaticana%20(BAV)&doc_id=Urb.lat.1779`
