"""Centralized HTTP client with retry, rate limiting, and per-library policy support.

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

import json
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ._rate_limiter import get_host_limiter
from .network_policy import normalize_library_key
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
    """Centralized HTTP client with per-library policy support.

    Supports unlimited library growth through configuration-driven
    policy resolution: parameter > library > host > global.
    """

    def __init__(self, network_policy: dict[str, Any], logger: logging.Logger | None = None):
        """Initialize HTTP client from network policy.

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
        """Resolve effective network policy for URL.

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
        if library_name:
            library_key = normalize_library_key(library_name)
            library_policy = self.libraries.get(library_key)
            if isinstance(library_policy, dict):
                if library_policy.get("use_custom_policy", library_key == "gallica"):
                    resolved.update(library_policy)
                    self.logger.debug(f"Using policy for library: {library_key}")
                else:
                    self.logger.debug(f"Using default policy for library: {library_key}")
                return resolved

        # Fall back to hostname extraction
        hostname = urlparse(url).netloc.lower()
        if hostname:
            # Check if hostname matches any known library
            for lib_name, lib_policy in self.libraries.items():
                if lib_name in hostname or hostname in lib_name:
                    if lib_policy.get("use_custom_policy", lib_name == "gallica"):
                        resolved.update(lib_policy)
                        self.logger.debug(f"Using policy for library: {lib_name} (matched from hostname: {hostname})")
                    else:
                        self.logger.debug(f"Using default policy for hostname match: {lib_name} ({hostname})")
                    return resolved

        # Default to global
        self.logger.debug(f"Using global policy for: {hostname or url}")
        return resolved

    def _wait_for_rate_limit(
        self,
        hostname: str,
        policy: dict[str, Any],
        *,
        should_cancel: Callable[[], bool] | None = None,
    ) -> None:
        """Block until the current host is allowed to make another request."""
        burst_window = int(self._get_setting(policy, "burst_window_s", 60))
        burst_max = int(self._get_setting(policy, "burst_max_requests", 100))
        limiter = get_host_limiter(hostname)
        if not limiter.wait_turn(
            window_s=burst_window,
            max_requests=burst_max,
            should_cancel=should_cancel,
        ):
            raise requests.RequestException("Request cancelled during rate limiting")

    def _get_setting(self, policy: dict[str, Any], key: str, default: Any = None) -> Any:
        """Get setting from policy with fallback.

        Args:
            policy: Resolved policy dict
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value
        """
        return policy.get(key, default)

    def _get_host_semaphore(self, host: str, policy: dict[str, Any]) -> threading.Semaphore:
        """Get or create per-host concurrency semaphore.

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
        """Get current HTTP metrics for diagnostics.

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
        """Update internal metrics.

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
        status_code: int | None,
        retry_after_header: str | None,
        policy: dict[str, Any],
        hostname: str = "unknown",
    ) -> float:
        """Calculate exponential backoff wait time.

        Args:
            attempt: Retry attempt number (0-indexed)
            status_code: HTTP status code
            retry_after_header: Optional Retry-After header value
            policy: Resolved network policy
            hostname: Hostname for rate limiter cooldown application

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
        """Determine if error is retriable.

        Args:
            response: Response object if available
            exception: Exception if raised

        Returns:
            True if error is retriable
        """
        # Retriable status codes
        retriable_status_codes = {403, 429, 500, 502, 503, 504}

        if response is not None:
            return response.status_code in retriable_status_codes

        # Retriable exceptions
        if exception is not None:
            return isinstance(exception, (requests.Timeout, requests.ConnectionError))

        return False

    def _sleep_before_retry(
        self,
        wait: float,
        *,
        url: str,
        should_cancel: Callable[[], bool] | None = None,
    ) -> bool:
        """Sleep before a retry unless the caller requested cancellation."""
        deadline = time.time() + max(float(wait), 0.0)
        while True:
            if should_cancel and should_cancel():
                self.logger.info(f"Request cancelled during backoff for {url}")
                return False
            remaining = deadline - time.time()
            if remaining <= 0:
                return True
            time.sleep(min(remaining, 0.25))

    def _retry_response_or_raise(
        self,
        *,
        response: requests.Response,
        attempt: int,
        max_retries: int,
        url: str,
        hostname: str,
        policy: dict[str, Any],
        retry_count: int,
        should_cancel: Callable[[], bool] | None = None,
        rate_limit_log: str | None = None,
    ) -> tuple[bool | None, int]:
        """Handle a retriable HTTP response.

        Returns:
            `(True, retry_count)` when caller should continue the retry loop,
            `(False, retry_count)` when the request should stop due to cancellation.
        """
        wait = self._compute_backoff(
            attempt, response.status_code, response.headers.get("Retry-After"), policy, hostname
        )
        if rate_limit_log:
            self.logger.warning(rate_limit_log.format(wait=wait))
        if attempt >= max_retries - 1:
            response.raise_for_status()
        if not self._sleep_before_retry(wait, url=url, should_cancel=should_cancel):
            return False, retry_count
        return True, retry_count

    def _retry_exception_or_raise(
        self,
        *,
        attempt: int,
        exception: Exception,
        max_retries: int,
        url: str,
        hostname: str,
        policy: dict[str, Any],
        retry_count: int,
        should_cancel: Callable[[], bool] | None = None,
        log_prefix: str = "Retrying after",
    ) -> tuple[bool | None, int]:
        """Handle a retriable transport exception.

        Returns:
            `(True, retry_count)` when caller should continue the retry loop,
            `(False, retry_count)` when the request should stop due to cancellation.
        """
        self.logger.debug(f"Request exception for {url}: {exception}")
        if attempt >= max_retries - 1:
            raise exception
        wait = self._compute_backoff(attempt, None, None, policy, hostname)
        self.logger.debug(f"{log_prefix} {wait:.1f}s")
        if not self._sleep_before_retry(wait, url=url, should_cancel=should_cancel):
            return False, retry_count
        return True, retry_count

    def _retry_request(
        self,
        url: str,
        policy: dict[str, Any],
        hostname: str,
        timeout: tuple[int, int],
        should_cancel: Callable[[], bool] | None = None,
        **kwargs,
    ) -> tuple[requests.Response | None, int]:
        """Execute request with retry logic.

        Args:
            url: Target URL
            policy: Resolved network policy
            hostname: Hostname for logging
            timeout: Timeout tuple (connect, read)
            should_cancel: Optional callable that returns True when operation should be cancelled
            **kwargs: Additional arguments for session.get()

        Returns:
            Tuple of (Response object, retry count), or `(None, retry_count)` if cancelled

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
                self._wait_for_rate_limit(hostname, policy, should_cancel=should_cancel)

                response = self.session.get(url, timeout=timeout, **kwargs)

                # Check if we should retry based on status
                if self._is_retriable_error(response, None):
                    retry_count += 1
                    self.logger.debug(f"Retriable status {response.status_code} for {url}")
                    should_continue, retry_count = self._retry_response_or_raise(
                        response=response,
                        attempt=attempt,
                        max_retries=max_retries,
                        url=url,
                        hostname=hostname,
                        policy=policy,
                        retry_count=retry_count,
                        should_cancel=should_cancel,
                        rate_limit_log=(
                            f"Rate limit error {response.status_code} for {hostname}, backing off {{wait:.1f}}s"
                            if response.status_code in {403, 429}
                            else None
                        ),
                    )
                    if should_continue is False:
                        return None, retry_count
                    continue

                # Success or non-retriable error
                response.raise_for_status()
                return response, retry_count

            except (requests.Timeout, requests.ConnectionError) as e:
                last_exception = e
                retry_count += 1
                should_continue, retry_count = self._retry_exception_or_raise(
                    attempt=attempt,
                    exception=e,
                    max_retries=max_retries,
                    url=url,
                    hostname=hostname,
                    policy=policy,
                    retry_count=retry_count,
                    should_cancel=should_cancel,
                )
                if should_continue is False:
                    return None, retry_count
                continue

            except requests.RequestException as e:
                # Non-retriable request exception
                self.logger.debug(f"Non-retriable exception for {url}: {e}")
                raise

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        # This should never happen but maintain the interface
        return self.session.get(url, timeout=timeout, **kwargs), retry_count

    def get(
        self,
        url: str,
        *,
        library_name: str | None = None,
        timeout: tuple[int, int] | None = None,
        retries: int | None = None,
        stream: bool = False,
        headers: dict[str, str] | None = None,
        should_cancel: Callable[[], bool] | None = None,
        **kwargs,
    ) -> requests.Response:
        """GET request with retry, rate limiting, and timeout.

        Integrates all HTTP client features:
        - Per-library policy resolution
        - Rate limiting via HostRateLimiter
        - Per-host concurrency control via Semaphore
        - Automatic retry with exponential backoff
        - Metrics collection

        Args:
            url: Target URL
            library_name: Optional library identifier for explicit policy lookup
            timeout: Override timeout as (connect, read) tuple
            retries: Override max retry attempts
            stream: Stream response body
            headers: Additional headers to merge with defaults
            should_cancel: Optional callable that returns True when operation should be cancelled
            **kwargs: Additional arguments passed to requests.Session.get()

        Returns:
            requests.Response object

        Raises:
            requests.RequestException: On unrecoverable failure or cancellation

        Examples:
            >>> client.get("https://example.com/image.jpg")
            >>> client.get("https://gallica.bnf.fr/image.jpg", library_name="gallica")
            >>> client.get("https://example.com/api", timeout=(5, 15), retries=3)
            >>> client.get("https://example.com/data", should_cancel=lambda: job.cancelled)
        """
        start_time = time.time()
        hostname = urlparse(url).netloc or "unknown"

        # Resolve effective policy
        policy = self._resolve_policy(url, library_name)

        # Resolve timeout (parameter > policy > default)
        if timeout is None:
            connect_timeout = int(self._get_setting(policy, "connect_timeout_s", 10))
            read_timeout = int(self._get_setting(policy, "read_timeout_s", 30))
            timeout = (connect_timeout, read_timeout)

        # Merge headers
        request_headers = dict(self.session.headers)
        if headers:
            request_headers.update(headers)

        # Get per-host semaphore for concurrency control
        semaphore = self._get_host_semaphore(hostname, policy)

        # Acquire concurrency semaphore
        acquired = semaphore.acquire(timeout=30)
        if not acquired:
            raise requests.RequestException(f"Could not acquire semaphore for {hostname}")

        metrics_recorded = False
        try:
            # Execute request with retry logic
            # Pass a modified policy if retries override was provided
            if retries is not None:
                policy = {**policy, "retry_max_attempts": retries}

            response, retry_count = self._retry_request(
                url,
                policy,
                hostname,
                timeout,
                should_cancel=should_cancel,
                stream=stream,
                headers=request_headers,
                **kwargs,
            )

            response_time = time.time() - start_time
            if response is None:
                self._update_metrics(
                    success=False,
                    hostname=hostname,
                    response_time=response_time,
                    retries=retry_count,
                )
                metrics_recorded = True
                raise requests.RequestException(f"Request to {url} was cancelled")

            # Update metrics on success
            self._update_metrics(
                success=True,
                hostname=hostname,
                response_time=response_time,
                retries=retry_count,
            )

            return response

        except requests.Timeout:
            # Update metrics on timeout
            response_time = time.time() - start_time
            if not metrics_recorded:
                self._update_metrics(
                    success=False,
                    hostname=hostname,
                    response_time=response_time,
                    timeout=True,
                )
            self.logger.warning(f"Request timeout for {hostname}: {url}")
            raise

        except requests.RequestException as e:
            # Update metrics on other failures
            response_time = time.time() - start_time
            rate_limited = "429" in str(e) or "rate limit" in str(e).lower()
            if not metrics_recorded:
                self._update_metrics(
                    success=False,
                    hostname=hostname,
                    response_time=response_time,
                    rate_limited=rate_limited,
                )
            self.logger.warning(f"Request failed for {hostname}: {url}, error: {e}")
            raise

        finally:
            semaphore.release()

    def post(
        self,
        url: str,
        *,
        library_name: str | None = None,
        timeout: tuple[int, int] | None = None,
        retries: int | None = None,
        headers: dict[str, str] | None = None,
        json: dict | None = None,
        data: bytes | str | None = None,
        **kwargs,
    ) -> requests.Response:
        """POST request with retry, rate limiting, and timeout."""
        start_time = time.time()
        hostname = urlparse(url).netloc or "unknown"
        policy = self._resolve_policy(url, library_name)

        if timeout is None:
            connect_timeout = int(self._get_setting(policy, "connect_timeout_s", 10))
            read_timeout = int(self._get_setting(policy, "read_timeout_s", 30))
            timeout = (connect_timeout, read_timeout)

        request_headers = dict(self.session.headers)
        if headers:
            request_headers.update(headers)

        semaphore = self._get_host_semaphore(hostname, policy)
        acquired = semaphore.acquire(timeout=30)
        if not acquired:
            raise requests.RequestException(f"Could not acquire semaphore for {hostname}")

        try:
            if retries is not None:
                policy = {**policy, "retry_max_attempts": retries}

            response, retry_count = self._post_with_retries(
                url=url,
                policy=policy,
                hostname=hostname,
                timeout=timeout,
                headers=request_headers,
                json_payload=json,
                data=data,
                **kwargs,
            )
            response_time = time.time() - start_time
            self._update_metrics(
                success=True,
                hostname=hostname,
                response_time=response_time,
                retries=retry_count,
            )
            return response

        except requests.Timeout:
            response_time = time.time() - start_time
            self._update_metrics(
                success=False,
                hostname=hostname,
                response_time=response_time,
                timeout=True,
            )
            self.logger.warning(f"POST request timeout for {hostname}: {url}")
            raise

        except requests.RequestException as e:
            response_time = time.time() - start_time
            rate_limited = any(token in str(e).lower() for token in ("403", "429", "rate limit"))
            self._update_metrics(
                success=False,
                hostname=hostname,
                response_time=response_time,
                rate_limited=rate_limited,
            )
            self.logger.warning(f"POST request failed for {hostname}: {url}, error: {e}")
            raise

        finally:
            if acquired:
                semaphore.release()

    def _post_with_retries(
        self,
        *,
        url: str,
        policy: dict[str, Any],
        hostname: str,
        timeout: tuple[int, int],
        headers: dict[str, str],
        json_payload: dict | None,
        data: bytes | str | None,
        **kwargs,
    ) -> tuple[requests.Response, int]:
        """POST request with retry, rate limiting, and timeout."""
        max_retries = int(self._get_setting(policy, "retry_max_attempts", 3))
        retry_count = 0

        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit(hostname, policy)
                response = self.session.post(
                    url,
                    json=json_payload,
                    data=data,
                    headers=headers,
                    timeout=timeout,
                    **kwargs,
                )
            except (requests.Timeout, requests.ConnectionError) as e:
                retry_count += 1
                should_continue, retry_count = self._retry_exception_or_raise(
                    attempt=attempt,
                    exception=e,
                    max_retries=max_retries,
                    url=url,
                    hostname=hostname,
                    policy=policy,
                    retry_count=retry_count,
                    log_prefix="Retrying POST after",
                )
                if should_continue:
                    continue
                raise requests.RequestException(f"POST request cancelled during backoff: {url}") from e

            if response.status_code in {403, 429, 500, 502, 503, 504}:
                retry_count += 1
                self.logger.debug(f"Retriable status {response.status_code} for POST {url}")
                should_continue, retry_count = self._retry_response_or_raise(
                    response=response,
                    attempt=attempt,
                    max_retries=max_retries,
                    url=url,
                    hostname=hostname,
                    policy=policy,
                    retry_count=retry_count,
                    rate_limit_log=(
                        f"Rate limit hit (POST {url}), waiting {{wait:.1f}}s. "
                        "Consider increasing burst_window_s or reducing concurrency."
                        if response.status_code in {403, 429}
                        else None
                    ),
                )
                if should_continue:
                    continue
                raise requests.RequestException(f"POST request cancelled during backoff: {url}")

            response.raise_for_status()
            return response, retry_count

        raise requests.RequestException(f"POST request failed after {max_retries} attempts: {url}")

    def get_json(
        self,
        url: str,
        *,
        library_name: str | None = None,
        timeout: tuple[int, int] | None = None,
        retries: int | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> dict[str, Any] | list[Any] | None:
        """GET JSON with automatic parsing and fallback handling.

        Wraps get() with JSON-specific parsing logic including:
        - Brotli decompression support
        - BOM removal
        - UTF-8 fallback decoding
        - Empty response handling

        Args:
            url: Target URL
            library_name: Optional library identifier
            timeout: Override timeout
            retries: Override retry attempts
            headers: Additional headers
            **kwargs: Additional arguments passed to get()

        Returns:
            Parsed JSON (dict or list) or None on failure

        Examples:
            >>> client.get_json("https://example.com/manifest.json")
            >>> client.get_json("https://api.example.com/data", library_name="gallica")
        """
        try:
            response = self.get(
                url,
                library_name=library_name,
                timeout=timeout,
                retries=retries,
                headers=headers,
                **kwargs,
            )

            # Handle empty response
            if not response.content:
                self.logger.warning(f"Empty response from {url}")
                return None

            # Try standard JSON parsing first
            try:
                return response.json()
            except ValueError:
                # JSON parse failed, try fallbacks
                self.logger.debug(f"Direct JSON parse failed for {url}, trying fallbacks")
                return self._handle_json_fallback(response)

        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch JSON from {url}: {e}")
            return None

    def _handle_json_fallback(self, response: requests.Response) -> dict[str, Any] | list[Any] | None:
        """Handle edge cases for JSON parsing.

        Tries multiple fallback strategies:
        1. Brotli decompression (if content-encoding: br)
        2. BOM removal and text cleanup
        3. Explicit UTF-8 decoding

        Args:
            response: Response object from requests

        Returns:
            Parsed JSON or None
        """
        # Try Brotli decompression
        content_encoding = response.headers.get("content-encoding", "").lower()
        if "br" in content_encoding:
            try:
                import brotli

                decoded = brotli.decompress(response.content)
                return json.loads(decoded.decode("utf-8"))
            except ImportError:
                self.logger.debug("Brotli compression detected but 'brotli' package not installed")
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.debug(f"Brotli decompression failed: {e}")

        # Try text cleanup (BOM removal, strip whitespace)
        try:
            text = response.text.strip()
            # Remove BOM if present
            if text.startswith("\ufeff"):
                text = text[1:]
            return json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"JSON fallback parsing failed: {e}")
            # Log preview for debugging
            self.logger.debug(f"Response preview: {response.text[:200]}")
            return None
