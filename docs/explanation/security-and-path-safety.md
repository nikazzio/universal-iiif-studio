# Security And Path Safety

Scriptoria is a local-first application that nonetheless touches user input, the file system, external HTTP services, and a local SQLite vault. The security posture is shaped by a small set of project-level rules. They are not bureaucratic compliance items; they exist because each one is enforced in real code and protects a concrete failure mode.

## Project Rules

The baseline rules apply across UI, CLI, and core services.

- Never hardcode secrets or tokens in source code. Provider credentials, API keys, and any user-bound tokens belong in configuration or environment variables, never in tracked files.
- Validate input at system boundaries. Routes, CLI argument parsing, and external payload deserialization are the points where validation must happen, not somewhere later in the pipeline.
- Enforce path safety for every operation that reads, writes, downloads, deletes, or optimizes a file on disk.
- Use parameterized access patterns for database operations. Never build SQL strings from user input.
- Do not leak sensitive details in user-facing error messages. The full reason can go to logs; the message shown to the user should not expose internal paths or credentials.
- Keep permissive CORS limited to explicit local development scenarios. Default to specific origins in any non-trivial deployment.

## Path Safety In Practice

Path safety is the rule with the most concrete enforcement in the codebase. Several flows could in principle be tricked into reading or writing outside the managed runtime tree, so they all share the same containment pattern.

The canonical helper looks like this in `universal_iiif_core/jobs.py`:

```python
@staticmethod
def _is_within(candidate: Path, root: Path) -> bool:
    try:
        return candidate.resolve().is_relative_to(root.resolve())
    except Exception:
        return False
```

The shape is intentional. Both paths are resolved before comparison so that symlinks and `..` segments cannot escape the root. Any operation that touches the file system on behalf of a manuscript is expected to use this kind of containment check before the real read or write happens.

The same pattern is used in scan optimization (`services/scan_optimize.py`) and in download runtime cleanup (`logic/downloader_runtime.py`), where the relevant root is the configured downloads or temp directory.

## Roots Always Come From ConfigManager

Path safety is meaningful only when the "root" is itself trustworthy. Scriptoria takes that root from `ConfigManager`, never from user input or from a hardcoded constant.

The current root families are the configured downloads, exports, temp, models, logs, and snippets directories. These are resolved once and used as the comparison anchor for every containment check. If the user reconfigures `data/local/downloads` to a different absolute path, the safety checks transparently follow.

This is why `docs/AGENTS.md` and the project rules forbid hardcoded runtime paths. It is not only about portability: hardcoded paths bypass the only mechanism that lets path safety work in user-customized installations.

## Filename Sanitization

User-visible folder and file names also need to be safe across operating systems. The `sanitize_filename` helper in `universal_iiif_core/utils.py` strips characters that are illegal on Windows or unwise on POSIX (`/ \ : * ? " < > |`), removes ASCII control characters, and collapses whitespace.

This is applied when building the per-manuscript directory name from the provider, manuscript id, and optional title, so that arbitrary upstream metadata cannot inject path separators or hidden characters into the local layout.

## The Centralized HTTP Client

External network behavior goes through `universal_iiif_core.http_client`. New code is required to use that module rather than instantiate `requests.Session()` directly.

This rule is partly architectural and partly a security measure. The centralized client is where retry policy, per-library backoff, rate limiting, and request hygiene live. Bypassing it does not just duplicate code: it disables the controls that prevent Scriptoria from hammering an upstream provider after a 403 or 429 response, and it removes the place where header policy and timeouts are enforced.

The companion `network_policy.py` module declares per-library policy: cooldowns on `403` and `429`, burst windows, retry-after handling, and per-host concurrency limits. A handful of providers (Gallica is the most visible example) explicitly need slow, polite traffic, and the policy file is how that knowledge stays consistent across the application.

## Vault Access

Local persistence goes through `VaultManager` and the related modules under `services/storage/`. All SQL is parameterized at the call site. New code that needs to query or update local state must use the existing helper methods or follow the same parameterized pattern. String-built SQL is never acceptable, even for "internal" tables.

The vault file itself is part of the user's local data and should be excluded from any sharing or backup that is not under the user's explicit control.

## Input Validation At The Boundary

The boundary for the web app is the FastHTML route handlers under `studio_ui/routes/`. The boundary for the CLI is `argparse` in `universal_iiif_cli/cli.py`. The boundary for external payloads is the resolver and discovery layer in `universal_iiif_core/resolvers/` and `universal_iiif_core/discovery/`.

Each of these is responsible for rejecting or normalizing untrusted input before it reaches the rest of the system. Internal modules deeper in the stack are allowed to assume that paths, identifiers, and URLs they receive have already been validated.

This is the principle that allows the rest of the codebase to stay readable: validation is concentrated where input enters the application, not scattered defensively throughout every function.

## Error Messages

Errors visible to the user should help them understand what went wrong without exposing internals that have no business being shown. Stack traces, full filesystem paths, raw HTTP response bodies from upstream providers, and configuration values belong in logs.

The route layer is responsible for catching exceptions from core services and rendering a user-appropriate message. The CLI follows the same pattern by printing a short error and a hint, while the full traceback goes to the logger.

## CORS Posture

Permissive CORS is acceptable only for explicit local development. The default deployment posture should restrict origins. If a route or middleware introduces broader CORS than the local-development case, that is an architectural change and should be reviewed against this rule before merging.

## Documentation Implication

Operational guides should explain safe behavior without exposing sensitive internals. Technical docs should point to the path-safety, validation, and network-policy model, especially around export, cleanup, optimization, and download flows. When a doc page describes a path or a file operation, it should describe the path family and the controlling configuration, not encourage readers to assume a fixed absolute path.

## Related Docs

- [Architecture Summary](architecture.md)
- [Storage Model](storage-model.md)
- [Job Lifecycle](job-lifecycle.md)
- [Runtime Paths](../reference/runtime-paths.md)
- [Configuration Reference](../CONFIG_REFERENCE.md)
