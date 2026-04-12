"""Shared utilities, constants, and HTTP helpers for discovery search modules."""

from __future__ import annotations

import re
from typing import Any, Final

from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.http_client import HTTPClient
from universal_iiif_core.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------

TIMEOUT_SECONDS: Final = 20
DISCOVERY_TIMEOUT: Final = (10, 20)

# ---------------------------------------------------------------------------
# Browser-like headers required by catalog/search surfaces that reject
# generic scripted requests with 403/500 responses.
# ---------------------------------------------------------------------------

REAL_BROWSER_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}
HTML_BROWSER_HEADERS: Final[dict[str, str]] = {
    **REAL_BROWSER_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ---------------------------------------------------------------------------
# Shared regex patterns
# ---------------------------------------------------------------------------

_HTML_TAG_RE: Final = re.compile(r"<[^>]+>")
_SPACE_RE: Final = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT_RE: Final = re.compile(r"\s+([,;:!?])")
_SPACE_BEFORE_SINGLE_PERIOD_RE: Final = re.compile(r"(?<!\.)\s+\.(?!\.)")

# ---------------------------------------------------------------------------
# Lazy HTTP client
# ---------------------------------------------------------------------------

_http_client_cache: HTTPClient | None = None


def get_search_http_client() -> HTTPClient:
    """Return a lazily-initialised HTTPClient for discovery searches."""
    global _http_client_cache  # noqa: PLW0603
    if _http_client_cache is None:
        cm = get_config_manager()
        network_policy = cm.data.get("settings", {}).get("network", {})
        _http_client_cache = HTTPClient(network_policy=network_policy)
    return _http_client_cache


# ---------------------------------------------------------------------------
# Text cleaning helpers
# ---------------------------------------------------------------------------


def clean_html_text(value: str) -> str:
    """Strip HTML tags, unescape entities, and collapse whitespace from *value*."""
    from html import unescape

    text = _HTML_TAG_RE.sub(" ", value)
    text = _SPACE_RE.sub(" ", unescape(text)).strip()
    text = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
    return _SPACE_BEFORE_SINGLE_PERIOD_RE.sub(".", text)


def regex_group_text(pattern: re.Pattern[str], chunk: str) -> str:
    """Return the first named-group value from *pattern* in *chunk*, or ``""``."""
    m = pattern.search(chunk)
    return clean_html_text(m.group("value")) if m else ""


def first_text(values: Any) -> str:
    """Extract the first non-empty string from a JSON value (scalar or list)."""
    if isinstance(values, str):
        return clean_html_text(values)
    if isinstance(values, list):
        for v in values:
            if isinstance(v, str) and v.strip():
                return clean_html_text(v)
    return ""
