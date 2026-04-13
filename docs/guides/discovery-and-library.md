# Discovery And Library

`Discovery` and `Library` solve different parts of the workflow:

- `Discovery` finds or resolves candidate documents.
- `Library` manages items already known to the local workspace.

Treat them as two distinct layers. Discovery is about external sources and provider behavior. Library is about local state, local paths, and the working copy that Scriptoria maintains on disk.

## Discovery

Discovery accepts:

- direct manifest URLs;
- provider item URLs;
- shelfmarks or supported IDs;
- free-text queries where search adapters exist.

Current behavior:

- `Add item` saves local metadata only;
- result payloads are normalized into shared fields;
- providers with real pagination expose `Load more`.

### Discovery Input Strategy

For the most stable results, use this order of preference:

1. direct IIIF manifest URL;
2. provider item URL;
3. provider-specific identifier or shelfmark;
4. free-text search.

Free-text search is convenient but not universal. Some providers expose reliable native or adapter-backed search, while others are effectively “resolve by identifier/URL first”.

### Search Versus Resolve

Scriptoria supports three practical discovery behaviors:

- `direct`: the provider is treated mainly as a resolver for explicit input;
- `fallback`: Scriptoria first tries to resolve the input directly and only falls back to search behavior when useful;
- `search_first`: Scriptoria treats search as a first-class entry path for that provider.

This matters when you choose what to paste into the field. A shelfmark that works well for Vaticana is not equivalent to a free-text query against Heidelberg or Cambridge.

### What Type Of Reference Should You Search For

Use the provider matrix in [Provider Support](../reference/provider-support.md) for exact details. As a practical rule:

- use shelfmarks for Vaticana;
- use ARK IDs, record URLs, or free text for Gallica;
- use numeric IDs or record URLs for Institut de France;
- use record UUIDs or Digital Bodleian URLs for Bodleian;
- use catalog IDs or record URLs for Heidelberg;
- use shelfmarks or CUDL URLs for Cambridge;
- use compound IDs such as `csg-0001` for e-codices;
- use DRS-based URLs for Harvard;
- use `loc.gov/item/...` URLs for Library of Congress;
- use `archive.org/details/...` URLs or free text for Internet Archive.

## Library

Library is the local catalog for saved and downloaded material.

Typical actions:

- open an item in Studio;
- review partial or complete status;
- retry missing pages;
- clean partial data;
- remove the item and its related runtime state.

### What Library Actually Stores

Library is not just a bookmark list. It tracks the manuscript record and its working state, including:

- provider/library identity;
- manifest URL and local path;
- local scan availability;
- whether a local manifest is available;
- whether a local PDF is already available;
- thumbnail or preview information for the card grid;
- missing-page and asset-state information used by the UI.

### Saved Versus Downloaded

An item can exist in Library without having a full local page set.

- A `saved` item is known locally and can usually still be opened in Studio.
- A downloaded item has local scans and, depending on policy and completeness, may move Studio into local reading mode.
- A partial item may mix local scans, staged temporary pages, and remote fallback behavior.

This is why Library is the operational center of the project. It is where external IIIF material becomes a managed local working object.

## Operational Rule

Runtime paths must come from `ConfigManager`, not hardcoded assumptions. Treat Library as the UI layer over managed local state.

## Related Docs

- [First Manuscript Workflow](first-manuscript-workflow.md)
- [Runtime Paths](../reference/runtime-paths.md)
- [Discovery And Provider Model](../explanation/discovery-provider-model.md)
