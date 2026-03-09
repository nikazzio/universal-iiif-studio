"""Tests for http_client module - skeleton and policy resolution."""

import pytest

from universal_iiif_core.http_client import HTTPClient, HTTPMetrics


@pytest.fixture
def mock_network_policy():
    """Mock network policy with global and library-specific settings."""
    return {
        "global": {
            "connect_timeout_s": 10,
            "read_timeout_s": 30,
            "transport_retries": 3,
        },
        "download": {
            "default_retry_max_attempts": 5,
            "default_backoff_base_s": 15.0,
            "default_backoff_cap_s": 300.0,
            "respect_retry_after": True,
        },
        "libraries": {
            "gallica": {
                "connect_timeout_s": 15,
                "read_timeout_s": 45,
                "workers_per_job": 1,
                "min_delay_s": 2.5,
                "max_delay_s": 6.0,
                "burst_max_requests": 10,
                "retry_max_attempts": 3,
                "per_host_concurrency": 2,
            },
            "bodleian": {
                "read_timeout_s": 60,
                "burst_max_requests": 15,
                "per_host_concurrency": 3,
            },
            "vaticana": {
                "burst_max_requests": 25,
                "min_delay_s": 0.6,
            },
        },
    }


class TestHTTPClientInitialization:
    """Test HTTPClient initialization and setup."""

    def test_initialization_with_network_policy(self, mock_network_policy):
        """Test HTTPClient initializes correctly from network policy."""
        client = HTTPClient(mock_network_policy)

        assert client.network_policy == mock_network_policy
        assert client.global_policy == mock_network_policy["global"]
        assert client.download_policy == mock_network_policy["download"]
        assert client.libraries == mock_network_policy["libraries"]
        assert client.session is not None
        assert isinstance(client.metrics, HTTPMetrics)

    def test_session_configuration(self, mock_network_policy):
        """Test requests.Session is configured correctly."""
        client = HTTPClient(mock_network_policy)

        # Check session has adapters
        assert "http://" in client.session.adapters
        assert "https://" in client.session.adapters

        # Check headers are set
        assert len(client.session.headers) > 0


class TestPolicyResolution:
    """Test policy resolution hierarchy."""

    def test_resolve_policy_with_explicit_library_name(self, mock_network_policy):
        """Test explicit library_name takes priority."""
        client = HTTPClient(mock_network_policy)

        policy = client._resolve_policy("https://example.com/image.jpg", library_name="gallica")

        # Should have Gallica-specific settings
        assert policy["read_timeout_s"] == 45
        assert policy["workers_per_job"] == 1
        assert policy["retry_max_attempts"] == 3

        # Should also have global defaults for unspecified settings
        assert policy["connect_timeout_s"] == 15
        assert policy["default_backoff_base_s"] == 15.0

    def test_resolve_policy_hostname_matching(self, mock_network_policy):
        """Test hostname extraction matches known library."""
        client = HTTPClient(mock_network_policy)

        # Bodleian URL should match bodleian policy
        policy = client._resolve_policy("https://digital.bodleian.ox.ac.uk/objects/1234/images/567.jpg")

        # Should have Bodleian-specific settings
        assert policy["read_timeout_s"] == 60
        assert policy["per_host_concurrency"] == 3

        # Should inherit global for unspecified
        assert policy["connect_timeout_s"] == 10

    def test_resolve_policy_falls_back_to_global(self, mock_network_policy):
        """Test unknown library falls back to global defaults."""
        client = HTTPClient(mock_network_policy)

        policy = client._resolve_policy("https://unknown-library.org/image.jpg")

        # Should use global defaults
        assert policy["connect_timeout_s"] == 10
        assert policy["read_timeout_s"] == 30
        assert policy["default_retry_max_attempts"] == 5

    def test_resolve_policy_partial_overrides(self, mock_network_policy):
        """Test library can override only specific settings."""
        client = HTTPClient(mock_network_policy)

        # Vaticana overrides only some settings
        policy = client._resolve_policy("https://digi.vatlib.it/view/image.jpg", library_name="vaticana")

        # Should have Vaticana-specific overrides
        assert policy["burst_max_requests"] == 25
        assert policy["min_delay_s"] == 0.6

        # Should inherit global for unspecified
        assert policy["connect_timeout_s"] == 10
        assert policy["read_timeout_s"] == 30
        assert policy["default_retry_max_attempts"] == 5

    def test_get_setting_with_fallback(self, mock_network_policy):
        """Test _get_setting helper."""
        client = HTTPClient(mock_network_policy)

        policy = {"timeout": 30, "retries": 5}

        assert client._get_setting(policy, "timeout") == 30
        assert client._get_setting(policy, "missing") is None
        assert client._get_setting(policy, "missing", default=10) == 10


