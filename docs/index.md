# Scriptoria Documentation

<div className="scriptoria-docs-hero">
  <div>
    <p><strong>Scriptoria is a local-first IIIF manuscript workbench.</strong> It helps you move from provider discovery to a managed local workspace where reading, repair, transcription, and export remain under your control.</p>
    <p>The project exists for situations where a normal viewer is not enough: inconsistent provider search, uneven image delivery, partial local downloads, page-by-page repair needs, and reproducible export requirements.</p>
  </div>
  <img className="scriptoria-docs-hero-art" src="/img/scriptoria-header.svg" alt="Scriptoria header graphic" />
</div>

<div className="scriptoria-fact-grid">
  <div className="scriptoria-fact-card">
    <strong>Runtime Model</strong>
    Discovery, local catalog, Studio workspace, and Output/export remain separate on purpose.
  </div>
  <div className="scriptoria-fact-card">
    <strong>Input Types</strong>
    Manifest URLs, provider URLs, shelfmarks, record identifiers, and supported free-text queries.
  </div>
  <div className="scriptoria-fact-card">
    <strong>Operational Focus</strong>
    Local scans, source-mode policy, page repair actions, and profile-driven export.
  </div>
  <div className="scriptoria-fact-card">
    <strong>Best Fit</strong>
    Scholars, librarians, digital humanists, and technical users working with manuscript-heavy IIIF sources.
  </div>
</div>

Scriptoria is a local research workbench for IIIF manuscripts. It is built for people who need more than a generic viewer: scholars who must move from catalog discovery to close reading, librarians or digital curators who need reproducible local working copies, and advanced users who want controlled export, provenance retention, and page-level repair tools.

The product is designed around one practical idea: remote IIIF sources are valuable but inconsistent. Search behavior differs from provider to provider, manifests are not equally clean, image delivery is uneven, and PDF availability is highly variable. Scriptoria gives you one local workspace where those differences remain visible and manageable instead of being hidden behind a fake notion of uniformity.

:::info Why "Scriptoria"?
In the history of the book, a *scriptorium* was a place where manuscripts were copied, annotated, corrected, and prepared for circulation. The name fits the product well: Scriptoria is not only a reader, but a working environment for acquiring, inspecting, correcting, and exporting manuscript material.
:::

## What Scriptoria Is For

Use Scriptoria when you need to resolve a manuscript from a supported IIIF provider, preserve a stable local record before a full download exists, work from local scans instead of trusting upstream availability, repair weak pages selectively, and export PDF or image bundles with explicit source and quality choices.

Just as important, Scriptoria keeps the operational boundary between remote source, local workspace, and final export artifact visible all the way through the workflow. It is not a public-facing digital library frontend, not a cloud collaboration suite, and not a generic IIIF demo viewer. It is a local-first technical workspace for manuscript-heavy research and curation work.

## Main Surfaces

The application has four main user-facing surfaces. They are intentionally separate because they solve different problems.

### Discovery

Discovery is where you resolve a manuscript from a provider-specific input. Depending on the provider, that input may be a shelfmark, a record URL, a text query, or a direct IIIF manifest URL. Discovery is not only "search". It is the normalization layer that translates heterogeneous provider behavior into a candidate item that Scriptoria can work with.

### Library

Library is the local catalog of known items. Saving an item to Library is different from downloading it. A manuscript can exist in Library as a local record even when its scans are still remote or incomplete. This separation is fundamental to the product model.

### Studio

Studio is the main document workspace. It combines viewer state, manifest resolution, local-versus-remote reading policy, OCR, transcription work, and export preparation. Opening Studio is not simply loading a viewer page. It means asking Scriptoria to resolve which assets are available, which source mode is active, and what degree of local completeness exists for the current manuscript.

### Output

Output is the controlled export surface. It combines thumbnail-based page inspection, per-page repair actions, profile-driven export, PDF inventory, and a live job monitor. Export is treated as an explicit workflow because output quality depends on source mode, page availability, profile settings, and upstream capabilities.

## Supported Libraries

Scriptoria currently supports these provider families in the shared registry:

- Vaticana (BAV)
- Gallica (BnF)
- Institut de France (Bibnum)
- Bodleian (Oxford)
- Universitaetsbibliothek Heidelberg
- Cambridge University Digital Library
- e-codices
- Harvard University
- Library of Congress
- Internet Archive
- generic direct IIIF manifest URL

This does **not** mean every provider behaves the same way. Some are strong for free-text search, some work best with record URLs or identifiers, and some have search flows that are technically supported but operationally less reliable. Read [Provider Support](reference/provider-support.md) before assuming a provider-specific workflow will behave like another one.

## How To Read This Documentation

The documentation is split by function rather than by audience labels. The idea is simple: guides show workflows, reference pages define exact behavior, and explanation pages describe the system model behind the UI.

### Start Here

If you are new to the product and want a working path:

1. Read [Getting Started](intro/getting-started.md).
2. Follow [First Manuscript Workflow](guides/first-manuscript-workflow.md).
3. Read [Discovery And Library](guides/discovery-and-library.md).
4. Read [Studio Workflow](guides/studio-workflow.md).
5. Read [PDF Export](guides/pdf-export.md) before relying on export profiles or page repair actions.

### Use The Reference When You Need Exact Behavior

Go to the reference section when you need exact inputs, settings, or capability boundaries:

- [Provider Support](reference/provider-support.md)
- [Configuration Overview](reference/configuration.md)
- [Detailed Configuration Reference](CONFIG_REFERENCE.md)
- [CLI Reference](reference/cli.md)
- [Runtime Paths](reference/runtime-paths.md)

### Use The Explanation Pages When You Need The System Model

The explanation pages are for the parts of the product that are easy to misunderstand if you only read the UI labels:

- [Architecture Summary](explanation/architecture.md)
- [Storage Model](explanation/storage-model.md)
- [Job Lifecycle](explanation/job-lifecycle.md)
- [Discovery And Provider Model](explanation/discovery-provider-model.md)
- [Export And PDF Model](explanation/export-and-pdf-model.md)
- [Security And Path Safety](explanation/security-and-path-safety.md)

## Configuration And Operations

Scriptoria is configurable because it has to cope with very different upstream behaviors and local workstation constraints. The runtime configuration is not cosmetic. It controls network policy, image acquisition strategy, thumbnail behavior, viewer source policy, PDF defaults, storage retention, and test behavior.

If you only need the map, start with [Configuration Overview](reference/configuration.md). If you need the full keyspace and runtime semantics, use [Detailed Configuration Reference](CONFIG_REFERENCE.md).

## Typical Working Path

The most common Scriptoria workflow looks like this:

1. Resolve a manuscript in `Discovery`.
2. Save it to `Library`.
3. Download only when local assets are actually needed.
4. Open the item in `Studio`.
5. Repair or inspect pages in `Output` when quality is uneven.
6. Export a PDF or image bundle with an explicit profile.

That sequence is important because Scriptoria is built around controlled transitions between states: discovered, saved, partially local, fully local, and exported.

## Project Documentation

The site also includes project-facing material for maintainers and contributors:

- [Contributing](project/contributing.md)
- [Testing Guide](project/testing-guide.md)
- [Wiki Maintenance](project/wiki-maintenance.md)
- [Issue Triage](project/issue-triage.md)

## Publishing Model

This docs site is the canonical documentation surface. Long-form material lives under `docs/`, while `docs/wiki/` is the source for the GitHub Wiki publishing layer. The wiki stays intentionally short and should direct readers back to the canonical site instead of duplicating it.
