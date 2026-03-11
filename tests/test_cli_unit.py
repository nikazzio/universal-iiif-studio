from universal_iiif_cli import cli


def test_resolve_manifest_uses_library_aware_resolver(monkeypatch):
    """CLI manifest resolution should preserve the detected library name."""
    monkeypatch.setattr(
        cli,
        "resolve_url_with_library",
        lambda _value: ("https://example.org/manifest.json", "DOC123", "Generic"),
    )

    manifest_url, suggested_id, library = cli._resolve_manifest("https://example.org/input")

    assert manifest_url == "https://example.org/manifest.json"
    assert suggested_id == "DOC123"
    assert library == "Generic"


def test_resolve_manifest_keeps_direct_manifest_urls():
    """Direct manifest URLs should still bypass resolver-specific detection."""
    original = cli.resolve_url_with_library
    cli.resolve_url_with_library = lambda _value: (None, None, "Unknown")
    try:
        manifest_url, suggested_id, library = cli._resolve_manifest("https://example.org/direct-manifest.json")
    finally:
        cli.resolve_url_with_library = original

    assert manifest_url == "https://example.org/direct-manifest.json"
    assert suggested_id is None
    assert library == "Unknown"
