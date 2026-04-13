# Testing Guide

The test suite is `pytest`-first and covers both core behavior and UI-facing handlers.

## Recommended Order

1. Run targeted tests for the touched area.
2. Run the full suite with `pytest tests/`.
3. Run Ruff checks.
4. Review docs or config drift when behavior changes affect public workflows.

## Key Test Areas

- provider and resolver behavior;
- search adapter normalization;
- download runtime staging and resume;
- export services and handlers;
- settings and studio workflows;
- vault and local state handling.

## Practical Commands

```bash
.venv/bin/pytest tests/
.venv/bin/pytest tests/test_http_client.py -q
.venv/bin/pytest tests/test_studio_handlers.py -q
```

## Related Docs

- [Repository test suite guide](https://github.com/nikazzio/scriptoria/blob/main/tests/README.md)
