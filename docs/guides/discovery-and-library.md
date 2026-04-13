# Discovery And Library

`Discovery` and `Library` solve different parts of the workflow:

- `Discovery` finds or resolves candidate documents.
- `Library` manages items already known to the local workspace.

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

## Library

Library is the local catalog for saved and downloaded material.

Typical actions:

- open an item in Studio;
- review partial or complete status;
- retry missing pages;
- clean partial data;
- remove the item and its related runtime state.

## Operational Rule

Runtime paths must come from `ConfigManager`, not hardcoded assumptions. Treat Library as the UI layer over managed local state.

## Related Docs

- [First Manuscript Workflow](first-manuscript-workflow.md)
- [Runtime Paths](../reference/runtime-paths.md)
- [Discovery And Provider Model](../explanation/discovery-provider-model.md)
