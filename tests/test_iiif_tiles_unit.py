"""Tests for universal_iiif_core.iiif_tiles — tile plan construction and math."""

from __future__ import annotations

from universal_iiif_core.iiif_tiles import (
    IIIFTilePlan,
    _pick_tile_spec,
    _tile_regions,
    build_tile_plan,
)


def _sample_info(width=4000, height=3000, tile_w=512, scale_factors=None):
    """Build a minimal info.json-like dict."""
    if scale_factors is None:
        scale_factors = [1, 2, 4, 8]
    return {
        "width": width,
        "height": height,
        "tiles": [{"width": tile_w, "scaleFactors": scale_factors}],
    }


def test_pick_tile_spec_basic():
    """Extract tile spec from standard info.json."""
    info = _sample_info(tile_w=512, scale_factors=[1, 2, 4])
    result = _pick_tile_spec(info)
    assert result is not None
    tile_w, tile_h, factors = result
    assert tile_w == 512
    assert tile_h == 512
    assert factors == [1, 2, 4]


def test_pick_tile_spec_with_explicit_height():
    """Tile spec should respect explicit height when provided."""
    info = {"width": 4000, "height": 3000, "tiles": [{"width": 256, "height": 128, "scaleFactors": [1]}]}
    result = _pick_tile_spec(info)
    assert result is not None
    tile_w, tile_h, _ = result
    assert tile_w == 256
    assert tile_h == 128


def test_pick_tile_spec_missing_tiles():
    """Return None when info.json has no tiles key."""
    assert _pick_tile_spec({}) is None
    assert _pick_tile_spec({"tiles": []}) is None
    assert _pick_tile_spec({"tiles": None}) is None


def test_pick_tile_spec_dict_tiles():
    """Handle info.json where tiles is a single dict instead of list."""
    info = {"tiles": {"width": 512, "scaleFactors": [1, 2]}}
    result = _pick_tile_spec(info)
    assert result is not None
    assert result[0] == 512


def test_pick_tile_spec_zero_width():
    """Return None when tile width is 0."""
    info = {"tiles": [{"width": 0, "scaleFactors": [1]}]}
    assert _pick_tile_spec(info) is None


def test_pick_tile_spec_single_scale_factor_int():
    """Handle scaleFactors as a single int instead of list."""
    info = {"tiles": [{"width": 512, "scaleFactors": 2}]}
    result = _pick_tile_spec(info)
    assert result is not None
    _, _, factors = result
    assert factors == [2]


def test_build_tile_plan_basic():
    """Build a tile plan from valid info.json."""
    info = _sample_info(width=4000, height=3000, tile_w=512)
    plan = build_tile_plan(info, "https://example.org/iiif/img1")
    assert plan is not None
    assert plan.full_width == 4000
    assert plan.full_height == 3000
    assert plan.tile_width == 512
    assert plan.scale_factor == 1
    assert plan.base_url == "https://example.org/iiif/img1"


def test_build_tile_plan_strips_trailing_slash():
    """Base URL should not have a trailing slash."""
    plan = build_tile_plan(_sample_info(), "https://example.org/iiif/img1/")
    assert plan is not None
    assert not plan.base_url.endswith("/")


def test_build_tile_plan_returns_none_for_invalid():
    """Return None for missing/invalid dimensions."""
    assert build_tile_plan({"width": 0, "height": 100, "tiles": [{"width": 512, "scaleFactors": [1]}]}, "u") is None
    assert build_tile_plan({"width": 100, "height": 0, "tiles": [{"width": 512, "scaleFactors": [1]}]}, "u") is None
    assert build_tile_plan({}, "u") is None
    assert build_tile_plan({"width": 100, "height": 100}, "u") is None


def test_tile_plan_out_dimensions():
    """Plan output dimensions should equal full dims at scale_factor=1."""
    plan = IIIFTilePlan(
        base_url="https://example.org",
        full_width=4000, full_height=3000,
        tile_width=512, tile_height=512, scale_factor=1,
    )
    assert plan.out_width == 4000
    assert plan.out_height == 3000


def test_tile_regions_covers_full_image():
    """Tile regions should cover the entire image without gaps."""
    plan = IIIFTilePlan(
        base_url="https://example.org",
        full_width=1024, full_height=768,
        tile_width=512, tile_height=512, scale_factor=1,
    )
    regions = list(_tile_regions(plan))
    # 2x2 grid for 1024x768 with 512px tiles
    assert len(regions) == 4

    # Verify full coverage
    xs = set()
    ys = set()
    for x, y, w, h in regions:
        xs.add(x)
        ys.add(y)
        assert x + w <= plan.full_width
        assert y + h <= plan.full_height

    assert 0 in xs
    assert 0 in ys


def test_tile_regions_non_divisible_dimensions():
    """Tile regions should handle images not evenly divisible by tile size."""
    plan = IIIFTilePlan(
        base_url="https://example.org", full_width=700, full_height=500, tile_width=512, tile_height=512, scale_factor=1
    )
    regions = list(_tile_regions(plan))
    # 2x1 grid (700/512 = 2 cols, 500/512 = 1 row)
    assert len(regions) == 2

    # Last tile should be smaller
    last_region = regions[-1]
    assert last_region[2] == 188  # 700 - 512
