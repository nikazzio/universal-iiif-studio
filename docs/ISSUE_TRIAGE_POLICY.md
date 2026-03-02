# Issue Triage Policy

This document defines mandatory issue/PR governance for backlog consistency and semantic-release alignment.

## Objectives

- Keep issue triage deterministic across contributors.
- Make priority and scope explicit before implementation starts.
- Align issue/PR metadata with release impact (`major|minor|patch|semver:none`).

## Required Labels

Every issue and PR must include:

- one `type:*` label
- one `priority:*` label
- one `area:*` label
- one semver label (`major`, `minor`, `patch`, or `semver:none`)

Optional status labels:

- `status:triage`
- `status:ready`
- `status:in-progress`
- `status:blocked`
- `status:needs-info`

## Priority Model

- `priority:P0`: critical blocker, data loss, security exposure, or release stopper.
- `priority:P1`: high-impact issue or core workflow feature/fix for current cycle.
- `priority:P2`: important but not blocking; can ship in next cycle.
- `priority:P3`: backlog, roadmap, or low urgency work.

## Milestone Model

- `Now (P0-P1)`: active execution lane.
- `Next (P2)`: near-term queue after current lane.
- `Later (P3/Backlog)`: long-horizon items and roadmap containers.

## Semver Guidance

- `major`: breaking change.
- `minor`: backward-compatible feature.
- `patch`: backward-compatible bug fix.
- `semver:none`: no direct release impact (meta/docs/process).

Note:

- semantic-release is driven by commit messages (`feat:`, `fix:`, ...).
- labels provide planning and governance context; they do not replace conventional commits.

## Automation

- Issue forms are required (`.github/ISSUE_TEMPLATE/work-item.yml`).
- `Issue Label Sync` workflow applies triage labels from issue form values.
- `PR Governance` workflow blocks PRs that do not satisfy mandatory metadata rules.

## PR Title and Body Rules

- Title must follow Conventional Commits:
  - `feat(scope): summary`
  - `fix: summary`
  - `docs: summary`
- Body must reference at least one issue:
  - `Closes #123`
  - `Fixes #123`
  - `Related #123`
