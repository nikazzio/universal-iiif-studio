# HTTPClient - Centralized HTTP Client with Retry & Rate Limiting

## Overview

`HTTPClient` is a centralized HTTP client that provides:
- **Automatic retry** with exponential backoff
- **Per-host rate limiting** with sliding window algorithm
- **Per-library network policies** (timeout, concurrency, backoff)
- **Metrics tracking** (requests, retries, timeouts)
- **Thread-safe** operations with semaphores

Introduced in **Issue #71** to eliminate duplicate retry/backoff logic across the codebase.

---

## Location

- **Implementation**: `src/universal_iiif_core/http_client.py`
- **Rate Limiter**: `src/universal_iiif_core/_rate_limiter.py`
- **Configuration**: `src/universal_iiif_core/network_policy.py`
- **Tests**: `tests/test_http_client.py`, `tests/test_rate_limiter.py`

---

## Basic Usage

```python
from universal_iiif_core.http_client import HTTPClient
from universal_iiif_core.config_manager import get_config_manager

# Create client with config
cm = get_config_manager()
http_client = HTTPClient(network_policy=cm.data.get("settings", {}).get("network", {}))

# GET request
response = http_client.get(
    "https://example.com/api/data",
    library_name="gallica",  # Optional: canonical library key
    timeout=(30, 30),
)

# GET JSON
data = http_client.get_json(
    "https://example.com/api/manifest.json",
    library_name="gallica",
    timeout=(20, 20),
)
```

---

## Features

### 1. Automatic Retry with Exponential Backoff

- Retries on connection errors, timeouts, and 5xx status codes
- Exponential backoff: `base_wait * (2 ** attempt)`
- Configurable per library via `network_policy`
- Respects `Retry-After` headers

### 2. Per-Host Rate Limiting

- Sliding window algorithm tracks requests per host
- Enforces `burst_max_requests` within `burst_window_s`
- Cooldowns on 403/429 errors
- Shared across all `HTTPClient` instances via global registry

### 3. Per-Library Network Policies

Configure different policies per library in `network_policy.py`:

```python
"libraries": {
    "gallica": {
        "burst_max_requests": 4,
        "burst_window_s": 60,
        "retry_max_attempts": 5,
        "backoff_base_s": 20,
        "per_host_concurrency": 2
    }
}
```

Hierarchy: **Parameter override > Library config > Download defaults > Global defaults**

### 4. Concurrency Control

- `per_host_concurrency`: Limits parallel requests per host
- Uses semaphores to prevent overwhelming servers
- Default: 4 concurrent requests globally, 2 for Gallica

### 5. Metrics Tracking

```python
metrics = http_client.get_metrics()
print(f"Requests: {metrics['total_requests']}")
print(f"Retries: {metrics['retry_count']}")
print(f"Timeouts: {metrics['timeout_count']}")
```

---

## Migrated Modules (Phase 2 Complete)

| Module | Usage | Status |
| ------ | ----- | ------ |
| **downloader.py** | Canvas downloads | ✅ Migrated |
| **iiif_tiles.py** | Tile stitching | ✅ Migrated |
| **iiif_resolution.py** | Resolution probe, highres fetch | ✅ Migrated |
| **utils.py** | `get_json()` wrapper (legacy) | ✅ Migrated |
| **resolvers/discovery.py** | Manifest fetches | ✅ Migrated (JSON only) |
| **library_catalog.py** | External catalog scraping | ✅ Migrated |

**Code Reduction**: ~200+ lines of duplicate retry/backoff logic removed

---

## Configuration

### Global Defaults

```json
{
  "global": {
    "connect_timeout_s": 15,
    "read_timeout_s": 30,
    "per_host_concurrency": 4
  },
  "download": {
    "default_retry_max_attempts": 3,
    "default_backoff_base_s": 15,
    "default_backoff_cap_s": 300,
    "respect_retry_after": true
  }
}
```

### Library-Specific Overrides

Gallica example (strictest rate limiting):

```json
{
  "gallica": {
    "burst_max_requests": 4,
    "burst_window_s": 60,
    "retry_max_attempts": 5,
    "backoff_base_s": 20,
    "cooldown_on_403_s": 120,
    "cooldown_on_429_s": 300,
    "per_host_concurrency": 2
  }
}
```

---

## Architecture

### Policy Resolution (3-Level Hierarchy)

1. **Parameter override**: `http_client.get(url, timeout=10)`
2. **Library-specific config**: Matched by hostname in `network_policy["libraries"]`
3. **Global defaults**: Fallback from `network_policy["global"]`

### Rate Limiter (Shared State)

