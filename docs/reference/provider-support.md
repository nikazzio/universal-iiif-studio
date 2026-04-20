# Provider Support

Scriptoria does not treat "IIIF support" as a binary label. A provider can be supported for direct manifest resolution, partly supported for free-text discovery, strong on record URLs but weak on keyword search, or good for local reading but inconsistent for export-oriented workflows. This page documents the current support model as it exists in the code.

## Current Registry

The shared provider registry currently exposes these providers:

- Vaticana (BAV)
- Gallica (BnF)
- Institut de France (Bibnum)
- Bodleian (Oxford)
- Universitaetsbibliothek Heidelberg
- Cambridge University Digital Library
- e-codices
- Biblioteca Estense (Modena)
- Harvard University
- Library of Congress
- Internet Archive
- Internet Culturale (ICCU) **[BETA]**
- generic direct IIIF manifest URL

These entries come from the runtime provider registry in `src/universal_iiif_core/providers.py`, which is the source used by both UI and shared resolution logic.

## What "Supported" Means Here

For Scriptoria, provider support can include several layers: direct resolution of provider URLs or identifiers to a manifest, free-text search through a provider-specific adapter, provider-specific helper text or browser-search fallbacks, provider-specific network policy for fragile upstream services, and dedicated filters such as the Gallica material-type selector.

Because those layers differ, two supported providers can feel very different in use.

## Practical Search Modes

The code currently uses three search modes.

### `direct`

The provider is mainly treated as a resolver. The best input is an explicit URL, manifest, or identifier. If you only have a vague keyword query, Scriptoria is usually not the best starting point for that provider.

### `fallback`

Scriptoria first tries to resolve explicit input and can fall back to a provider search flow. This is a mixed mode: it can work well, but exact identifiers and URLs are usually still more reliable than exploratory text search.

### `search_first`

The provider has a stronger search-first experience and can reasonably be used for discovery by keyword. This does not remove the value of direct identifiers; it simply means the product-side search surface is a first-class path instead of a last resort.

## Provider Matrix

| Provider | Best first input | Search mode | Practical recommendation |
| --- | --- | --- | --- |
| Vaticana | shelfmark or manifest URL | `fallback` | Start from shelfmark-like references such as `Urb.lat.1779`; direct manifest URLs are also strong |
| Gallica | ARK, record URL, or text query | `search_first` | One of the best discovery-first providers; use filters when needed |
| Institut de France | numeric ID, viewer URL, or text query | `fallback` | Stronger with exact IDs and viewer URLs than with broad free text |
| Bodleian | UUID or record URL | `direct` with search handler | Treat as URL/UUID-driven in normal work |
| Heidelberg | record ID or URL | `fallback` | Free-text search is variable; explicit record references are safer |
| Cambridge | shelfmark or CUDL URL | `fallback` | Similar to Heidelberg; better with shelfmark/URL than with exploratory search |
| e-codices | compound identifier or URL | `direct` with search handler | Best with IDs such as `csg-0001` or a direct e-codices URL |
| Biblioteca Estense (Modena) | text query, pressmark, Jarvis manifest URL or UUID | `search_first` | Native IIIF v2/v3 with level-2 Image API. Search covers short title, author and pressmark together |
| Harvard | DRS-bearing item URL | `fallback` | Usually best treated as URL-driven |
| Library of Congress | public item URL | `fallback` | Prefer `loc.gov/item/...` URLs |
| Internet Archive | item URL or text query | `search_first` | Good discovery-first behavior for many cases |
| Internet Culturale **[BETA]** | text query, OAI ID, or magparser/viewresource URL | `search_first` | Gateway for ~50 Italian libraries (Laurenziana, Marciana, BNCF/BNCR, Estense, Marucelliana, Ambrosiana partners, etc.). Integration is experimental: many upstream records are incomplete and image quality is variable. Use only when ICCU is the only channel available |
| Generic / direct manifest | exact manifest URL | `direct` | Use only when you already have a valid IIIF manifest URL |

## Per-Provider Notes

### Vaticana

Vaticana works best when you already know the shelfmark or have an item-level reference. Scriptoria can search, but the real strength of this provider is explicit catalog-oriented input. If the search surface feels ambiguous, switch immediately to a shelfmark or direct manifest path.

### Gallica

Gallica is one of the strongest providers for discovery-first use in the current product. It supports a more natural keyword workflow, and Scriptoria also exposes a provider-specific material filter. If you are doing exploratory work rather than known-item resolution, Gallica is one of the friendliest sources in the registry.

### Institut de France

Institut de France supports both search and direct resolution, but in practice it behaves better when you already have a stable record reference or numeric identifier. Product-side search is still useful, especially when you know the corpus but not the exact record id.

### Bodleian

Bodleian is operationally strongest as an explicit-resolution provider. Use a UUID or a direct Digital Bodleian URL whenever possible. Search support exists, but the cleanest workflow is still identifier-driven.

### Heidelberg

Heidelberg is supported, but free-text discovery can be uneven. The provider metadata in the code explicitly exposes browser-search guidance for this reason. If you are struggling with product-side discovery, use the Heidelberg catalog in the browser and paste the resulting record id or URL back into Scriptoria.

### Cambridge

Cambridge behaves similarly to Heidelberg. Product-side support exists, but shelfmarks and direct CUDL record URLs remain the more dependable path. For exploratory searching, browser-assisted discovery may still be the most efficient route.

### e-codices

e-codices behaves well with explicit compound identifiers and direct record URLs. If you know the item id, Scriptoria can usually normalize it cleanly.

### Biblioteca Estense (Modena)

