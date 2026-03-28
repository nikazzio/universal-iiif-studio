from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

from PIL import Image
from requests import Response

from universal_iiif_core import iiif_resolution, library_catalog
from universal_iiif_core.http_client import HTTPClient
from universal_iiif_core.services.ocr.model_manager import ModelManager


def _make_jpeg_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color="white").save(buffer, format="JPEG")
    return buffer.getvalue()


class _RecordingLimiter:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def wait_turn(self, *, window_s: int, max_requests: int, should_cancel=None) -> bool:
        _ = should_cancel
        self.calls.append((window_s, max_requests))
        return True

    def set_cooldown(self, _seconds: int) -> None:
        return None


def test_http_client_get_reapplies_rate_limit_for_each_retry(monkeypatch):
    """Each retry attempt should consult the host rate limiter again."""
    policy = {
        "global": {"connect_timeout_s": 1, "read_timeout_s": 1, "per_host_concurrency": 1},
        "download": {"default_retry_max_attempts": 2},
        "libraries": {},
    }
    client = HTTPClient(policy)
    limiter = _RecordingLimiter()
    responses = [500, 200]

    def _fake_get(*_args, **_kwargs):
        response = Response()
        response.status_code = responses.pop(0)
        response._content = b'{"ok": true}'
        response.url = "https://example.com/data.json"
        return response

    monkeypatch.setattr("universal_iiif_core.http_client.get_host_limiter", lambda _host: limiter)
    monkeypatch.setattr(client.session, "get", _fake_get)
    monkeypatch.setattr("universal_iiif_core.http_client.time.sleep", lambda _seconds: None)

    result = client.get_json("https://example.com/data.json")

    assert result == {"ok": True}
    assert len(limiter.calls) == 2


def test_http_client_post_treats_403_as_retriable_and_rate_limited(monkeypatch):
    """POST should back off and retry on 403 responses."""
    policy = {
        "global": {"connect_timeout_s": 1, "read_timeout_s": 1, "per_host_concurrency": 1},
        "download": {"default_retry_max_attempts": 2},
        "libraries": {},
    }
    client = HTTPClient(policy)
    limiter = _RecordingLimiter()
    responses = [403, 200]

    def _fake_post(*_args, **_kwargs):
        response = Response()
        response.status_code = responses.pop(0)
        response._content = b'{"ok": true}'
        response.url = "https://example.com/api"
        return response

    monkeypatch.setattr("universal_iiif_core.http_client.get_host_limiter", lambda _host: limiter)
    monkeypatch.setattr(client.session, "post", _fake_post)
    monkeypatch.setattr("universal_iiif_core.http_client.time.sleep", lambda _seconds: None)

    response = client.post("https://example.com/api", json={"hello": "world"})

    assert response.status_code == 200
    assert len(limiter.calls) == 2


def test_probe_remote_max_dimensions_uses_network_node(monkeypatch):
    """Temporary clients for probes should use settings.network."""
    captured: dict[str, object] = {}
    network_policy = {"global": {"connect_timeout_s": 4}}

    class _FakeHTTPClient:
        def __init__(self, network_policy):
            captured["network_policy"] = network_policy

        def get_json(self, *_args, **_kwargs):
            return {"width": 1200, "height": 800}

    monkeypatch.setattr(
        "universal_iiif_core.config_manager.get_config_manager",
        lambda: SimpleNamespace(data={"settings": {"network": network_policy}}),
    )
    monkeypatch.setattr(iiif_resolution, "HTTPClient", _FakeHTTPClient)

    result = iiif_resolution.probe_remote_max_dimensions(
        {"items": [{"items": [{"items": [{"body": {"service": [{"@id": "https://example.com/iiif/page1"}]}}]}]}]},
        1,
    )

    assert result == (1200, 800, "https://example.com/iiif/page1")
    assert captured["network_policy"] == network_policy


def test_fetch_highres_page_image_streams_and_closes_response(tmp_path, monkeypatch):
    """High-res fetch should stream bytes to disk and always close the response."""
    request_kwargs: dict[str, object] = {}
    jpeg_bytes = _make_jpeg_bytes()

    class _FakeResponse:
        def __init__(self):
            self.status_code = 200
            self.closed = False

        @property
        def content(self):
            raise AssertionError("response.content should not be used for high-res downloads")

        def iter_content(self, chunk_size: int = 8192):
            for idx in range(0, len(jpeg_bytes), chunk_size):
                yield jpeg_bytes[idx : idx + chunk_size]

        def close(self):
            self.closed = True

    response = _FakeResponse()

    class _FakeHTTPClient:
        def get(self, url, **kwargs):
            request_kwargs["url"] = url
            request_kwargs["kwargs"] = kwargs
            return response

    out_path = tmp_path / "page.jpg"
    ok, message = iiif_resolution.fetch_highres_page_image(
        {"items": [{"items": [{"items": [{"body": {"service": [{"@id": "https://example.com/iiif/page1"}]}}]}]}]},
        1,
        out_path,
        http_client=_FakeHTTPClient(),
    )

    assert ok is True
    assert message == "ok"
    assert out_path.exists()
    assert request_kwargs["kwargs"]["stream"] is True
    assert response.closed is True


def test_extract_external_catalog_data_uses_network_node(monkeypatch):
    """Catalog enrichment should build HTTPClient from settings.network."""
    captured: dict[str, object] = {}
    network_policy = {"global": {"connect_timeout_s": 4}}

    class _FakeResponse:
        status_code = 200
        text = "<html><body><h1>Catalog title</h1></body></html>"

    class _FakeHTTPClient:
        def __init__(self, network_policy):
            captured["network_policy"] = network_policy

        def get(self, *_args, **_kwargs):
            return _FakeResponse()

    monkeypatch.setattr(
        "universal_iiif_core.config_manager.get_config_manager",
        lambda: SimpleNamespace(data={"settings": {"network": network_policy}}),
    )
    monkeypatch.setattr(library_catalog, "HTTPClient", _FakeHTTPClient)

    result = library_catalog.extract_external_catalog_data("https://example.com/item")

    assert result["reference_text"] == "Catalog title"
    assert captured["network_policy"] == network_policy


def test_model_manager_uses_network_node_and_closes_streaming_response(tmp_path, monkeypatch):
    """Model downloads should inherit settings.network and close streaming responses."""
    captured: dict[str, object] = {}
    network_policy = {"global": {"connect_timeout_s": 4}}
    payload = b"model-bytes"

    class _FakeResponse:
        def __init__(self):
            self.closed = False

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size: int = 8192):
            for idx in range(0, len(payload), chunk_size):
                yield payload[idx : idx + chunk_size]

        def close(self):
            self.closed = True

    response = _FakeResponse()

    class _FakeHTTPClient:
        def __init__(self, network_policy):
            captured["network_policy"] = network_policy

        def get(self, url, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs
            return response

    monkeypatch.setattr(
        "universal_iiif_core.config_manager.get_config_manager",
        lambda: SimpleNamespace(
            data={"settings": {"network": network_policy}},
            get_models_dir=lambda: tmp_path,
        ),
    )
    monkeypatch.setattr("universal_iiif_core.services.ocr.model_manager.HTTPClient", _FakeHTTPClient)

    manager = ModelManager()
    ok, message = manager._download_file("https://example.com/model.mlmodel", tmp_path / "model.mlmodel")

    assert ok is True
    assert "Downloaded model" in message
    assert captured["network_policy"] == network_policy
    assert captured["kwargs"]["stream"] is True
    assert response.closed is True
    assert (tmp_path / "model.mlmodel").read_bytes() == payload
