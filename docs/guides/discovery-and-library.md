# Discovery And Library

Discovery and Library look adjacent in the UI, but they solve different engineering problems.

Discovery is the boundary layer between Scriptoria and heterogeneous external providers. Library is the managed local catalog of items that Scriptoria already knows about. If you treat them as one feature, the application becomes harder to understand. If you keep them separate, the product model becomes predictable.

## What Discovery Does

Discovery resolves external input into a candidate item record. That input can be a direct IIIF manifest URL, a provider item URL, a shelfmark or provider-specific identifier, or a free-text query when the provider has a usable search adapter.

The output of Discovery is not yet a full local workspace. It is a normalized candidate with enough metadata for preview, local registration, and later download.

## Resolve Versus Search

Internally, Discovery supports both direct resolution and provider-specific search. Those are not the same operation.

- direct resolution means Scriptoria can normalize a known URL or identifier directly into a manifest and stable item identity;
- search means Scriptoria asks a provider-specific search surface for possible results and then maps those results back into the product model.

Some providers are strong at both. Others are mostly direct-resolution providers with limited search value. This is why the type of input you paste matters.

Each supported provider declares whether it supports search through a `supports_search()` capability, and the active search adapter is selected per provider. A provider without a search adapter is usable as a resolver but will not return free-text results.

## Discovery Input Strategy

For the most stable results, use this order:

1. direct IIIF manifest URL;
2. provider item URL;
3. provider-specific identifier or shelfmark;
4. free-text query.

That is not just user advice. It reflects the shape of the provider registry and the uneven quality of upstream search implementations.

## What Happens When You Add An Item

`Add item` does not force a full download. It persists a local item record and related normalized metadata so the item becomes part of the local catalog.

This is one of the most important product rules:

- discovery creates or enriches local knowledge about an item;
- download creates or enriches the local asset set for that item.

Because those are separate, you can build a serious shortlist in Library without immediately consuming network time or disk space.

If you already know that you want both the record and the scans in one step, Discovery also exposes `Add and download`, which creates the local record and immediately enqueues a download job. Use the chained action when the decision is already made; use `Add item` when you are still curating.

## Probing Before You Commit

Discovery exposes a `Probe manifest` action that fetches lightweight information from the candidate without registering it locally. Use it when you want to verify that the manifest actually points where you expect before adding the item to your catalog.

There is also a `PDF capability` check that reports whether the provider exposes a native PDF for the item. This matters because export behavior in Output later depends on whether a native PDF is available, and knowing this in advance is useful when planning an acquisition.

## Search Pagination And Provider Behavior

Discovery also reflects provider-specific result behavior. Some providers can expose `Load more` because they offer real pagination. Others behave much better as resolver-first systems, where URLs and identifiers are more reliable than broad text queries. In a few cases the product deliberately points you toward browser-assisted discovery because the upstream search surface is not strong enough to justify pretending otherwise.

The practical posture is to treat Discovery as a normalized gateway, not as proof that every library offers the same search ergonomics.

Biblioteca Estense (Modena) is a dedicated provider for the Jarvis backend (`jarvis.edl.beniculturali.it`). Unlike ICCU, it exposes native IIIF v2/v3 manifests with a level-2 Image API, so items read comfortably inside Mirador with real zoom. Search uses the Spring Data REST endpoint and covers short title, author, and pressmark in a single call; pagination works the same way as for other discovery-first providers.

Internet Culturale **(BETA)** is a special case worth calling out explicitly. It sits at the bottom of the provider select because the integration is experimental: useful when ICCU is the only channel to reach an Italian record, but less reliable than any native IIIF provider. It is an aggregator that fronts around fifty Italian libraries (Laurenziana, Marciana, BNCF, BNCR, Estense, and many smaller partners) and it routinely returns thousands of results for a single keyword. Scriptoria shows the upstream total as "Mostrati X di Y risultati" so the size of the result set is visible, and "Carica altri risultati" walks through the remaining pages twenty at a time. Because the upstream does not expose a IIIF manifest directly, the manifest used internally is converted on-the-fly from ICCU's MAG/XML document; partial records (those declaring more pages than the server actually serves) are still saved as partial scans rather than failing outright, but expect occasional teaser records where only the frontispiece is really available.

## What Library Does

Library is the local catalog of item records and their current working state.

In practical terms, Library is where you:

- reopen known items;
- inspect whether an item is only saved, partially local, or complete enough for local work;
- start, retry, or scope downloads;
- annotate and classify items inside your own catalog;
- refresh or reclassify entries when the upstream record or the provider registry changes;
- clean partial runtime data;
- delete an item and its related local workspace.

Library is not a passive bookmark list. It is the operational registry for the local side of the application.

## What A Library Entry Represents

A Library card is the visible UI form of a local item record. That record can include provider identity, item id and manifest URL, normalized title and metadata preview, path information, local manifest state, local scan state, local PDF state, missing-page information, and the asset-state hints later used by Studio and Output.

This is why Library matters even before a full download exists. It is already the stable identity layer for the item inside Scriptoria.

## Saved, Partial, Complete

You should think about Library entries in terms of operational state rather than binary presence.

### Saved

The item is registered locally, but the full local scan set may not exist yet. Studio can still open it, often in remote mode.

### Partial

Some local assets exist, but the workspace is incomplete. This is the most common state during interrupted or incremental acquisition and the one most likely to produce mixed local/remote behavior.

### Complete

The local workspace has enough material for the configured local reading and export policies to behave predictably as a local-first workflow.

Those distinctions matter later in Studio. They are not only labels for the Library page.

## Acquisition Actions

Library exposes acquisition at more than one granularity. This is intentional because real-world IIIF acquisition often fails unevenly.

- `Download full` runs a complete acquisition for the item.
- `Download range` acquires a specific page interval.
- `Retry missing` fills in only the pages that the local workspace does not yet have.
- `Retry range` re-acquires a specific interval, useful when a portion came down weak.
- `Cleanup partial` clears inconsistent staged data so the next attempt starts from a clean slate.

Each of these is dispatched as a tracked download job with the standard pause, resume, retry, cancel, prioritize, and remove operations available in the download manager.

## Catalog Maintenance Actions

The other surface in Library is catalog-side: actions that change how an item is described or classified locally without re-downloading anything.

- `Set type` records the item type inside your own catalog.
- `Update notes` stores free-form annotations on the entry.
- `Refresh metadata` re-fetches normalized metadata from the upstream provider when the source record has changed.
- `Reclassify` re-runs provider classification for one item; `Reclassify all` and `Normalize states` are bulk passes used after registry or schema upgrades.

These actions are cheap, local-state operations. Use them to keep your catalog coherent without paying acquisition costs.

## Why Discovery And Library Must Stay Separate

The separation is deliberate for three reasons. Providers are inconsistent, and the local catalog should not inherit the instability of upstream discovery surfaces. Local state also has to remain legible: an item may be known locally long before it becomes a complete local asset set. Finally, the workflow is incremental by design. Scriptoria is built for shortlisting, staged download, partial repair, and later export, not only for all-or-nothing acquisition.

## Practical Rule Of Thumb

If you are still deciding what the document is, you are in `Discovery`.

If Scriptoria already knows the document and you are deciding what to do with its local state, you are in `Library`.

## Related Docs

- [First Manuscript Workflow](first-manuscript-workflow.md)
- [Provider Support](../reference/provider-support.md)
- [Runtime Paths](../reference/runtime-paths.md)
- [Discovery And Provider Model](../explanation/discovery-provider-model.md)
- [Job Lifecycle](../explanation/job-lifecycle.md)
