# Scriptoria Documentation

Scriptoria is a local research workbench for IIIF manuscripts. It is designed for scholars, librarians, and advanced users who need to move from a remote IIIF source to a controlled local workspace without losing provenance, page structure, or export flexibility.

The product has two user-facing entry points:

- `scriptoria` for the local web application;
- `scriptoria-cli` for direct CLI workflows.

The web application is built around four surfaces:

- `Discovery` to resolve a manifest, provider URL, shelfmark, or supported search query;
- `Library` to keep a local catalog of saved and downloaded items;
- `Studio` to read, inspect, transcribe, and prepare output for one item;
- `Output` to manage PDF-oriented export jobs and page-level recovery actions.

## Start Here

- [Getting Started](intro/getting-started.md)
- [First Manuscript Workflow](guides/first-manuscript-workflow.md)
- [Troubleshooting](guides/troubleshooting.md)

Use the guides when you need a concrete workflow, the reference section when you need exact keys or commands, and the explanation section when you need to understand system behavior.

## Product Model

Scriptoria separates concerns on purpose:

- resolving a document is not the same as downloading it;
- saving an item to Library is not the same as creating a full local archive;
- reading can happen against remote IIIF assets or local scans, depending on availability and policy;
- exporting a PDF is treated as a tracked workflow, not as an unstructured one-click side effect.

This matters because many upstream libraries are inconsistent. Some support stable free-text discovery, some mostly support identifier- or URL-driven access, and some expose native PDFs while others only expose image-based workflows. Scriptoria keeps these differences visible instead of pretending every provider behaves the same way.

## Main Reading Paths

### Guides

- [Discovery And Library](guides/discovery-and-library.md)
- [Studio Workflow](guides/studio-workflow.md)
- [PDF Export](guides/pdf-export.md)

### Reference

- [Configuration Overview](reference/configuration.md)
- [CLI Reference](reference/cli.md)
- [Runtime Paths](reference/runtime-paths.md)
- [Provider Support](reference/provider-support.md)

### Explanation

- [Architecture Summary](explanation/architecture.md)
- [Storage Model](explanation/storage-model.md)
- [Job Lifecycle](explanation/job-lifecycle.md)
- [Discovery And Provider Model](explanation/discovery-provider-model.md)
- [Export And PDF Model](explanation/export-and-pdf-model.md)
- [Security And Path Safety](explanation/security-and-path-safety.md)

## Typical Reading Order

For a new user:

1. Read [Getting Started](intro/getting-started.md).
2. Follow [First Manuscript Workflow](guides/first-manuscript-workflow.md).
3. Use [Discovery And Library](guides/discovery-and-library.md) and [Studio Workflow](guides/studio-workflow.md) as operating guides.
4. Read [Provider Support](reference/provider-support.md) before relying on a provider-specific search flow.
5. Read [PDF Export](guides/pdf-export.md) when you need controlled output.

For a maintainer or contributor:

1. Read [Architecture Summary](explanation/architecture.md).
2. Read [Discovery And Provider Model](explanation/discovery-provider-model.md).
3. Read [Storage Model](explanation/storage-model.md) and [Job Lifecycle](explanation/job-lifecycle.md).
4. Use [Configuration Overview](reference/configuration.md) and [CLI Reference](reference/cli.md) as exact reference material.

## Project Docs

- [Contributing](project/contributing.md)
- [Testing Guide](project/testing-guide.md)
- [Wiki Maintenance](project/wiki-maintenance.md)
- [Issue Triage](project/issue-triage.md)

## Publishing Model

- The docs site is the canonical public documentation surface.
- `docs/wiki/` is the source of truth for the GitHub Wiki.
- The GitHub Wiki is an orientation layer, not a parallel documentation set.
