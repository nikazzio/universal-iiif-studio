# Test Directory

This directory contains test scripts and fixtures for the universal-iiif-downloader project.

## Structure

```
tests/
├── README.md                      # This file
├── fixtures/                      # Test data and sample files
│   └── gallica_sample.xml        # Sample Gallica SRU API response
├── test_discovery_resolvers.py   # Tests for library resolvers (Gallica, Oxford, Vaticana)
├── test_search_apis.py           # Tests for search APIs (Gallica SRU, Oxford)
├── test_oxford_api.py            # Legacy test for deprecated Oxford API
├── test_live.py                  # Live download tests
└── out/                          # Output directory for test downloads
```

## Running Tests

All test scripts should be run from the project root directory:

### Discovery Resolvers Test
Tests the `resolve_shelfmark()` function for all three libraries:

```bash
python -m tests.test_discovery_resolvers
```

### Search APIs Test
Tests the search functionality for Gallica and Oxford:

```bash
python -m tests.test_search_apis
```

**Note**: Oxford API test will fail as the API is deprecated (returns 404).

### Oxford API Test (Legacy)
Direct test of the Oxford API endpoint:

```bash
python -m tests.test_oxford_api
```

This test is kept for historical reference but will fail as the API is no longer available.

### Live Download Test
Full end-to-end test with actual downloads:

```bash
python -m tests.test_live
```

## Fixtures

The `fixtures/` directory contains sample API responses and test data:

- **`gallica_sample.xml`**: Sample XML response from Gallica's SRU API, useful for offline testing and understanding the response structure.

## Notes

- **Oxford/Bodleian**: As of January 2026, the public search API at `digital.bodleian.ox.ac.uk/api/search/` has been removed. Tests for this API are kept for documentation but will fail.
- **Gallica**: Uses the official BnF SRU API which is stable and well-documented.
- **Vaticana**: Does not have a public search API, only direct manifest resolution is supported.

## Adding New Tests

When adding new test scripts:

1. Place them in the `tests/` directory
2. Add a docstring explaining what the test does
3. Make sure they can be run with `python -m tests.test_name`
4. Update this README with the new test information
5. If the test requires sample data, add it to `fixtures/`
