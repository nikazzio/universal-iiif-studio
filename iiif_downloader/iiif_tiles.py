from __future__ import annotations

import io
import math
import mmap
import time
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError
from requests import RequestException, Session


@dataclass(frozen=True)
class IIIFTilePlan:
    """Plan describing how to stitch IIIF tiles into one canvas."""

    base_url: str
    full_width: int
    full_height: int
    tile_width: int
    tile_height: int
    scale_factor: int

    @property
    def out_width(self) -> int:
        """Target canvas width for this plan."""
        return int(math.ceil(self.full_width / self.scale_factor))

    @property
    def out_height(self) -> int:
        """Target canvas height for this plan."""
        return int(math.ceil(self.full_height / self.scale_factor))


def _pick_tile_spec(info: dict[str, Any]) -> tuple[int, int, Iterable[int]] | None:
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
    info: dict[str, Any],
    base_url: str,
) -> IIIFTilePlan | None:
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
        mm[dst_off : dst_off + row_stride] = tile_bytes[src_off : src_off + row_stride]


def _tile_regions(plan: IIIFTilePlan) -> Iterable[tuple[int, int, int, int]]:
    step_x = plan.tile_width * plan.scale_factor
    step_y = plan.tile_height * plan.scale_factor

    for y in range(0, plan.full_height, step_y):
        h = min(step_y, plan.full_height - y)
        for x in range(0, plan.full_width, step_x):
            w = min(step_x, plan.full_width - x)
            yield x, y, w, h


def _fetch_info(session: Session, info_url: str, timeout_s: int) -> dict[str, Any] | None:
    try:
        r = session.get(info_url, timeout=timeout_s)
        r.raise_for_status()
        return r.json()
    except (RequestException, ValueError, OSError):
        return None


def _init_canvas_buffer(
    out_w: int,
    out_h: int,
    *,
    est_out_bytes: int,
    max_ram_bytes: int,
    out_path: Path,
) -> tuple[bool, Image.Image | None, Path | None, Any | None, mmap.mmap | None] | None:
    use_disk_buffer = est_out_bytes > int(max_ram_bytes)
    if not use_disk_buffer:
        try:
            canvas = Image.new("RGB", (out_w, out_h), (255, 255, 255))
        except (OSError, ValueError, MemoryError):
            return None
        return use_disk_buffer, canvas, None, None, None

    raw_path = out_path.with_name(out_path.stem + ".stitch.raw")
    raw_fh = None
    mm = None
    try:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_fh = raw_path.open("w+b")
        raw_fh.truncate(est_out_bytes)
        mm = mmap.mmap(raw_fh.fileno(), est_out_bytes, access=mmap.ACCESS_WRITE)
        return use_disk_buffer, None, raw_path, raw_fh, mm
    except (OSError, ValueError):
        if mm is not None:
            with suppress(OSError):
                mm.close()
        if raw_fh is not None:
            with suppress(OSError):
                raw_fh.close()
        if raw_path is not None:
            with suppress(OSError):
                raw_path.unlink(missing_ok=True)
        return None


def _cleanup_buffers(canvas: Image.Image | None, mm: mmap.mmap | None, raw_fh: Any | None, raw_path: Path | None):
    if canvas is not None:
        with suppress(OSError):
            canvas.close()
    if mm is not None:
        with suppress(OSError):
            mm.close()
    if raw_fh is not None:
        with suppress(OSError):
            raw_fh.close()
    if raw_path is not None:
        with suppress(OSError):
            raw_path.unlink(missing_ok=True)


def _fetch_tile_bytes(
    session: Session,
    tile_url: str,
    *,
    timeout_s: int,
    max_retries_per_tile: int,
    throttle_base_wait_s: float,
) -> bytes | None:
    for attempt in range(max_retries_per_tile):
        try:
            resp = session.get(tile_url, timeout=timeout_s)
            if resp.status_code == 429:
                time.sleep((2**attempt) * throttle_base_wait_s)
                continue
            resp.raise_for_status()
            tile_bytes = resp.content
            if not tile_bytes:
                raise ValueError("empty tile")
            return tile_bytes
        except (RequestException, ValueError):
            if attempt >= max_retries_per_tile - 1:
                return None
    return None


def _paste_tile_to_canvas(
    *,
    tile_bytes: bytes,
    use_disk_buffer: bool,
    mm: mmap.mmap | None,
    canvas: Image.Image | None,
    out_w: int,
    x: int,
    y: int,
    w: int,
    h: int,
) -> bool:
    try:
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
        return True
    except (UnidentifiedImageError, OSError, ValueError):
        return False


def _save_output(
    *,
    out_path: Path,
    use_disk_buffer: bool,
    out_w: int,
    out_h: int,
    mm: mmap.mmap | None,
    canvas: Image.Image | None,
    jpeg_quality: int,
) -> bool:
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if use_disk_buffer:
            assert mm is not None
            img = Image.frombuffer("RGB", (out_w, out_h), mm, "raw", "RGB", 0, 1)
            img.save(str(out_path), format="JPEG", quality=int(jpeg_quality), optimize=True)
            with suppress(OSError):
                img.close()
        else:
            assert canvas is not None
            canvas.save(str(out_path), format="JPEG", quality=int(jpeg_quality), optimize=True)
        return True
    except (OSError, ValueError):
        return False


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
) -> tuple[int, int] | None:
    """Download and stitch IIIF tiles sequentially into a JPEG.

    Returns (width, height) of the output image on success, else None.

        Memory behavior:
        - Never keeps more than one tile image in memory at a time.
        - If the uncompressed output would exceed `max_ram_bytes`, we assemble
            the RGB raster on disk (mmap) and then encode to JPEG.
    """
    info_url = base_url.rstrip("/") + "/info.json"
    info = _fetch_info(session, info_url, timeout_s)
    if not info:
        return None

    plan = build_tile_plan(info, base_url)
    if not plan:
        return None

    out_w, out_h = plan.out_width, plan.out_height
    est_out_bytes = out_w * out_h * 3
    buffer = _init_canvas_buffer(
        out_w,
        out_h,
        est_out_bytes=est_out_bytes,
        max_ram_bytes=max_ram_bytes,
        out_path=out_path,
    )
    if not buffer:
        return None
    use_disk_buffer, canvas, raw_path, raw_fh, mm = buffer

    for x, y, w, h in _tile_regions(plan):
        region = f"{x},{y},{w},{h}"
        size = f"{w},"
        tile_url = f"{plan.base_url}/{region}/{size}/0/{iiif_quality}.jpg"
        tile_bytes = _fetch_tile_bytes(
            session,
            tile_url,
            timeout_s=timeout_s,
            max_retries_per_tile=max_retries_per_tile,
            throttle_base_wait_s=throttle_base_wait_s,
        )
        if not tile_bytes:
            _cleanup_buffers(canvas, mm, raw_fh, raw_path)
            return None
        if not _paste_tile_to_canvas(
            tile_bytes=tile_bytes,
            use_disk_buffer=use_disk_buffer,
            mm=mm,
            canvas=canvas,
            out_w=out_w,
            x=x,
            y=y,
            w=w,
            h=h,
        ):
            _cleanup_buffers(canvas, mm, raw_fh, raw_path)
            return None

    saved = _save_output(
        out_path=out_path,
        use_disk_buffer=use_disk_buffer,
        out_w=out_w,
        out_h=out_h,
        mm=mm,
        canvas=canvas,
        jpeg_quality=jpeg_quality,
    )
    _cleanup_buffers(canvas, mm, raw_fh, raw_path)
    if not saved:
        return None
    return out_w, out_h
