# Discovery And Provider Model

Discovery is built around a shared provider registry and typed orchestration.

## Responsibilities

- classify user input;
- resolve direct provider inputs;
- dispatch free-text search to supported adapters;
- normalize results into a shared contract;
- support provider-specific pagination and filters where possible.

## Why It Is Not Just Search

The discovery layer is also where provider fragility becomes product behavior:

- some providers are stable enough for search;
- some are direct-resolution only;
- some require network policies that shape the UX.

## Related Docs

- [Discovery And Library](../guides/discovery-and-library.md)
- [Provider Support](../reference/provider-support.md)
- [HTTP Client Notes](../HTTP_CLIENT.md)
