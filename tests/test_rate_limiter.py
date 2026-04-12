"""Tests for _rate_limiter module.

Uses a monkeypatched fake clock so all tests run in <0.1s total
instead of 12s+ with real time.sleep() calls.
"""

from __future__ import annotations

import threading
from unittest.mock import patch

import pytest

from universal_iiif_core._rate_limiter import (
    HostRateLimiter,
    get_all_limiter_stats,
    get_host_limiter,
    reset_all_limiter_stats,
)


class _FakeClock:
    """Deterministic clock for rate-limiter tests."""

    def __init__(self) -> None:
        self._now = 1_000_000.0
        self._lock = threading.Lock()

    def time(self) -> float:
        with self._lock:
            return self._now

    def sleep(self, seconds: float) -> None:
        with self._lock:
            self._now += max(seconds, 0)


@pytest.fixture()
def clock():
    """Provide a fake clock and patch time.time/time.sleep in _rate_limiter."""
    fake = _FakeClock()
    with (
        patch("universal_iiif_core._rate_limiter.time.time", side_effect=fake.time),
        patch("universal_iiif_core._rate_limiter.time.sleep", side_effect=fake.sleep),
    ):
        yield fake


class TestHostRateLimiter:
    """Test HostRateLimiter sliding window and cooldown logic."""

    def test_basic_rate_limiting(self, clock: _FakeClock):
        """Sliding window allows max_requests, then blocks until window slides."""
        limiter = HostRateLimiter()

        for _ in range(3):
            assert limiter.wait_turn(window_s=1, max_requests=3) is True

        before = clock.time()
        assert limiter.wait_turn(window_s=1, max_requests=3) is True
        assert clock.time() - before >= 0.95

    def test_cooldown_enforcement(self, clock: _FakeClock):
        """Cooldown blocks requests until the period elapses."""
        limiter = HostRateLimiter()
        limiter.set_cooldown(1)

        before = clock.time()
        assert limiter.wait_turn(window_s=10, max_requests=100) is True
        assert clock.time() - before >= 0.95

    def test_cooldown_extends_if_longer(self, clock: _FakeClock):
        """A longer cooldown replaces a shorter one."""
        limiter = HostRateLimiter()

        limiter.set_cooldown(1)
        clock.sleep(0.5)
        limiter.set_cooldown(2)

        before = clock.time()
        assert limiter.wait_turn(window_s=10, max_requests=100) is True
        assert clock.time() - before >= 1.4

    def test_cooldown_does_not_shrink(self, clock: _FakeClock):
        """A shorter cooldown must not override a longer one."""
        limiter = HostRateLimiter()
        limiter.set_cooldown(2)
        limiter.set_cooldown(1)

        before = clock.time()
        assert limiter.wait_turn(window_s=10, max_requests=100) is True
        assert clock.time() - before >= 1.9

    def test_should_cancel_callback(self, clock: _FakeClock):
        """should_cancel=True causes wait_turn to return False immediately."""
        limiter = HostRateLimiter()
        limiter.set_cooldown(10)

        call_count = 0

        def should_cancel() -> bool:
            nonlocal call_count
            call_count += 1
            return call_count >= 2

        assert limiter.wait_turn(window_s=10, max_requests=100, should_cancel=should_cancel) is False

    def test_thread_safety(self, clock: _FakeClock):
        """Concurrent threads all complete without errors."""
        limiter = HostRateLimiter()
        results: list[bool] = []
        lock = threading.Lock()

        def worker():
            for _ in range(5):
                success = limiter.wait_turn(window_s=1, max_requests=50)
                with lock:
                    results.append(success)

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(results)
        assert len(results) == 15

    def test_stats_tracking(self, clock: _FakeClock):
        """Burst limit hits are counted in stats."""
        limiter = HostRateLimiter()

        for _ in range(3):
            limiter.wait_turn(window_s=1, max_requests=2)

        stats = limiter.get_stats()
        assert stats["total_waits"] >= 1
        assert stats["burst_limit_hits"] >= 1
        assert stats["last_request_time"] > 0

    def test_stats_cooldown_tracking(self, clock: _FakeClock):
        """Cooldown hits are counted when cooldown is active."""
        limiter = HostRateLimiter()
        limiter.set_cooldown(1)
        limiter.wait_turn(window_s=10, max_requests=100)

        assert limiter.get_stats()["cooldown_hits"] >= 1

    def test_reset_stats(self, clock: _FakeClock):
        """reset_stats zeroes all counters."""
        limiter = HostRateLimiter()
        limiter.set_cooldown(1)
        limiter.wait_turn(window_s=10, max_requests=100)
        limiter.reset_stats()

        stats = limiter.get_stats()
        assert stats["total_waits"] == 0
        assert stats["cooldown_hits"] == 0
        assert stats["burst_limit_hits"] == 0


class TestGlobalRegistry:
    """Test global rate limiter registry functions."""

    def test_get_host_limiter_singleton(self):
        limiter1 = get_host_limiter("example.com")
        limiter2 = get_host_limiter("example.com")
        assert limiter1 is limiter2

    def test_get_host_limiter_different_hosts(self):
        limiter1 = get_host_limiter("example.com")
        limiter2 = get_host_limiter("other.com")
        assert limiter1 is not limiter2

    def test_get_all_limiter_stats(self, clock: _FakeClock):
        limiter1 = get_host_limiter("test1.com")
        limiter2 = get_host_limiter("test2.com")

        limiter1.wait_turn(window_s=10, max_requests=100)
        limiter2.set_cooldown(1)
        limiter2.wait_turn(window_s=10, max_requests=100)

        all_stats = get_all_limiter_stats()
        assert "test1.com" in all_stats
        assert all_stats["test2.com"]["cooldown_hits"] >= 1

    def test_reset_all_limiter_stats(self, clock: _FakeClock):
        limiter1 = get_host_limiter("reset1.com")
        limiter2 = get_host_limiter("reset2.com")

        limiter1.set_cooldown(1)
        limiter1.wait_turn(window_s=10, max_requests=100)
        limiter2.set_cooldown(1)
        limiter2.wait_turn(window_s=10, max_requests=100)

        reset_all_limiter_stats()

        for stats in get_all_limiter_stats().values():
            assert stats["total_waits"] == 0
            assert stats["cooldown_hits"] == 0

    def test_registry_thread_safety(self):
        results: list[object] = []

        def worker(host_id: int):
            limiter = get_host_limiter(f"host{host_id}.com")
            results.append(limiter)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10
        assert len(set(id(r) for r in results)) == 10
