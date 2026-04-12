"""Tests for universal_iiif_core.iiif_logic — manifest URL rewriting and canvas counting."""

from __future__ import annotations

from universal_iiif_core.iiif_logic import rewrite_image_urls, total_canvases


def _v2_manifest(n_canvases: int = 3) -> dict:
    """Build a minimal IIIF v2 manifest with n canvases."""
    canvases = []
    for i in range(n_canvases):
        canvases.append(
            {
                "images": [
                    {
                        "resource": {
                            "@id": f"https://remote.example.org/iiif/page{i}/full/max/0/default.jpg",
                            "service": {"@id": f"https://remote.example.org/iiif/page{i}"},
                        }
                    }
                ]
            }
        )
    return {"sequences": [{"canvases": canvases}]}


def _v3_manifest(n_canvases: int = 3) -> dict:
    """Build a minimal IIIF v3 manifest with n canvases."""
    items = []
    for i in range(n_canvases):
        items.append(
            {
                "items": [
                    {
                        "items": [
                            {
                                "body": {
                                    "id": f"https://remote.example.org/iiif/page{i}/full/max/0/default.jpg",
                                    "service": [{"id": f"https://remote.example.org/iiif/page{i}"}],
                                }
                            }
                        ]
                    }
                ]
            }
        )
    return {"items": items}


def test_total_canvases_v2():
    """Count canvases in a IIIF v2 manifest."""
    assert total_canvases(_v2_manifest(5)) == 5


def test_total_canvases_v3():
    """Count canvases in a IIIF v3 manifest."""
    assert total_canvases(_v3_manifest(4)) == 4


def test_total_canvases_empty():
    """Empty manifest should return 0."""
    assert total_canvases({}) == 0
    assert total_canvases({"sequences": [{"canvases": []}]}) == 0


def test_rewrite_v2_images_replaces_urls():
    """Rewrite should replace v2 resource @id and strip service."""
    manifest = _v2_manifest(2)
    rewrite_image_urls(manifest, "http://localhost:8000", "gallica", "doc123")

    for idx, canvas in enumerate(manifest["sequences"][0]["canvases"]):
        resource = canvas["images"][0]["resource"]
        assert resource["@id"] == f"http://localhost:8000/downloads/gallica/doc123/scans/pag_{idx:04d}.jpg"
        assert "service" not in resource


def test_rewrite_v3_bodies_replaces_urls():
    """Rewrite should replace v3 body id and strip service."""
    manifest = _v3_manifest(2)
    rewrite_image_urls(manifest, "http://localhost:8000", "vatican", "mss_123")

    for idx, canvas in enumerate(manifest["items"]):
        body = canvas["items"][0]["items"][0]["body"]
        assert body["id"] == f"http://localhost:8000/downloads/vatican/mss_123/scans/pag_{idx:04d}.jpg"
        assert "service" not in body


def test_rewrite_noop_on_empty_manifest():
    """Rewrite should not crash on manifests without sequences/items."""
    manifest = {"label": "test"}
    rewrite_image_urls(manifest, "http://localhost:8000", "lib", "doc")
    assert manifest == {"label": "test"}


def test_rewrite_v2_skips_empty_resource():
    """Rewrite should handle canvases with empty/missing resource."""
    manifest = {"sequences": [{"canvases": [{"images": [{"resource": {}}]}, {"images": [{}]}]}]}
    rewrite_image_urls(manifest, "http://localhost:8000", "lib", "doc")
