# Security And Path Safety

The documentation layer needs to reflect several project-level safety rules.

## Main Rules

- do not hardcode secrets or tokens;
- validate user input at system boundaries;
- enforce path safety for file read, write, download, delete, and optimization operations;
- avoid leaking sensitive details in user-facing errors;
- keep permissive CORS limited to explicit local development scenarios.

## Documentation Implication

Operational guides should explain safe behavior without exposing sensitive internals. Technical docs should point to the path-safety and validation model, especially around export, cleanup, and optimization flows.
