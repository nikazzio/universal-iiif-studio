"""Tests for HTTPClient pure methods.

Covers HTTPMetrics, _resolve_policy, _compute_backoff,
_is_retriable_error, _handle_json_fallback.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from universal_iiif_core.http_client import HTTPClient, HTTPMetrics

# --- HTTPMetrics ---

class TestHTTPMetrics:
    def test_avg_response_time_empty(self):
        m = HTTPMetrics()
        assert m.avg_response_time_ms == 0.0

    def test_avg_response_time_calculation(self):
        m = HTTPMetrics(response_times=[0.1, 0.2, 0.3])
        assert round(m.avg_response_time_ms, 1) == 200.0

    def test_to_dict_keys(self):
        m = HTTPMetrics()
        d = m.to_dict()
        assert set(d.keys()) == {
            "total_requests",
            "successful_requests",
            "failed_requests",
            "retry_count",
            "rate_limit_hits",
            "timeout_count",
            "avg_response_time_ms",
            "per_host_stats",
        }

    def test_to_dict_avg_rounded(self):
        m = HTTPMetrics(response_times=[0.1234])
        d = m.to_dict()
        assert d["avg_response_time_ms"] == 123.4


# --- _resolve_policy ---

class TestResolvePolicy:
    def _make_client(self, **overrides) -> HTTPClient:
        policy = {
            "global": {"timeout_s": 30},
            "download": {"retries": 3},
            "libraries": overrides.get("libraries", {}),
        }
        return HTTPClient(network_policy=policy)

    def test_global_defaults(self):
        client = self._make_client()
        policy = client._resolve_policy("https://unknown.com/manifest.json")
        assert policy.get("timeout_s") == 30
        assert policy.get("retries") == 3

    def test_explicit_library_name(self):
        client = self._make_client(
            libraries={"gallica": {"use_custom_policy": True, "timeout_s": 60, "retries": 5}}
        )
        policy = client._resolve_policy("https://gallica.bnf.fr/manifest", library_name="Gallica")
        assert policy["timeout_s"] == 60
        assert policy["retries"] == 5

    def test_library_without_custom_policy_uses_global(self):
        client = self._make_client(
            libraries={"oxford": {"use_custom_policy": False, "timeout_s": 99}}
        )
        policy = client._resolve_policy("https://iiif.bodleian.ox.ac.uk/manifest", library_name="Oxford")
        assert policy["timeout_s"] == 30  # Global, not oxford's 99

    def test_hostname_fallback(self):
        client = self._make_client(
            libraries={"gallica": {"use_custom_policy": True, "timeout_s": 45}}
        )
        policy = client._resolve_policy("https://gallica.bnf.fr/iiif/manifest")
        assert policy["timeout_s"] == 45


# --- _compute_backoff ---

class TestComputeBackoff:
    def _make_client(self) -> HTTPClient:
        return HTTPClient(network_policy={"global": {}, "download": {}, "libraries": {}})

    def test_basic_exponential(self):
        client = self._make_client()
        policy = {"backoff_base_s": 2.0, "backoff_cap_s": 300.0}
        # attempt 0: 2*2^0=2, attempt 1: 2*2^1=4, attempt 2: 2*2^2=8
        assert client._compute_backoff(0, None, None, policy) == 2.0
        assert client._compute_backoff(1, None, None, policy) == 4.0
        assert client._compute_backoff(2, None, None, policy) == 8.0

    def test_cap_limits_backoff(self):
        client = self._make_client()
        policy = {"backoff_base_s": 100.0, "backoff_cap_s": 150.0}
        # 100*2^2=400, but capped to 150
        assert client._compute_backoff(2, None, None, policy) == 150.0

    def test_retry_after_header(self):
        client = self._make_client()
        policy = {"backoff_base_s": 1.0, "backoff_cap_s": 300.0, "respect_retry_after": True}
        # Retry-After 120s > base wait 1*2^0=1
        result = client._compute_backoff(0, 429, "120", policy)
        assert result == 120.0

    def test_retry_after_header_ignored_when_disabled(self):
        client = self._make_client()
        policy = {"backoff_base_s": 5.0, "backoff_cap_s": 300.0, "respect_retry_after": False}
        result = client._compute_backoff(0, 429, "120", policy)
        assert result == 5.0

    @patch("universal_iiif_core.http_client.get_host_limiter")
    def test_403_sets_cooldown(self, mock_limiter_fn):
        mock_limiter = MagicMock()
        mock_limiter_fn.return_value = mock_limiter
        client = self._make_client()
        policy = {"backoff_base_s": 1.0, "backoff_cap_s": 300.0, "cooldown_on_403_s": 60}
        client._compute_backoff(0, 403, None, policy, hostname="test.com")
        mock_limiter.set_cooldown.assert_called_once_with(60)

    @patch("universal_iiif_core.http_client.get_host_limiter")
    def test_429_sets_cooldown(self, mock_limiter_fn):
        mock_limiter = MagicMock()
        mock_limiter_fn.return_value = mock_limiter
        client = self._make_client()
        policy = {"backoff_base_s": 1.0, "backoff_cap_s": 300.0, "cooldown_on_429_s": 30}
        client._compute_backoff(0, 429, None, policy, hostname="test.com")
        mock_limiter.set_cooldown.assert_called_once_with(30)


# --- _is_retriable_error ---

class TestIsRetriableError:
    def _make_client(self) -> HTTPClient:
        return HTTPClient(network_policy={"global": {}, "download": {}, "libraries": {}})

    def test_retriable_status_codes(self):
        client = self._make_client()
        for code in [403, 429, 500, 502, 503, 504]:
            resp = MagicMock(spec=requests.Response)
            resp.status_code = code
            assert client._is_retriable_error(resp, None) is True, f"Expected {code} to be retriable"

    def test_non_retriable_status(self):
        client = self._make_client()
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 404
        assert client._is_retriable_error(resp, None) is False

    def test_timeout_exception_retriable(self):
        client = self._make_client()
        assert client._is_retriable_error(None, requests.Timeout()) is True

    def test_connection_error_retriable(self):
        client = self._make_client()
        assert client._is_retriable_error(None, requests.ConnectionError()) is True

    def test_value_error_not_retriable(self):
        client = self._make_client()
        assert client._is_retriable_error(None, ValueError()) is False

    def test_no_response_no_exception(self):
        client = self._make_client()
        assert client._is_retriable_error(None, None) is False


# --- _handle_json_fallback ---

class TestHandleJsonFallback:
    def _make_client(self) -> HTTPClient:
        return HTTPClient(network_policy={"global": {}, "download": {}, "libraries": {}})

    def test_bom_removal(self):
        client = self._make_client()
        resp = MagicMock(spec=requests.Response)
        resp.headers = {"content-encoding": ""}
        resp.text = '\ufeff{"key": "value"}'
        result = client._handle_json_fallback(resp)
        assert result == {"key": "value"}

    def test_whitespace_cleanup(self):
        client = self._make_client()
        resp = MagicMock(spec=requests.Response)
        resp.headers = {"content-encoding": ""}
        resp.text = '  \n  {"a": 1}  \n  '
        result = client._handle_json_fallback(resp)
        assert result == {"a": 1}

    def test_invalid_json_returns_none(self):
        client = self._make_client()
        resp = MagicMock(spec=requests.Response)
        resp.headers = {"content-encoding": ""}
        resp.text = "not valid json {{"
        result = client._handle_json_fallback(resp)
        assert result is None
