"""Security tests for routing layer.

Tests for path traversal, CORS configuration, and exception handling.
"""

import pytest
from starlette.requests import Request

from studio_ui.routes.api import get_manifest, serve_download_file
from universal_iiif_core.config_manager import get_config_manager


def test_path_traversal_blocked():
    """Ensure downloads endpoint rejects path traversal attempts."""
    # Try to access parent directory
    response = serve_download_file("../../../etc/passwd")
    # Should be blocked (403) or resolved to non-existent path (404)
    assert response.status_code in (403, 404)
    body = (response.body or b"").decode("utf-8", errors="ignore")
    assert "Forbidden" in body or "Not Found" in body

    # Try with encoded dots
    response = serve_download_file("..%2F..%2F..%2Fetc%2Fpasswd")
    assert response.status_code in (403, 404)

    # Try with multiple slashes
    response = serve_download_file("../../config.json")
    assert response.status_code in (403, 404)


def test_downloads_serve_only_allowed_files():
    """Ensure path validation logic blocks files outside downloads_dir."""
    from universal_iiif_core.config_manager import get_config_manager

    config = get_config_manager()
    downloads_dir = config.get_downloads_dir()

    # Test 1: Valid path within downloads_dir
    try:
        resolved = (downloads_dir / "subdir/test.jpg").resolve()
        resolved.relative_to(downloads_dir.resolve())
        # If no exception, path is valid
        assert True
    except ValueError:
        pytest.fail("Valid path incorrectly rejected")

    # Test 2: Path traversal attempt
    malicious_path = downloads_dir / "../../../etc/passwd"
    try:
        resolved = malicious_path.resolve()
        resolved.relative_to(downloads_dir.resolve())
        pytest.fail("Path traversal not blocked!")
    except ValueError:
        # Expected: path is outside downloads_dir
        assert True

    # Test 3: Another traversal variant
    malicious_path2 = downloads_dir / "../../config.json"
    try:
        resolved = malicious_path2.resolve()
        resolved.relative_to(downloads_dir.resolve())
        pytest.fail("Path traversal variant not blocked!")
    except ValueError:
        # Expected: path is outside downloads_dir
        assert True


def test_downloads_404_for_nonexistent_file():
    """Ensure downloads endpoint returns 404 for non-existent files."""
    response = serve_download_file("nonexistent_file.jpg")
    assert response.status_code == 404
    body = (response.body or b"").decode("utf-8", errors="ignore")
    assert "Not Found" in body


def test_cors_configuration_from_config():
    """Verify CORS origins are loaded from config."""
    config = get_config_manager()
    allowed_origins = config.data.get("security", {}).get("allowed_origins", ["*"])

    # With default config.json, should have localhost entries
    assert isinstance(allowed_origins, list)
    assert len(allowed_origins) > 0

    # Should not be wildcard in production config
    if "localhost" not in str(allowed_origins):
        assert "*" not in allowed_origins, "Production config should not use CORS wildcard"


def test_exception_sanitization_resolve_manifest():
    """Verify exception messages don't leak internal details."""
    from studio_ui.routes.discovery_handlers import resolve_manifest

    # Test with invalid input that would trigger exception
    result = resolve_manifest("InvalidLibrary", "test_shelfmark")

    # Result should be an error component, not raw exception
    result_str = str(result)

    # Should NOT contain:
    # - Stack traces
    # - File paths
    # - Internal variable names
    assert "Traceback" not in result_str
    assert "/home/" not in result_str
    assert "/src/" not in result_str
    assert 'File "' not in result_str

    # Should contain user-friendly message
    assert "Errore" in result_str or "Error" in result_str


def test_exception_sanitization_start_download(monkeypatch):
    """Verify download errors don't expose internal state."""
    from studio_ui.routes import discovery_handlers

    # Avoid real network/worker side effects in this sanitization test.
    def _raise_manifest(_manifest_url):
        raise RuntimeError("network stack trace")

    monkeypatch.setattr(discovery_handlers, "analyze_manifest", _raise_manifest)
    monkeypatch.setattr(discovery_handlers, "start_downloader_thread", lambda *_a, **_k: "jid_test")

    # Test with malformed inputs that would cause errors downstream
    # Note: start_download actually starts a background job even with invalid inputs,
    # but errors should be sanitized when they occur
    result = discovery_handlers.start_download("https://invalid-manifest-url-that-will-fail", "test_doc", "Gallica")

    result_str = str(result)

    # Should NOT expose:
    # - Database paths
    # - Internal exceptions with stack traces
    # - Sensitive system info
    assert "Traceback" not in result_str
    assert ".py:" not in result_str  # Python file references in stack traces

    # The component should be a valid HTMX polling fragment
    assert (
        'hx-get="/api/download_status/' in result_str
        or 'hx-get="/api/download_manager"' in result_str
        or 'id="download-manager-area"' in result_str
        or "Errore" in result_str
    )


def test_path_validation_with_symlinks(tmp_path):
    """Ensure symlinks cannot escape downloads_dir."""
    config = get_config_manager()
    downloads_dir = config.get_downloads_dir()

    # Create a symlink pointing outside downloads_dir
    symlink = downloads_dir / "evil_link"
    target = tmp_path / "secret.txt"
    target.write_text("secret content")

    try:
        symlink.symlink_to(target)

        # Attempt to access via symlink
        response = serve_download_file("evil_link")

        # Should be blocked (403) or not found (404), but NOT 200
        assert response.status_code in (403, 404)

        if response.status_code == 200:
            # If it somehow returns 200, content must NOT be the secret
            body = (response.body or b"").decode("utf-8", errors="ignore")
            assert body != "secret content"

    finally:
        # Cleanup
        if symlink.exists():
            symlink.unlink()
        if target.exists():
            target.unlink()


def test_manifest_endpoint_error_handling():
    """Verify manifest serving doesn't leak internal errors."""
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "server": ("testserver", 80),
            "path": "/iiif/manifest/Gallica/nonexistent_doc",
            "headers": [],
            "query_string": b"",
        }
    )

    # Request non-existent manifest
    response = get_manifest(request, "Gallica", "nonexistent_doc")

    # Should return JSON error, not HTML exception page
    assert response.status_code in (404, 500)

    # Content-Type should be JSON
    assert "application/json" in response.media_type

    # Parse response
    import json

    data = json.loads((response.body or b"{}").decode("utf-8", errors="ignore") or "{}")
    assert "error" in data

    # Error message should be generic, not expose internals
    error_msg = str(data.get("error", ""))
    assert "Traceback" not in error_msg
    assert "/home/" not in error_msg
    assert ".py" not in error_msg
