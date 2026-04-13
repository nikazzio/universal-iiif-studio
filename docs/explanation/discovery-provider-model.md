# Discovery And Provider Model

Discovery is built around a shared provider registry and typed orchestration.

## Responsibilities

- classify user input;
- resolve direct provider inputs;
- dispatch free-text search to supported adapters;
- normalize results into a shared contract;
- support provider-specific pagination and filters where possible.

## What The Provider Registry Actually Does

The provider registry is the product contract between UI behavior and provider-specific logic. Each provider entry defines:

- canonical product name and aliases;
- which resolver class can normalize direct inputs;
- whether search is supported;
- which search strategy handler should be used;
- whether the provider is effectively direct, fallback, or search-first;
- provider-specific helper text, placeholder guidance, and optional search filters.

This lets Discovery behave consistently in the UI while still respecting real provider differences.

## Why It Is Not Just Search

The discovery layer is also where provider fragility becomes product behavior:

- some providers are stable enough for search;
- some are direct-resolution only;
- some require network policies that shape the UX.

It is also where the product decides how much confidence to place in a given input. A direct manifest URL is usually high-confidence. Free-text search is lower-confidence and more provider-dependent.

## Search Is Only One Path

Scriptoria does not assume that “search” is the universal answer. In manuscript work, users often start from:

- a shelfmark;
- a catalog record URL;
- a local note containing a provider-specific identifier;
- a previously known manifest URL.

The discovery model therefore supports both exploratory and reference-driven workflows.

## Why The Search Modes Matter

`search_first` providers are suitable for exploratory discovery directly in Scriptoria.

`fallback` providers can search, but the best product behavior still starts with explicit references when available.

`direct` providers should be treated as resolution surfaces. In those cases, Scriptoria is helping you normalize already-known material rather than replacing the source library's own catalog.

## Related Docs

- [Getting Started](../intro/getting-started.md)
- [Discovery And Library](../guides/discovery-and-library.md)
- [Provider Support](../reference/provider-support.md)
- [HTTP Client Notes](../HTTP_CLIENT.md)
