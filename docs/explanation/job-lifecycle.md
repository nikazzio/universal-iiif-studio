# Job Lifecycle

Scriptoria treats download and export work as tracked jobs backed by local state.

## Download Jobs

A typical download job:

1. is created from discovery or library actions;
2. records progress in local state;
3. stages validated pages first;
4. promotes them according to storage policy;
5. can be paused, resumed, retried, or cancelled.

## Export Jobs

A typical export job:

1. starts from a profile or page-level action;
2. records progress in local state;
3. uses local or temporary remote assets depending on the profile;
4. persists output artifacts under managed paths.

## Why The Model Matters

The job layer is the safety mechanism that keeps partial work understandable and recoverable.