The Biblioteca Estense Universitaria in Modena (Biblioteca Estense Digitale / Estense Digital Library) is served by the Jarvis backend at `jarvis.edl.beniculturali.it`. It exposes full native IIIF with **both** Presentation v2 and v3 manifests and a **level-2 Image API** (tile service, zoom, rescaling) — there is no on-the-fly conversion, the manifest is first-class.

Search uses the Spring Data REST endpoint `findBySgttOrAutnOrPressmark`, which covers short title, author, and pressmark in a single call and returns paged results with `totalElements` / `totalPages`. Scriptoria shows this as "Mostrati X di Y risultati" and enables "Carica altri" just like for Internet Archive or Gallica.

Accepted inputs for direct resolution:

- Manifest URL v2: `https://jarvis.edl.beniculturali.it/meta/iiif/{uuid}/manifest`
- Manifest URL v3: `https://jarvis.edl.beniculturali.it/meta/iiif/v3/{uuid}/manifest`
- Mirador viewer wrapper URL on the same host
- A bare item UUID (8-4-4-4-12 hex)

The public `https://edl.beniculturali.it/beu/{id}` URLs are single-page-app links and are not resolved statically: reach the record via search and use the returned manifest/viewer URL.

### Harvard

Harvard support is best understood as URL-driven support. If you have a Harvard IIIF or HOLLIS URL that carries the DRS identifier, use that. Free-text use exists, but it is not the main strength of this provider.

### Library of Congress

Library of Congress is best approached with the public `loc.gov/item/...` page as the canonical starting reference. That path is clearer and more reproducible than generic searching when you already know the record.

### Internet Archive

Internet Archive supports a more discovery-first workflow than many other providers in the registry. It is usually comfortable both for direct item URLs and for broad text search.

### Internet Culturale (ICCU) **[BETA]**

Internet Culturale is the Italian national aggregator run by ICCU. The integration is currently **BETA**: it is good enough to reach content that is otherwise unreachable from Scriptoria, but far from the reliability of native IIIF providers. Treat it as a last-resort channel when no other provider covers the item.

Unlike the other providers in the registry, ICCU does not expose a native IIIF Presentation manifest. Instead, Scriptoria fetches the upstream MAG/XML document (the `jmms/magparser` endpoint) and converts it to a IIIF v2 manifest on the fly. Canvas image URLs come from the real `src` attribute of each `<page>` element — the `/jmms/thumbnail?page=N` endpoint ignores the page parameter and must not be used.

Search is HTML scraping over the advanced search page, paginated with `pag=N` (not `paginate_pageNum`, which the server silently ignores). The parser extracts the total result count and total pages so the UI can show "Mostrati X di Y risultati" and enable "Carica altri". Typical result set sizes are in the thousands.

Known BETA limitations:

- Many ICCU records are "teaser" entries: the MAG XML declares several pages but only the first image is actually served upstream. The downloader applies a partial-finalize mode for ICCU manifests so partial downloads still land correctly in `scans/`, but the user-visible experience is still "you asked for N pages and only got M".
- Image quality and resolution vary widely between teche and between records in the same teca.
- The external viewer path used by Scriptoria is the canonical `/jmms/iccuviewer/iccu.jsp?id=...&mode=all&teca=...`. The older `viewresource` URL renders as a blank page for some teche (BNCF in particular).
- For Mirador-based local reading Scriptoria exposes an internal proxy endpoint, `/api/iccu/manifest?url=...`, that serves the converted manifest as JSON with CORS-friendly headers.
- The ICCU Image API v2.1 does exist at `internetculturale.it/iiif/image/2.1/{id_b64}/...` but is level 0 only (no tile server, no zoom). Static fullsize is the only tier available regardless of which download path is chosen.
- For native IIIF access to Biblioteca Estense records, prefer a dedicated Estense provider (Jarvis backend) when available, rather than going through ICCU.

### Generic Direct Manifest

This path is intentionally simple. It exists for the case where the source is IIIF-compatible but not covered by one of the dedicated resolvers. Scriptoria expects a valid direct manifest URL and does not try to infer provider-specific behavior beyond that.

## Browser-Assisted Search Cases

Two providers deserve a separate operational note: Heidelberg and Cambridge.

In both cases, the registry metadata already assumes that browser-assisted search may be the most reliable path for some queries. That is not a failure of the product model; it is a reflection of the upstream services. Scriptoria keeps those limits visible instead of pretending discovery is equally strong everywhere.

## Provider Filters

The current provider registry exposes two dedicated provider filters:

- `Gallica` — material type (all, manuscripts, printed books).
- `Internet Culturale` **[BETA]** — material type (all, `Manoscritto`, `Libro moderno`, `Musica`, `Fotografia`).

Both filters map directly to server-side parameters and survive pagination, so "Carica altri" preserves the selected material type. More provider-specific filters can be added later, but only when the upstream service and the user workflow justify them.

## How To Choose The Right Input

As a rule, use a direct IIIF manifest URL when you already have one, use provider record URLs when the provider is URL-driven, use shelfmarks or compound identifiers when the corpus is catalog-centric, and reserve free-text search for providers that behave well in discovery-first mode. When a provider is known to be inconsistent from the product UI, switch to browser-assisted search early instead of forcing a weak path.

That is the practical way to avoid frustration across heterogeneous libraries.

## Related Docs

- [Getting Started](../intro/getting-started.md)
- [Discovery And Library](../guides/discovery-and-library.md)
- [Discovery And Provider Model](../explanation/discovery-provider-model.md)
- [Configuration Overview](configuration.md)
- [HTTP Client Notes](../HTTP_CLIENT.md)
