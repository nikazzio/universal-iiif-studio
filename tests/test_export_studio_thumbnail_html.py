import json

from studio_ui.common.mirador import window_config_json
from studio_ui.components.viewer import mirador_viewer


def test_window_config_includes_manifest_url():
    """Mirador helper should embed the manifest URL in the config."""
    manifest_url = "https://example.org/iiif/manifest.json"
    cfg = json.loads(window_config_json(manifest_url))

    assert cfg["manifestId"] == manifest_url


def test_mirador_viewer_escapes_js_bootstrap_values():
    """Viewer bootstrap should JSON-escape JS string literals derived from inputs."""
    manifest_url = "https://example.org/iiif/ma'nifest\\test.json"
    container_id = "viewer'one\\two"
    rendered = "".join(str(part) for part in mirador_viewer(manifest_url, container_id))

    assert f"const containerId = {json.dumps(container_id)};" in rendered
    assert f"const manifestId = {json.dumps(manifest_url)};" in rendered
