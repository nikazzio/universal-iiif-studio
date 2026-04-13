# Configuration Overview

Runtime settings live in `config.json`. The detailed key-by-key reference remains available in [Configuration Reference](../CONFIG_REFERENCE.md).

Use this page to understand the configuration model before working directly with individual keys.

## High-Impact Areas

- `settings.network.*` controls transport behavior and provider-specific throttling.
- `settings.images.*` controls download strategy, stitching behavior, and local optimization.
- `settings.pdf.*` controls PDF preferences, export defaults, and profiles.
- `settings.storage.*` controls retention, staging, and promotion behavior.
- `settings.viewer.*` controls local-vs-remote reading behavior.
- `settings.discovery.*` controls result sizing and discovery behavior.

## Recommended Reading Order

1. Start with this page for the mental model.
2. Use the detailed [Configuration Reference](../CONFIG_REFERENCE.md) for exact keys.
3. Use [Runtime Paths](runtime-paths.md) when you need to understand where data really lives.

## Related Docs

- [Runtime Paths](runtime-paths.md)
- [Configuration Reference](../CONFIG_REFERENCE.md)
- [HTTP Client Notes](../HTTP_CLIENT.md)
