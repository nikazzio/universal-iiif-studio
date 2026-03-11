"""Tests for _rate_limiter module."""

import pytest
import threading
import time

from universal_iiif_core._rate_limiter import (
    HostRateLimiter,
    get_all_limiter_stats,
    get_host_limiter,
    reset_all_limiter_stats,
)

# Mark as slow (uses time.sleep and threading)
pytestmark = pytest.mark.slow


class TestHostRateLimiter:
    """Test HostRateLimiter sliding window and cooldown logic."""

    def test_basic_rate_limiting(self):
        """Test basic sliding window rate limiting."""
        limiter = HostRateLimiter()

        # Should allow max_requests within window
        for _ in range(3):
            result = limiter.wait_turn(window_s=1, max_requests=3)
            assert result is True

        # Fourth request should wait for window to slide
        start = time.time()
        result = limiter.wait_turn(window_s=1, max_requests=3)
        elapsed = time.time() - start
        assert result is True
        assert elapsed >= 0.95  # Should wait ~1s

    def test_cooldown_enforcement(self):
        """Test cooldown period blocks all requests."""
        limiter = HostRateLimiter()

        # Set 1 second cooldown
        limiter.set_cooldown(1)

        # Request should wait for cooldown
        start = time.time()
        result = limiter.wait_turn(window_s=10, max_requests=100)
        elapsed = time.time() - start
        assert result is True
        assert elapsed >= 0.95

    def test_cooldown_extends_if_longer(self):
        """Test cooldown extends if new cooldown is longer."""
        limiter = HostRateLimiter()

        # Set short cooldown
        limiter.set_cooldown(1)
        time.sleep(0.5)

        # Extend with longer cooldown
        limiter.set_cooldown(2)

        # Should wait for the longer cooldown
        start = time.time()
        result = limiter.wait_turn(window_s=10, max_requests=100)
        elapsed = time.time() - start
        assert result is True
        assert elapsed >= 1.4  # ~2s total - 0.5s already elapsed

    def test_cooldown_does_not_shrink(self):
        """Test shorter cooldown does not override longer one."""
        limiter = HostRateLimiter()

        # Set long cooldown
        limiter.set_cooldown(2)

        # Try to set shorter cooldown (should be ignored)
        limiter.set_cooldown(1)

        # Should still wait for original longer cooldown
        start = time.time()
        result = limiter.wait_turn(window_s=10, max_requests=100)
        elapsed = time.time() - start
        assert result is True
        assert elapsed >= 1.9

    def test_should_cancel_callback(self):
        """Test should_cancel callback stops waiting."""
        limiter = HostRateLimiter()
        limiter.set_cooldown(2)  # Shorter cooldown for faster test

        cancel_flag = threading.Event()

        def should_cancel():
            return cancel_flag.is_set()

        # Start wait in thread
        result = [None]

        def wait_thread():
            result[0] = limiter.wait_turn(window_s=10, max_requests=100, should_cancel=should_cancel)

        thread = threading.Thread(target=wait_thread)
        thread.start()

        # Cancel immediately
        time.sleep(0.1)
        cancel_flag.set()
        thread.join(timeout=2.0)

        # Should have been cancelled (returned False)
        assert result[0] is False
        assert not thread.is_alive()  # Thread should have finished

    def test_thread_safety(self):
        """Test rate limiter is thread-safe."""
        limiter = HostRateLimiter()
        results = []
        lock = threading.Lock()

        def worker():
            for _ in range(5):
                success = limiter.wait_turn(window_s=1, max_requests=10)
                with lock:
                    results.append(success)

        # Run 3 workers concurrently
        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed
        assert all(results)
        assert len(results) == 15

    def test_stats_tracking(self):
        """Test statistics are tracked correctly."""
        limiter = HostRateLimiter()

        # Cause a burst limit hit
        for _ in range(3):
            limiter.wait_turn(window_s=1, max_requests=2)

        stats = limiter.get_stats()
        assert stats["total_waits"] >= 1
        assert stats["burst_limit_hits"] >= 1
        assert stats["last_request_time"] > 0

    def test_stats_cooldown_tracking(self):
        """Test cooldown hits are tracked."""
        limiter = HostRateLimiter()

        # Set cooldown and wait
        limiter.set_cooldown(1)
        limiter.wait_turn(window_s=10, max_requests=100)

        stats = limiter.get_stats()
        assert stats["cooldown_hits"] >= 1

    def test_reset_stats(self):
        """Test stats reset works."""
        limiter = HostRateLimiter()

        # Generate some stats
        limiter.set_cooldown(1)
        limiter.wait_turn(window_s=10, max_requests=100)

        # Reset
        limiter.reset_stats()

        stats = limiter.get_stats()
        assert stats["total_waits"] == 0
        assert stats["cooldown_hits"] == 0
        assert stats["burst_limit_hits"] == 0


class TestGlobalRegistry:
    """Test global rate limiter registry functions."""

    def test_get_host_limiter_singleton(self):
        """Test same host returns same limiter instance."""
        limiter1 = get_host_limiter("example.com")
        limiter2 = get_host_limiter("example.com")
        assert limiter1 is limiter2

    def test_get_host_limiter_different_hosts(self):
        """Test different hosts get different limiters."""
        limiter1 = get_host_limiter("example.com")
        limiter2 = get_host_limiter("other.com")
        assert limiter1 is not limiter2

    def test_get_all_limiter_stats(self):
        """Test getting stats for all limiters."""
        # Create some limiters with activity
        limiter1 = get_host_limiter("test1.com")
        limiter2 = get_host_limiter("test2.com")

        limiter1.wait_turn(window_s=10, max_requests=100)
        limiter2.set_cooldown(1)
        limiter2.wait_turn(window_s=10, max_requests=100)

        all_stats = get_all_limiter_stats()
        assert "test1.com" in all_stats
        assert "test2.com" in all_stats
        assert all_stats["test1.com"]["last_request_time"] > 0
        assert all_stats["test2.com"]["cooldown_hits"] >= 1

    def test_reset_all_limiter_stats(self):
        """Test resetting all limiter stats."""
        # Create limiters with activity
        limiter1 = get_host_limiter("reset1.com")
        limiter2 = get_host_limiter("reset2.com")

        limiter1.set_cooldown(1)
        limiter1.wait_turn(window_s=10, max_requests=100)
        limiter2.set_cooldown(1)
        limiter2.wait_turn(window_s=10, max_requests=100)

        # Reset all
        reset_all_limiter_stats()

        # Check stats are reset
        all_stats = get_all_limiter_stats()
        for stats in all_stats.values():
            assert stats["total_waits"] == 0
            assert stats["cooldown_hits"] == 0

    def test_registry_thread_safety(self):
        """Test global registry is thread-safe."""
        results = []

        def worker(host_id):
            limiter = get_host_limiter(f"host{host_id}.com")
            results.append(limiter)

        # Create limiters from multiple threads
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10
        # Each unique host should have exactly one instance
        unique_limiters = len(set(id(r) for r in results))
        assert unique_limiters == 10
