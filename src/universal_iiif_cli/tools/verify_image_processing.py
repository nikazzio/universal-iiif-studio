"""Tool to verify local image handling for a downloaded manuscript."""

from __future__ import annotations

import argparse
import io
from pathlib import Path

from PIL import Image

from universal_iiif_core.config_manager import get_config_manager


def _default_image_path(library: str, doc_id: str, page: int) -> Path:
    downloads = Path(get_config_manager().get_downloads_dir())
    return downloads / library / doc_id / "scans" / f"pag_{page - 1:04d}.jpg"


def _simulate_iiif(image: Image.Image, region: str, size: str) -> Image.Image:
    if region != "full" and "," in region:
        x, y, w, h = map(int, region.split(","))
        image = image.crop((x, y, x + w, y + h))
    if size != "full":
        image = image.resize((int(image.width * 0.5), int(image.height * 0.5)))
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify image processing flow for Universal IIIF downloads.")
    parser.add_argument("--library", default="Vaticana", help="Library folder inside downloads/")
    parser.add_argument("--doc", default="Urb.lat.1779", help="Document identifier (folder name)")
    parser.add_argument("--page", type=int, default=7, help="1-based page index to inspect")
    parser.add_argument("--image", type=Path, help="Direct path to an image file (overrides library/doc/page)")
    parser.add_argument("--region", default="full", help="IIIF region specifier (e.g., 0,0,3000,3000)")
    parser.add_argument("--size", default="full", help="IIIF size specifier (e.g., full or 1000)")
    args = parser.parse_args()

    image_path = args.image if args.image else _default_image_path(args.library, args.doc, args.page)

    print("Testing image:", image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    img = Image.open(str(image_path))
    print(f"✴️ Opened {image_path.name} ({img.width}×{img.height})")

    try:
        processed = _simulate_iiif(img, args.region, args.size)
        buf = io.BytesIO()
        processed.convert("RGB").save(buf, format="JPEG", quality=90)
        print(f"✅ Output JPEG bytes: {len(buf.getvalue())}")
    finally:
        img.close()

    print("Done.")


if __name__ == "__main__":
    main()
