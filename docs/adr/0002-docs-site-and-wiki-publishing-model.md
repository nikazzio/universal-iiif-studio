# ADR 0002: Docs Site And Wiki Publishing Model

## Status

Accepted

## Decision

Scriptoria uses:

- a Docusaurus docs site as the canonical public documentation surface;
- GitHub Wiki as a minimal entry layer;
- `docs/wiki/` as the wiki source of truth.

## Rationale

The repository already had good Markdown content, but the wiki experience was confusing and pushed users toward repository file views instead of clean documentation pages.

The docs site solves canonical navigation. The wiki remains useful only as a short bridge for users who arrive through GitHub.
