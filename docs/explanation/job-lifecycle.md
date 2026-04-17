# Job Lifecycle

Scriptoria treats long-running work as tracked jobs backed by local state. Downloads and exports are not fire-and-forget calls: they have an identity, a status row in the vault, and a defined set of transitions. This is what makes acquisition and export reliable across providers that behave inconsistently and across sessions that can be interrupted.

## Why The Job Layer Exists

Manuscript acquisition is large, slow, and failure-prone. Pages can fail individually, providers rate-limit aggressively, and a long download can be interrupted at any point. A naive script-style approach would lose work whenever something went wrong.

The job layer is the safety mechanism that prevents that. It records the work in progress, exposes pause and resume operations, lets the user retry only what failed, and survives application restarts without losing the partial state that was already on disk.

## The Job Manager

The download and export job manager is a process-wide singleton implemented in `universal_iiif_core/jobs.py`. It owns:

- a registry of in-flight job records keyed by short job ids;
- a download queue that admits jobs up to a configured concurrency limit;
- the threading boundaries that isolate worker exceptions from the UI;
- the bridge between in-memory job state and the persistent `download_jobs` table in the local vault.

The concurrency cap is taken from network policy. The default value of `max_concurrent_download_jobs` is `2`, which is intentionally conservative: most upstream providers prefer a few well-paced clients over many aggressive ones.

## Status Values

The vault recognizes a small, fixed set of statuses for download and export jobs.

### Transitional States

A job is in a transitional state when something is actively happening or being requested:

- `queued`: the job has been created and is waiting for an execution slot;
- `running`: a worker thread is actively processing the job;
- `cancelling`: the user requested cancellation while the job was running and the worker is winding down;
- `pausing`: the user requested a pause and the worker is winding down to a paused state.

### Terminal States

Terminal states describe a job that is no longer doing work:

- `paused`: the worker stopped at a clean point and the job can be resumed later;
- `cancelled`: the worker stopped after a cancel request and the job will not resume automatically;
- `completed`: the job finished successfully;
- `error`: the job stopped because of an error, and the failure reason is recorded in `error_message`.

The vault enforces terminality. Once a row is in `paused`, `cancelled`, `completed`, or `error`, transitional updates that would overwrite that state are ignored. This prevents late worker callbacks from undoing a user-driven decision.

## Lifecycle Of A Download Job

A typical download job goes through this sequence.

1. The route layer calls into the job manager to enqueue the job. A row is created in `download_jobs` with status `queued` and a `job_origin` such as `library_download`.
2. When a slot frees up, the job is promoted to `running`, `started_at` is set, and the worker thread starts acquiring pages.
3. Pages are written to a staging area first. They are validated as image files before being considered acceptable for promotion.
4. As the worker progresses, `current_page` and `total_pages` are updated.
5. On a clean finish, the job moves to `completed`, `finished_at` is recorded, and validated pages are promoted into the local scan set according to the configured promotion policy.
6. On a fatal error, the job moves to `error` and the failure reason is stored.
7. If the user pauses or cancels, the worker first goes through `pausing` or `cancelling`, then settles into the corresponding terminal state.

The pause and cancel transitions exist as their own states because the worker cannot stop instantaneously. Acknowledging the request and the actual stop are different events, and the lifecycle reflects that.

## Why Staging Comes Before Promotion

Staged pages are not the same thing as local scans. The job writes to a temporary directory under the configured temp root, validates each image, and only moves the result into the manuscript's `scans/` directory once promotion is allowed.

The promotion policy is governed by the `storage.partial_promotion_mode` setting:

- `never`: only fully completed runs promote staged pages into `scans/`;
- `on_pause`: a clean pause also promotes the staged pages it managed to validate.

This separation is what allows partial work to survive a restart without polluting the local scan set with half-validated images. It is also what lets `Retry missing` and `Retry range` make sense as targeted operations rather than always implying a full redownload.

## Resume Safety

Resume is a first-class operation, not a side effect. When a paused or interrupted job is resumed, the manager:

- reuses the existing vault row instead of creating a duplicate;
- skips pages that already exist in the staging or scan directory;
- continues acquisition from where the previous run stopped;
- transitions the row back through `queued` and `running` like any new job.

This is why Library exposes `Retry missing` and `Retry range` separately from `Download full`: they all rely on the same resume-safe job model, but they scope the work differently.

## Export Jobs

Export jobs follow the same overall lifecycle but live in their own job records and run through the export service. Each export job stores scope type, document ids, library identity, export format, output kind, page-selection mode, destination, progress counters, the final output path, and any terminal error.

The route layer creates the job entry first and only then spawns the worker thread. That order is important: it lets the UI poll status, cancel active jobs, and retain history after completion, without depending on whether the worker has had time to start.

On startup, the application also marks any export rows that were left in transitional states by a previous crashed run as `error`, so that stale jobs do not appear to be still running.

## Job Origin

Download jobs carry a `job_origin` field. Common values include `library_download`, `discovery_add_and_download`, and similar markers indicating where the job was triggered from. This is mostly diagnostic, but it lets the system distinguish between user-initiated downloads and chained operations when a problem needs to be traced.

## Why The Model Matters

The job layer is the safety mechanism that keeps partial work understandable and recoverable. Without it, the application would silently lose progress on every interruption, retries would be all-or-nothing, and pause would either not exist or would corrupt the local scan set.

With it, Scriptoria can run long acquisitions on flaky upstream providers, survive restarts cleanly, and let the user reason about their workspace in terms of states like `partial` and `complete` instead of just "did the download finish".

## Related Docs

- [Storage Model](storage-model.md)
- [First Manuscript Workflow](../guides/first-manuscript-workflow.md)
- [Discovery And Library](../guides/discovery-and-library.md)
- [Export And PDF Model](export-and-pdf-model.md)
- [Configuration Reference](../CONFIG_REFERENCE.md)
