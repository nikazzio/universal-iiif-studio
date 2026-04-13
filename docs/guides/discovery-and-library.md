# Discovery And Library

Discovery and Library look adjacent in the UI, but they solve different engineering problems.

Discovery is the boundary layer between Scriptoria and heterogeneous external providers. Library is the managed local catalog of items that Scriptoria already knows about. If you treat them as one feature, the application becomes harder to understand. If you keep them separate, the product model becomes predictable.

## What Discovery Does

Discovery resolves external input into a candidate manuscript record. That input can be a direct IIIF manifest URL, a provider item URL, a shelfmark or provider-specific identifier, or a free-text query when the provider has a usable search adapter.

The output of Discovery is not yet a full local manuscript workspace. It is a normalized candidate with enough metadata for preview, local registration, and later download.

## Resolve Versus Search

Internally, Discovery supports both direct resolution and provider-specific search. Those are not the same operation.

- direct resolution means Scriptoria can normalize a known URL or identifier directly into a manifest and manuscript identity;
- search means Scriptoria asks a provider-specific search surface for possible results and then maps those results back into the product model.

Some providers are strong at both. Others are mostly direct-resolution providers with limited search value. This is why the type of input you paste matters.

## Discovery Input Strategy

For the most stable results, use this order:

1. direct IIIF manifest URL;
2. provider item URL;
3. provider-specific identifier or shelfmark;
4. free-text query.

That is not just user advice. It reflects the shape of the provider registry and the uneven quality of upstream search implementations.

## What Happens When You Add An Item

`Add item` does not force a full download. It persists a local manuscript record and related normalized metadata so the item becomes part of the local catalog.

This is one of the most important product rules:

- discovery creates or enriches local knowledge about an item;
- download creates or enriches the local asset set for that item.

Because those are separate, you can build a serious shortlist in Library without immediately consuming network time or disk space.

## Search Pagination And Provider Behavior

Discovery also reflects provider-specific result behavior. Some providers can expose `Load more` because they offer real pagination. Others behave much better as resolver-first systems, where URLs and identifiers are more reliable than broad text queries. In a few cases the product deliberately points you toward browser-assisted discovery because the upstream search surface is not strong enough to justify pretending otherwise.

The practical posture is to treat Discovery as a normalized gateway, not as proof that every library offers the same search ergonomics.

## What Library Does

Library is the local catalog of manuscript records and their current working state.

In practical terms, Library is where you:

- reopen known items;
- inspect whether an item is only saved, partially local, or complete enough for local work;
- start or retry downloads;
- clean partial runtime data;
- delete an item and its related local workspace.

Library is not a passive bookmark list. It is the operational registry for the local side of the application.

## What A Library Entry Represents

A Library card is the visible UI form of a local manuscript record. That record can include provider identity, manuscript id and manifest URL, normalized title and metadata preview, path information, local manifest state, local scan state, local PDF state, missing-page information, and the asset-state hints later used by Studio and Output.

This is why Library matters even before a full download exists. It is already the stable identity layer for the manuscript inside Scriptoria.

## Saved, Partial, Complete

You should think about Library entries in terms of operational state rather than binary presence.

### Saved

The item is registered locally, but the full local scan set may not exist yet. Studio can still open it, often in remote mode.

### Partial

Some local assets exist, but the workspace is incomplete. This is the most common state during interrupted or incremental acquisition and the one most likely to produce mixed local/remote behavior.

### Complete

The local workspace has enough material for the configured local reading and export policies to behave predictably as a local-first workflow.

Those distinctions matter later in Studio. They are not only labels for the Library page.

## Why Discovery And Library Must Stay Separate

The separation is deliberate for three reasons. Providers are inconsistent, and the local catalog should not inherit the instability of upstream discovery surfaces. Local state also has to remain legible: a manuscript may be known locally long before it becomes a complete local asset set. Finally, the workflow is incremental by design. Scriptoria is built for shortlisting, staged download, partial repair, and later export, not only for all-or-nothing acquisition.

## Practical Rule Of Thumb

If you are still deciding what the manuscript is, you are in `Discovery`.

If Scriptoria already knows the manuscript and you are deciding what to do with its local state, you are in `Library`.

## Related Docs

- [First Manuscript Workflow](first-manuscript-workflow.md)
- [Provider Support](../reference/provider-support.md)
- [Runtime Paths](../reference/runtime-paths.md)
- [Discovery And Provider Model](../explanation/discovery-provider-model.md)
