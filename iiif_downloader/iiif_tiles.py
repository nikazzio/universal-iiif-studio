from __future__ import annotations

import io
import math
import mmap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

from PIL import Image
from PIL import UnidentifiedImageError
from requests import RequestException, Session


@dataclass(frozen=True)
class IIIFTilePlan:
    base_url: str
    full_width: int
    full_height: int
    tile_width: int
    tile_height: int
    scale_factor: int

    @property
    def out_width(self) -> int:
        return int(math.ceil(self.full_width / self.scale_factor))

    @property
    def out_height(self) -> int:
        return int(math.ceil(self.full_height / self.scale_factor))


def _pick_tile_spec(info: Dict[str, Any]) -> Optional[Tuple[int, int, Iterable[int]]]:
    tiles = info.get("tiles")
    if not tiles:
        return None
    if isinstance(tiles, dict):
        tiles = [tiles]
    if not isinstance(tiles, list) or not tiles:
        return None

    spec = tiles[0]
    if not isinstance(spec, dict):
        return None

    tile_w = int(spec.get("width") or 0)
    tile_h = int(spec.get("height") or tile_w)
    scale_factors = spec.get("scaleFactors") or spec.get("scale_factors") or [1]
    if isinstance(scale_factors, int):
        scale_factors = [scale_factors]

    if tile_w <= 0:
        return None

    return tile_w, tile_h, [int(x) for x in scale_factors if int(x) > 0]


def build_tile_plan(
    info: Dict[str, Any],
    base_url: str,
) -> Optional[IIIFTilePlan]:
    """Create a stitching plan from `info.json`.

    This plan always targets full resolution (scaleFactor=1).

    The caller can decide whether to keep the output canvas in RAM or to
    use a disk-backed buffer (mmap) based on its own RAM cap.
    """

    try:
        full_w = int(info.get("width") or 0)
        full_h = int(info.get("height") or 0)
    except (TypeError, ValueError):
        return None

    if full_w <= 0 or full_h <= 0:
        return None

    tile_spec = _pick_tile_spec(info)
    if not tile_spec:
        return None
    tile_w, tile_h, _scale_factors = tile_spec

    return IIIFTilePlan(
        base_url=base_url.rstrip("/"),
        full_width=full_w,
        full_height=full_h,
        tile_width=tile_w,
        tile_height=tile_h,
        scale_factor=1,
    )


def _write_tile_rgb_to_mmap(
    mm: mmap.mmap,
    *,
    out_width: int,
    x: int,
    y: int,
    w: int,
    h: int,
    tile_rgb: Image.Image,
) -> None:
    if tile_rgb.mode != "RGB":
        tile_rgb = tile_rgb.convert("RGB")
    if tile_rgb.size != (w, h):
        # Servers can return slightly different sizes on edges; keep coverage.
        tile_rgb = tile_rgb.resize((w, h))

    tile_bytes = tile_rgb.tobytes()
    row_stride = w * 3
    for row in range(h):
        src_off = row * row_stride
        dst_off = ((y + row) * out_width + x) * 3
        mm[dst_off: dst_off + row_stride] = tile_bytes[src_off: src_off + row_stride]


def _tile_regions(plan: IIIFTilePlan) -> Iterable[Tuple[int, int, int, int]]:
    step_x = plan.tile_width * plan.scale_factor
    step_y = plan.tile_height * plan.scale_factor

    for y in range(0, plan.full_height, step_y):
        h = min(step_y, plan.full_height - y)
        for x in range(0, plan.full_width, step_x):
            w = min(step_x, plan.full_width - x)
            yield x, y, w, h


