"""Host-based rate limiter with sliding window algorithm and cooldown support.

This module provides thread-safe per-host rate limiting for HTTP clients.
Originally extracted from downloader.py to enable centralized HTTP client.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class RateLimiterStats:
    """Statistics for rate limiter diagnostics."""

    total_waits: int = 0
    total_wait_time_s: float = 0.0
    cooldown_hits: int = 0
    burst_limit_hits: int = 0
    last_request_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_waits": self.total_waits,
            "total_wait_time_s": round(self.total_wait_time_s, 2),
            "cooldown_hits": self.cooldown_hits,
            "burst_limit_hits": self.burst_limit_hits,
            "last_request_time": self.last_request_time,
        }


class HostRateLimiter:
    """Thread-safe per-host rate limiter with sliding window algorithm.

    Limits requests to a host within a time window and supports cooldown periods
    for rate limit errors (403, 429). Multiple downloader instances can share
    the same limiter via get_host_limiter().

    Thread-safe for concurrent access.
    """

    def __init__(self) -> None:
        self._timestamps: deque[float] = deque()
        self._cooldown_until = 0.0
        self._lock = threading.Lock()
        self._stats = RateLimiterStats()

    def wait_turn(
        self,
        *,
        window_s: int,
        max_requests: int,
        should_cancel: Callable[[], bool] | None = None,
    ) -> bool:
        """Wait for rate limit slot, respecting burst window and cooldown.

        Args:
            window_s: Time window in seconds for burst limiting
            max_requests: Maximum requests allowed within window
            should_cancel: Optional callback to check if waiting should be cancelled

        Returns:
            True if request can proceed, False if cancelled

        Algorithm:
            - Sliding window: Track timestamps of recent requests
            - Cooldown: Honor cooldown period set by set_cooldown()
            - Burst limit: Enforce max_requests per window_s
        """
        wait_start = time.time()
        waited = False

        while True:
            if should_cancel and should_cancel():
                return False

            wait_s = 0.0
            now = time.time()

            with self._lock:
                # Check cooldown
                if now < self._cooldown_until:
                    wait_s = max(wait_s, self._cooldown_until - now)
                    if not waited:
                        self._stats.cooldown_hits += 1
                        waited = True

                # Prune old timestamps outside window
                cutoff = now - float(window_s)
                while self._timestamps and self._timestamps[0] <= cutoff:
                    self._timestamps.popleft()

                # Check if we can proceed
                if len(self._timestamps) < max_requests and wait_s <= 0:
                    self._timestamps.append(now)
                    self._stats.last_request_time = now
                    if waited:
                        wait_elapsed = now - wait_start
                        self._stats.total_waits += 1
                        self._stats.total_wait_time_s += wait_elapsed
                    return True

                # Calculate wait time
                if self._timestamps:
                    wait_s = max(wait_s, self._timestamps[0] + float(window_s) - now)
                    if not waited:
                        self._stats.burst_limit_hits += 1
                        waited = True
                else:
                    wait_s = max(wait_s, 0.05)

            time.sleep(max(wait_s, 0.05))

    def set_cooldown(self, cooldown_s: int) -> None:
        """Set cooldown period during which all requests are blocked.

        Used to handle rate limit errors (403, 429) by enforcing a pause
        before retrying. Multiple calls extend the cooldown if longer.

        Args:
            cooldown_s: Cooldown duration in seconds (0 or negative = no-op)
        """
        if cooldown_s <= 0:
            return
        until = time.time() + float(cooldown_s)
        with self._lock:
            if until > self._cooldown_until:
                self._cooldown_until = until

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiter statistics for diagnostics.

        Returns:
            Dict with stats: total_waits, total_wait_time_s, cooldown_hits,
            burst_limit_hits, last_request_time
        """
        with self._lock:
            return self._stats.to_dict()

    def reset_stats(self) -> None:
        """Reset statistics counters (does not reset cooldown or timestamps)."""
        with self._lock:
            self._stats = RateLimiterStats()


# Global registry for per-host rate limiters
_HOST_LIMITER_LOCK = threading.Lock()
_HOST_LIMITERS: dict[str, HostRateLimiter] = {}


def get_host_limiter(hostname: str) -> HostRateLimiter:
    """Get or create rate limiter for a hostname.

    Thread-safe singleton registry ensures all downloaders/clients share
    the same rate limiter for a given host.

    Args:
        hostname: Host identifier (e.g., "gallica.bnf.fr")

    Returns:
        HostRateLimiter instance for the host
    """
    with _HOST_LIMITER_LOCK:
        if hostname not in _HOST_LIMITERS:
            _HOST_LIMITERS[hostname] = HostRateLimiter()
        return _HOST_LIMITERS[hostname]


def get_all_limiter_stats() -> dict[str, dict[str, Any]]:
    """Get statistics for all registered rate limiters.

    Returns:
        Dict mapping hostname to rate limiter stats
    """
    with _HOST_LIMITER_LOCK:
        return {host: limiter.get_stats() for host, limiter in _HOST_LIMITERS.items()}


def reset_all_limiter_stats() -> None:
    """Reset statistics for all registered rate limiters."""
    with _HOST_LIMITER_LOCK:
        for limiter in _HOST_LIMITERS.values():
            limiter.reset_stats()
