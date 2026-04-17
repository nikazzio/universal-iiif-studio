# First Manuscript Workflow

This guide walks through the shortest serious workflow for a manuscript in Scriptoria. The goal is not only to describe which buttons to press, but to explain what state the system is building at each step.

## 1. Resolve The Source In Discovery

Start in `Discovery` with the strongest reference you have available. Best case is a direct IIIF manifest URL. A supported provider URL, shelfmark, provider-specific identifier, or free-text query can also work, but they are progressively less stable depending on the provider.

When the preview looks correct, use `Add item`.

That action is intentionally limited. It stores the local manuscript record and normalized metadata, but it does not start a heavy asset acquisition pipeline on your behalf. If you already know that you want both the record and the scans, use `Add and download` instead, which chains the two operations.

## 2. Register The Item In Library

Once the item is in `Library`, it becomes part of your local workspace model.

At that point you decide whether the item should remain a metadata-only local record, move immediately into a full download, or resume a previous partial acquisition. This is the moment where an external manuscript becomes a managed local object. The workspace may still be thin, but the identity and current state are now under Scriptoria's control.

Library is also where you act on local-side properties of the item without touching upstream:

- `Set type` to classify the manuscript inside your own catalog;
- `Update notes` for personal annotations on the entry;
- `Refresh metadata` when the upstream record has changed and you want to re-fetch normalized metadata;
- `Reclassify` to re-run provider classification for one item, or `Reclassify all` and `Normalize states` for catalog-wide consistency passes after upgrades.

These actions are catalog-level. They do not start downloads.

## 3. Understand The Initial State

Before opening Studio, understand the three states that matter operationally:

- `saved`: local record exists, but a complete local scan set does not;
- `partial`: some local assets exist, but the workspace is incomplete;
- `complete`: local coverage is good enough for stable local-first reading and export.

These are not decorative labels. They drive later behavior in Studio and Output.

## 4. Acquire Scans With The Right Granularity

Scriptoria does not assume that a download is always a single all-or-nothing operation. From Library, you can:

- start a `Full download` to acquire every page;
- request a `Range download` to fetch only a specific page interval;
- run `Retry missing` to fill in gaps left by a previous interrupted run;
- use `Retry range` to re-acquire a specific interval that came down weak;
- run `Cleanup partial` when a previous attempt left inconsistent staged data and you want a clean slate.

Each of these is a real download job and is tracked in the download manager.

## 5. Track Long Jobs In The Download Manager

Acquisition is treated as a tracked job, not a fire-and-forget script.

The download manager exposes the standard operations you would expect on a queued job: pause, resume, retry, cancel, prioritize, and remove. If a job dies because of an upstream rate limit or a transient network error, you do not lose the partial work — you can resume it from where it stopped, and the vault keeps the existing staged pages.

This is what makes incremental acquisition viable across providers that behave inconsistently.

## 6. Open The Item In Studio

Open the manuscript from `Library` into `Studio`.

At this point Scriptoria resolves several things at once:

- whether the manifest should come from local cache or remote source;
- whether page images should be local or remote;
- whether the current state satisfies the configured local-reading policy;
- whether the item opens as a local manuscript or an online manuscript.

This is why the correct question is not "does the item exist in Library?" but "what local coverage does the item currently have?"

## 7. Inspect And Repair Only What Needs Attention

If the manuscript is incomplete or some pages are weak, do not assume you need to redownload everything.

Use `Output` for:

- thumbnail-based page inspection;
- page selection;
- per-page actions: `Scarica` to acquire the page, `Hi-res` to fetch a higher-resolution version, `Opt` to optimize an existing local scan;
- PDF inventory review;
- export job creation.

This is one of Scriptoria's strengths: page-level repair exists because real-world manuscript pipelines often fail unevenly rather than uniformly. Repairing one weak page is cheaper and more honest than re-running the whole acquisition.

## 8. Export Deliberately

When the manuscript is ready, create the export from `Output`.

Use a PDF profile as the normal control surface. Only open job-level overrides when the current export is exceptional.

The final export can depend on:

- whether a native provider PDF exists;
- the quality of the current local scans;
- whether remote temporary high-resolution fetch is needed;
- whether all pages or only a subset should be included;
- whether temporary assets should be cleaned after the job.

That is why Scriptoria treats export as a tracked workflow instead of a one-click side effect.

## Common Failure Modes

If the first workflow feels wrong, the cause is usually one of a small set of predictable cases: the provider input was too vague and should be replaced with a direct URL or identifier, the item is only `saved` and not yet locally complete, Studio is correctly staying in remote mode because coverage is still incomplete, staged pages have not yet been promoted because storage policy is conservative, a previous run left partial state that should be resolved with `Cleanup partial` before retrying, or the provider itself is better handled through URL-driven or browser-assisted discovery.

## Related Docs

- [Discovery And Library](discovery-and-library.md)
- [Studio Workflow](studio-workflow.md)
- [PDF Export](pdf-export.md)
- [Troubleshooting](troubleshooting.md)
- [Job Lifecycle](../explanation/job-lifecycle.md)