def stitch_iiif_tiles_to_jpeg(
    session: Session,
    base_url: str,
    out_path: Path,
    *,
    iiif_quality: str = "default",
    jpeg_quality: int = 90,
    max_ram_bytes: int = int(2 * (1024**3)),
    timeout_s: int = 30,
    max_retries_per_tile: int = 3,
    throttle_base_wait_s: float = 2.0,
) -> Optional[Tuple[int, int]]:
    """Download and stitch IIIF tiles sequentially into a JPEG.

    Returns (width, height) of the output image on success, else None.

        Memory behavior:
        - Never keeps more than one tile image in memory at a time.
        - If the uncompressed output would exceed `max_ram_bytes`, we assemble
            the RGB raster on disk (mmap) and then encode to JPEG.
    """

    info_url = base_url.rstrip("/") + "/info.json"
    try:
        r = session.get(info_url, timeout=timeout_s)
        r.raise_for_status()
        info = r.json()
    except (RequestException, ValueError, OSError):
        return None

    plan = build_tile_plan(info, base_url)
    if not plan:
        return None

    out_w, out_h = plan.out_width, plan.out_height
    est_out_bytes = out_w * out_h * 3
    use_disk_buffer = est_out_bytes > int(max_ram_bytes)

    canvas = None
    raw_path: Optional[Path] = None
    raw_fh = None
    mm = None

    if not use_disk_buffer:
        # Create the output canvas (this is the main RAM cost).
        try:
            canvas = Image.new("RGB", (out_w, out_h), (255, 255, 255))
        except (OSError, ValueError, MemoryError):
            return None
    else:
        # Disk-backed RGB buffer (avoid multi-GB RAM usage).
        raw_path = out_path.with_name(out_path.stem + ".stitch.raw")
        try:
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_fh = raw_path.open("w+b")
            raw_fh.truncate(est_out_bytes)
            mm = mmap.mmap(raw_fh.fileno(), est_out_bytes, access=mmap.ACCESS_WRITE)
        except (OSError, ValueError):
            try:
                if mm is not None:
                    mm.close()
            except OSError:
                pass
            try:
                if raw_fh is not None:
                    raw_fh.close()
            except OSError:
                pass
            try:
                if raw_path is not None:
                    raw_path.unlink(missing_ok=True)
            except OSError:
                pass
            return None

    for x, y, w, h in _tile_regions(plan):
        region = f"{x},{y},{w},{h}"
        size = f"{w},"
        tile_url = f"{plan.base_url}/{region}/{size}/0/{iiif_quality}.jpg"

        for attempt in range(max_retries_per_tile):
            try:
                resp = session.get(tile_url, timeout=timeout_s)
                if resp.status_code == 429:
                    time.sleep((2 ** attempt) * throttle_base_wait_s)
                    continue
                resp.raise_for_status()
                tile_bytes = resp.content
                if not tile_bytes:
                    raise ValueError("empty tile")

                with Image.open(io.BytesIO(tile_bytes)) as tile:
                    if use_disk_buffer:
                        assert mm is not None
                        _write_tile_rgb_to_mmap(
                            mm,
                            out_width=out_w,
                            x=x,
                            y=y,
                            w=w,
                            h=h,
                            tile_rgb=tile,
                        )
                    else:
                        assert canvas is not None
                        if tile.mode != "RGB":
                            tile = tile.convert("RGB")
                        if tile.size != (w, h):
                            tile = tile.resize((w, h))
                        canvas.paste(tile, (x, y))
                break
            except (RequestException, UnidentifiedImageError, OSError, ValueError):
                if attempt >= max_retries_per_tile - 1:
                    try:
                        if canvas is not None:
                            canvas.close()
                    except OSError:
                        pass
                    try:
                        if mm is not None:
                            mm.close()
                    except OSError:
                        pass
                    try:
                        if raw_fh is not None:
                            raw_fh.close()
                    except OSError:
                        pass
                    try:
                        if raw_path is not None:
                            raw_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                    return None

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if use_disk_buffer:
            assert mm is not None
            img = Image.frombuffer("RGB", (out_w, out_h), mm, "raw", "RGB", 0, 1)
            img.save(str(out_path), format="JPEG", quality=int(jpeg_quality), optimize=True)
            try:
                img.close()
            except OSError:
                pass
        else:
            assert canvas is not None
            canvas.save(str(out_path), format="JPEG", quality=int(jpeg_quality), optimize=True)
        return out_w, out_h
    except (OSError, ValueError):
        return None
    finally:
        try:
            if canvas is not None:
                canvas.close()
        except OSError:
            pass
        try:
            if mm is not None:
                mm.close()
        except OSError:
            pass
        try:
            if raw_fh is not None:
                raw_fh.close()
        except OSError:
            pass
        try:
            if raw_path is not None:
                raw_path.unlink(missing_ok=True)
        except OSError:
            pass