- `HostRateLimiter` instances stored in global `_HOST_LIMITERS` registry
- All `HTTPClient` instances share same rate limiter per host
- Ensures consistent rate limiting across the application

### Request Flow

```
1. Resolve policy (library + global + param overrides)
2. Acquire host semaphore (concurrency control)
3. Wait for rate limiter green light
4. Make request with timeout
5. Handle response:
   - Success → return response
   - Retriable error → exponential backoff, retry
   - 403/429 → set cooldown, retry
   - Non-retriable → raise exception
6. Release semaphore
7. Update metrics
```

---

## Testing

### Unit Tests

```bash
# HTTPClient tests (31+ tests)
pytest tests/test_http_client.py -v

# Rate limiter tests (14 tests)
pytest tests/test_rate_limiter.py -v

# Downloader regression (16 tests)
pytest tests/test_downloader_*.py -v
```

### Manual Testing

See `~/.copilot/session-state/.../files/manual-tests.md` for comprehensive test guide.

**Essential tests**:
1. Download standard manuscript (any library)
2. Download Gallica manuscript (verify slow rate: 4 req/min)
3. Pause/Resume (verify progress tracking)

---

## Migration Guide (For Future Code)

### Before (Old Code)

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry_strategy = Retry(total=3, backoff_factor=2, ...)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)

for attempt in range(max_retries):
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)
        else:
            raise
```

### After (HTTPClient)

```python
from universal_iiif_core.http_client import HTTPClient
from universal_iiif_core.config_manager import get_config_manager

cm = get_config_manager()
http_client = HTTPClient(network_policy=cm.data.get("settings", {}).get("network", {}))

# Automatic retry, backoff, rate limiting
data = http_client.get_json(url, library_name="gallica", timeout=(20, 20))
```

**Benefits**:
- ✅ 80% less code
- ✅ Consistent retry/backoff behavior
- ✅ Rate limiting automatically applied
- ✅ Metrics tracked
- ✅ Per-library policies

---

## Known Limitations

1. **Legacy `get_json()` in utils.py**: Creates temporary `HTTPClient` per call (inefficient). New code should create persistent instance.

2. **XML/HTML requests in resolvers**: Some discovery search calls still use `requests` directly (Gallica SRU XML API). Not critical, can be migrated later.

3. **Metrics are per-instance**: No global metrics aggregation yet. Each `HTTPClient` tracks its own metrics.

4. **Session still used in downloader**: For viewer URL prewarming (Gallica, Vatican). Kept separate from `HTTPClient`.

---

## Future Improvements

### Potential Phase 3 Tasks

1. **Global metrics endpoint** (deferred): Expose `/metrics` route with aggregated stats
2. **Async support**: Add async version for non-blocking operations
3. **Connection pooling stats**: Expose urllib3 pool metrics
4. **Retry budget**: Limit total retries per time window
5. **Circuit breaker**: Temporarily stop requests to failing hosts

---

## References

- **Issue**: [#71 - Centralized HTTP Client](https://github.com/nikazzio/scriptoria/issues/71)
- **Branch**: `feat/issue-71-centralized-http-client`
- **Implementation Plan**: `~/.copilot/session-state/.../plan.md`
- **Test Guide**: `~/.copilot/session-state/.../files/manual-tests.md`

---

## Summary

`HTTPClient` centralizes all HTTP operations with:
- ✅ **200+ lines of duplicate code eliminated**
- ✅ **6 core modules migrated** (downloader, tiles, resolution, utils, resolvers, catalog)
- ✅ **61+ tests passing** (45 HTTPClient + 16 downloader regression)
- ✅ **Per-library rate limiting** (Gallica: 4 req/min, others: 20 req/min)
- ✅ **Backward compatibility maintained** (`get_json()`, resolution functions)

**Status**: Phase 2 complete (100% core IIIF modules), Phase 3 pending (services migration).

---

## Related Features (v0.7.0)

### Professional Status Panel

The Studio interface now displays HTTP client metrics via a professional status panel:
- Color-coded badges for technical status (read_source, state, scans, staging, PDF info)
- **READ_SOURCE badge**: AMBER when remote (using HTTPClient to fetch from original server), GREEN when local
- Responsive grid layout for mobile and desktop
- Located in: `src/studio_ui/components/studio/status_panel.py`

### Mirador Viewing Modes

HTTPClient powers the remote preview mode:
- **Remote Mode**: Mirador loads original manifest, HTTPClient fetches images on-demand with rate limiting
- **Local Mode**: Uses local images, no HTTP requests needed
- Status panel shows current mode with color-coded badge
- See `docs/ARCHITECTURE.md` and `docs/wiki/Studio-Workflow.md` for details
