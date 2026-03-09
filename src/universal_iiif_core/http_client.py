"""
Centralized HTTP client with retry, rate limiting, and per-library policy support.

This module provides a thread-safe HTTP client that consolidates:
- Per-library network policy overrides (timeout, retry, rate limiting)
- Automatic retry with exponential backoff
- Per-host rate limiting via HostRateLimiter
- Per-host concurrency limits via threading.Semaphore
- Unified error handling and metrics collection

Design principle: Every setting supports 3-level hierarchy:
    Parameter override > Library-specific config > Global defaults

This architecture enables unlimited library growth without code changes.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ._rate_limiter import get_host_limiter
from .utils import DEFAULT_HEADERS


@dataclass
class HTTPMetrics:
    """Metrics for HTTP client diagnostics."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retry_count: int = 0
    rate_limit_hits: int = 0
    timeout_count: int = 0
    response_times: list[float] = field(default_factory=list)
    per_host_stats: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def avg_response_time_ms(self) -> float:
        """Calculate average response time in milliseconds."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) * 1000 / len(self.response_times)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "retry_count": self.retry_count,
            "rate_limit_hits": self.rate_limit_hits,
            "timeout_count": self.timeout_count,
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
            "per_host_stats": self.per_host_stats,
        }


class HTTPClient:
    """
    Centralized HTTP client with per-library policy support.

    Supports unlimited library growth through configuration-driven
    policy resolution: parameter > library > host > global.
    """

    def __init__(self, network_policy: dict[str, Any], logger: logging.Logger | None = None):
        """
        Initialize HTTP client from network policy.

        Args:
            network_policy: Network policy dict with structure:
                {
                    "global": {<global defaults>},
                    "libraries": {
                        "gallica": {<library overrides>},
                        "bodleian": {<library overrides>},
                        ...
                    }
                }
            logger: Optional logger instance
        """
        self.network_policy = network_policy
        self.global_policy = network_policy.get("global", {})
        self.download_policy = network_policy.get("download", {})
        self.libraries = network_policy.get("libraries", {})
        self.logger = logger or logging.getLogger(__name__)

        # Session and coordination structures
        self.session = self._create_session()
        self.host_semaphores: dict[str, threading.Semaphore] = {}
        self.semaphore_lock = threading.Lock()
        self.metrics = HTTPMetrics()
        self.metrics_lock = threading.Lock()

    def _create_session(self) -> requests.Session:
        """Create requests.Session with default configuration."""
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)

        # Configure transport-level retries
        transport_retries = int(self.global_policy.get("transport_retries", 3))
        retry_strategy = Retry(
            total=max(0, transport_retries),
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=0,  # Use application-level backoff
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _resolve_policy(self, url: str, library_name: str | None = None) -> dict[str, Any]:
        """
        Resolve effective network policy for URL.

        Resolution order:
        1. Explicit library_name in libraries config
        2. Host-extracted library name (if matches known library)
        3. Global defaults

        Args:
            url: Target URL
            library_name: Optional explicit library identifier

        Returns:
            Merged policy dict with library overrides applied to global defaults
        """
        # Start with global and download defaults
        resolved = {**self.global_policy, **self.download_policy}

        # Try explicit library_name first
        if library_name and library_name in self.libraries:
            library_policy = self.libraries[library_name]
            resolved.update(library_policy)
            self.logger.debug(f"Using policy for library: {library_name}")
            return resolved

        # Fall back to hostname extraction
        hostname = urlparse(url).netloc
        if hostname:
            # Check if hostname matches any known library
            for lib_name, lib_policy in self.libraries.items():
                if lib_name in hostname or hostname in lib_name:
                    resolved.update(lib_policy)
                    self.logger.debug(f"Using policy for library: {lib_name} (matched from hostname: {hostname})")
                    return resolved

        # Default to global
        self.logger.debug(f"Using global policy for: {hostname or url}")
        return resolved

    def _get_setting(self, policy: dict[str, Any], key: str, default: Any = None) -> Any:
        """
        Get setting from policy with fallback.

        Args:
            policy: Resolved policy dict
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value
        """
        return policy.get(key, default)

    def _get_host_semaphore(self, host: str, policy: dict[str, Any]) -> threading.Semaphore:
        """
        Get or create per-host concurrency semaphore.

        Args:
            host: Hostname
            policy: Resolved policy for this host

        Returns:
            Semaphore for host concurrency control
        """
        with self.semaphore_lock:
            if host not in self.host_semaphores:
                # Get per-host concurrency limit from policy
                limit = int(
                    self._get_setting(policy, "per_host_concurrency", 4)
                    or self._get_setting(policy, "workers_per_job", 4)
                )
                self.host_semaphores[host] = threading.Semaphore(limit)
                self.logger.debug(f"Created semaphore for {host} with limit={limit}")
            return self.host_semaphores[host]

    def get_metrics(self) -> dict[str, Any]:
        """
        Get current HTTP metrics for diagnostics.

        Returns:
            Dict with metrics including per-host breakdown
        """
        with self.metrics_lock:
            return self.metrics.to_dict()

    def reset_metrics(self) -> None:
        """Reset metrics counters."""
        with self.metrics_lock:
            self.metrics = HTTPMetrics()

    def _update_metrics(
        self,
        success: bool,
        hostname: str,
        response_time: float,
        retries: int = 0,
        timeout: bool = False,
        rate_limited: bool = False,
    ) -> None:
        """
        Update internal metrics.

        Args:
            success: Whether request succeeded
            hostname: Target hostname
            response_time: Response time in seconds
            retries: Number of retries performed
            timeout: Whether request timed out
            rate_limited: Whether rate limit was hit
        """
        with self.metrics_lock:
            self.metrics.total_requests += 1
            if success:
                self.metrics.successful_requests += 1
            else:
                self.metrics.failed_requests += 1
            self.metrics.retry_count += retries
            if timeout:
                self.metrics.timeout_count += 1
            if rate_limited:
                self.metrics.rate_limit_hits += 1
            if response_time > 0:
                self.metrics.response_times.append(response_time)

            # Update per-host stats
            if hostname not in self.metrics.per_host_stats:
                self.metrics.per_host_stats[hostname] = {
                    "requests": 0,
                    "successes": 0,
                    "failures": 0,
                }
            host_stats = self.metrics.per_host_stats[hostname]
            host_stats["requests"] += 1
            if success:
                host_stats["successes"] += 1
            else:
                host_stats["failures"] += 1

    def _compute_backoff(
        self,
        attempt: int,
        status_code: int,
        retry_after_header: str | None,
        policy: dict[str, Any],
    ) -> float:
        """
        Calculate exponential backoff wait time.

        Args:
            attempt: Retry attempt number (0-indexed)
            status_code: HTTP status code
            retry_after_header: Optional Retry-After header value
            policy: Resolved network policy

        Returns:
            Wait time in seconds
        """
        # Exponential backoff: base * (2^attempt)
        backoff_base = float(
            self._get_setting(policy, "backoff_base_s", 15.0)
            or self._get_setting(policy, "default_backoff_base_s", 15.0)
        )
        backoff_cap = float(
            self._get_setting(policy, "backoff_cap_s", 300.0)
            or self._get_setting(policy, "default_backoff_cap_s", 300.0)
        )

        base_wait = backoff_base * (2**attempt)
        capped_wait = min(base_wait, backoff_cap)

        # Honor Retry-After header if configured
        retry_after_wait = 0.0
        respect_retry_after = bool(self._get_setting(policy, "respect_retry_after", True))
        if respect_retry_after and retry_after_header:
            try:
                retry_after_wait = max(float(retry_after_header), 0.0)
            except (ValueError, TypeError):
                self.logger.debug(f"Could not parse Retry-After header: {retry_after_header}")

        # Use the longer of backoff or Retry-After
        wait = max(capped_wait, retry_after_wait)

        # Apply cooldowns for 403/429 via rate limiter
        hostname = "unknown"  # Will be set by caller
        if status_code == 403:
            cooldown_s = int(self._get_setting(policy, "cooldown_on_403_s", 0))
            if cooldown_s > 0:
                limiter = get_host_limiter(hostname)
                limiter.set_cooldown(cooldown_s)
                self.logger.debug(f"Set {cooldown_s}s cooldown for {hostname} due to 403")
        elif status_code == 429:
            cooldown_s = int(self._get_setting(policy, "cooldown_on_429_s", 0))
            if cooldown_s > 0:
                limiter = get_host_limiter(hostname)
                limiter.set_cooldown(cooldown_s)
                self.logger.debug(f"Set {cooldown_s}s cooldown for {hostname} due to 429")

        return wait

    def _is_retriable_error(self, response: requests.Response | None, exception: Exception | None) -> bool:
        """
        Determine if error is retriable.

        Args:
            response: Response object if available
            exception: Exception if raised

        Returns:
            True if error is retriable
        """
        # Retriable status codes
        retriable_status_codes = {429, 500, 502, 503, 504}

        if response is not None:
            return response.status_code in retriable_status_codes

        # Retriable exceptions
        if exception is not None:
            return isinstance(exception, (requests.Timeout, requests.ConnectionError))

        return False

    def _retry_request(
        self,
        url: str,
        policy: dict[str, Any],
        hostname: str,
        timeout: tuple[int, int],
        **kwargs,
    ) -> requests.Response:
        """
        Execute request with retry logic.

        Args:
            url: Target URL
            policy: Resolved network policy
            hostname: Hostname for logging
            timeout: Timeout tuple (connect, read)
            **kwargs: Additional arguments for session.get()

        Returns:
            Response object

        Raises:
            requests.RequestException: On unrecoverable failure
        """
        max_retries = int(
            self._get_setting(policy, "retry_max_attempts", 5)
            or self._get_setting(policy, "default_retry_max_attempts", 5)
        )

        last_exception = None
        retry_count = 0

        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Request attempt {attempt + 1}/{max_retries} for {url}")

                response = self.session.get(url, timeout=timeout, **kwargs)

                # Check if we should retry based on status
                if self._is_retriable_error(response, None):
                    retry_count += 1
                    self.logger.debug(f"Retriable status {response.status_code} for {url}")

                    # Calculate backoff
                    wait = self._compute_backoff(
                        attempt, response.status_code, response.headers.get("Retry-After"), policy
                    )

                    # Special handling for 403/429: break early
                    if response.status_code in {403, 429}:
                        self.logger.warning(
                            f"Rate limit error {response.status_code} for {hostname}, backing off {wait:.1f}s"
                        )
                        if attempt < max_retries - 1:
                            time.sleep(wait)
                            continue
                        else:
                            # Last attempt, raise
                            response.raise_for_status()

                    # Other retriable errors
                    if attempt < max_retries - 1:
                        time.sleep(wait)
                        continue
                    else:
                        # Last attempt
                        response.raise_for_status()

                # Success or non-retriable error
                response.raise_for_status()
                return response

            except (requests.Timeout, requests.ConnectionError) as e:
                last_exception = e
                retry_count += 1
                self.logger.debug(f"Request exception for {url}: {e}")

                if attempt < max_retries - 1:
                    # Calculate backoff
                    wait = self._compute_backoff(attempt, 0, None, policy)
                    self.logger.debug(f"Retrying after {wait:.1f}s")
                    time.sleep(wait)
                else:
                    # Last attempt, raise
                    raise

            except requests.RequestException as e:
                # Non-retriable request exception
                self.logger.debug(f"Non-retriable exception for {url}: {e}")
                raise

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise requests.RequestException(f"Failed after {max_retries} attempts")