class TestHostSemaphoreManagement:
    """Test per-host concurrency semaphore management."""

    def test_get_host_semaphore_creates_new(self, mock_network_policy):
        """Test semaphore is created for new host."""
        client = HTTPClient(mock_network_policy)

        policy = client._resolve_policy("https://example.com", library_name="gallica")
        semaphore = client._get_host_semaphore("example.com", policy)

        assert semaphore is not None
        assert "example.com" in client.host_semaphores

    def test_get_host_semaphore_reuses_existing(self, mock_network_policy):
        """Test same host returns same semaphore."""
        client = HTTPClient(mock_network_policy)

        policy = client._resolve_policy("https://example.com", library_name="gallica")
        sem1 = client._get_host_semaphore("example.com", policy)
        sem2 = client._get_host_semaphore("example.com", policy)

        assert sem1 is sem2

    def test_get_host_semaphore_uses_policy_limit(self, mock_network_policy):
        """Test semaphore limit comes from policy."""
        client = HTTPClient(mock_network_policy)

        # Gallica has per_host_concurrency=2
        policy = client._resolve_policy("https://gallica.bnf.fr/", library_name="gallica")
        semaphore = client._get_host_semaphore("gallica.bnf.fr", policy)

        # Semaphore should allow 2 concurrent
        assert semaphore._value == 2  # Access internal value for testing

    def test_different_hosts_get_different_semaphores(self, mock_network_policy):
        """Test different hosts get separate semaphores."""
        client = HTTPClient(mock_network_policy)

        policy1 = client._resolve_policy("https://host1.com")
        policy2 = client._resolve_policy("https://host2.com")

        sem1 = client._get_host_semaphore("host1.com", policy1)
        sem2 = client._get_host_semaphore("host2.com", policy2)

        assert sem1 is not sem2


class TestMetrics:
    """Test metrics collection."""

    def test_initial_metrics_are_zero(self, mock_network_policy):
        """Test metrics start at zero."""
        client = HTTPClient(mock_network_policy)

        metrics = client.get_metrics()

        assert metrics["total_requests"] == 0
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 0
        assert metrics["retry_count"] == 0
        assert metrics["rate_limit_hits"] == 0
        assert metrics["timeout_count"] == 0
        assert metrics["avg_response_time_ms"] == 0.0

    def test_update_metrics_success(self, mock_network_policy):
        """Test updating metrics for successful request."""
        client = HTTPClient(mock_network_policy)

        client._update_metrics(success=True, hostname="example.com", response_time=0.5, retries=0)

        metrics = client.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["successful_requests"] == 1
        assert metrics["failed_requests"] == 0
        assert metrics["avg_response_time_ms"] > 0

    def test_update_metrics_failure(self, mock_network_policy):
        """Test updating metrics for failed request."""
        client = HTTPClient(mock_network_policy)

        client._update_metrics(success=False, hostname="example.com", response_time=0.0, retries=2)

        metrics = client.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 1
        assert metrics["retry_count"] == 2

    def test_update_metrics_timeout(self, mock_network_policy):
        """Test updating metrics for timeout."""
        client = HTTPClient(mock_network_policy)

        client._update_metrics(success=False, hostname="example.com", response_time=0.0, timeout=True)

        metrics = client.get_metrics()
        assert metrics["timeout_count"] == 1

    def test_update_metrics_rate_limited(self, mock_network_policy):
        """Test updating metrics for rate limit."""
        client = HTTPClient(mock_network_policy)

        client._update_metrics(success=False, hostname="example.com", response_time=0.0, rate_limited=True)

        metrics = client.get_metrics()
        assert metrics["rate_limit_hits"] == 1

    def test_per_host_stats(self, mock_network_policy):
        """Test per-host statistics tracking."""
        client = HTTPClient(mock_network_policy)

        client._update_metrics(success=True, hostname="host1.com", response_time=0.5)
        client._update_metrics(success=False, hostname="host1.com", response_time=0.0)
        client._update_metrics(success=True, hostname="host2.com", response_time=0.3)

        metrics = client.get_metrics()
        assert "host1.com" in metrics["per_host_stats"]
        assert "host2.com" in metrics["per_host_stats"]
        assert metrics["per_host_stats"]["host1.com"]["requests"] == 2
        assert metrics["per_host_stats"]["host1.com"]["successes"] == 1
        assert metrics["per_host_stats"]["host1.com"]["failures"] == 1
        assert metrics["per_host_stats"]["host2.com"]["requests"] == 1

    def test_reset_metrics(self, mock_network_policy):
        """Test metrics reset."""
        client = HTTPClient(mock_network_policy)

        client._update_metrics(success=True, hostname="example.com", response_time=0.5)
        client.reset_metrics()

        metrics = client.get_metrics()
        assert metrics["total_requests"] == 0
        assert metrics["successful_requests"] == 0

    def test_avg_response_time_calculation(self, mock_network_policy):
        """Test average response time is calculated correctly."""
        client = HTTPClient(mock_network_policy)

        client._update_metrics(success=True, hostname="test.com", response_time=0.1)
        client._update_metrics(success=True, hostname="test.com", response_time=0.3)
        client._update_metrics(success=True, hostname="test.com", response_time=0.2)

        metrics = client.get_metrics()
        # Average: (0.1 + 0.3 + 0.2) / 3 = 0.2s = 200ms
        assert 199.0 < metrics["avg_response_time_ms"] < 201.0
