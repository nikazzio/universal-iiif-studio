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
