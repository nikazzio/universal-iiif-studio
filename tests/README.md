# Test Suite Guide

The test suite is `pytest`-first and covers both the shared IIIF core and the FastHTML/HTMX UI surface.

## Main Areas

- `test_providers.py`, `test_discovery_resolvers*.py`
  - provider registry normalization
  - shared CLI/web direct resolution
  - regression coverage for provider autodetection order
- `test_search_*_unit.py`
  - provider-specific search adapters
  - result parsing and normalization into canonical `SearchResult` payloads
- `test_discovery_handlers_resolve_manifest.py`
  - end-to-end discovery route behavior
  - search-result rendering vs manifest-preview rendering
- `test_discovery_orchestrator.py`, `test_discovery_search_adapters.py`
  - orchestrator policy contract (`manifest|results|not_found`)
  - provider search-adapter dispatch and payload forwarding (e.g. Gallica filter)
- `test_live.py`
  - optional live smoke checks against real remote providers
- downloader / export / library tests
  - runtime staging
  - PDF behavior
  - vault state
  - UI handler responses

## Current Search Adapter Coverage

- `Gallica`
- `Vaticana`
- `Institut de France`
- `Archive.org`
- `Bodleian`
- `e-codices`
- `Cambridge`
- `Heidelberg`
- `Harvard`
- `Library of Congress`

Direct-only providers currently covered through resolver/provider tests:

- generic direct manifest URLs

## Running Tests

From the project root:

```bash
.venv/bin/pytest tests/
```

Targeted examples:

```bash
.venv/bin/pytest tests/test_providers.py -q
.venv/bin/pytest tests/test_search_archive_org_unit.py tests/test_search_vatican_unit.py -q
.venv/bin/pytest tests/test_discovery_handlers_resolve_manifest.py -q
```

## Fixtures

- `fixtures/gallica_sample.xml`
  - sample Gallica SRU response for parser-oriented tests

## Notes

- Some provider surfaces are HTML-based and intentionally mocked in unit tests because the public sites can rate-limit or block scripted traffic.
- Cambridge free-text coverage includes the browser-handoff fallback when CUDL search is blocked by its WAF.
- Heidelberg free-text coverage includes a browser-handoff fallback when automated hit extraction does not yield stable `diglit` results.
- Live tests are useful for smoke validation, but they are not a stable substitute for parser/contract tests.
- When adding a new provider search adapter, prefer:
  1. parser/unit tests
  2. provider-registry coverage
  3. one route-level discovery test
  4. optional live smoke check
