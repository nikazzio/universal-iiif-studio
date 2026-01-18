from pathlib import Path

from PIL import Image

from iiif_downloader.pdf_utils import generate_pdf_from_images


def test_generate_pdf_from_images_creates_pdf(tmp_path: Path):
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    image_paths = []
    for i in range(3):
        img = Image.new("RGB", (200, 120), color=(255, 255, 255))
        p = images_dir / f"pag_{i:04d}.jpg"
        img.save(p, format="JPEG", quality=90)
        image_paths.append(str(p))

    out_pdf = tmp_path / "out.pdf"
    ok, msg = generate_pdf_from_images(image_paths, str(out_pdf))

    assert ok, msg
    assert out_pdf.exists(), "PDF file was not created"
    assert out_pdf.stat().st_size > 500, "PDF looks too small"
