# Storage Model

Scriptoria maintains local working state through managed runtime paths and storage services.

## Main Concepts

- manuscripts and metadata are tracked through local storage services;
- staged downloads can exist before final promotion;
- local scans are the operational source for local study workflows;
- export artifacts and job metadata are kept separately from raw scans.

## Why Staging Exists

Staging protects against partial and interrupted downloads. Validated output can be promoted only when the configured policy allows it.

## Core Rule

Documentation and code should describe storage through managed path families and policies, not through hardcoded absolute assumptions.

## Related Docs

- [Runtime Paths](../reference/runtime-paths.md)
- [Job Lifecycle](job-lifecycle.md)
- [Security And Path Safety](security-and-path-safety.md)
