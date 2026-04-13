# Architecture Summary

Scriptoria separates UI orchestration from reusable core services.

## Main Layers

- `studio_ui/` renders the FastHTML and HTMX application.
- `universal_iiif_core/` owns provider resolution, storage, downloads, export, OCR, and runtime policy.
- `universal_iiif_cli/` exposes CLI behavior on top of the same core layer.

## Important Boundary

The UI depends on the core layer. The core layer does not depend on UI modules.

## Why This Matters

This boundary lets Scriptoria:

- share resolution and download behavior between web and CLI;
- keep runtime policy in one place;
- reduce duplication in storage, networking, and export behavior.

## Deep Dive

For the more detailed component breakdown, see [Project Architecture](../ARCHITECTURE.md).
