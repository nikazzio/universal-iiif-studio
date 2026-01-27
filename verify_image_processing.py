
import io
import os

from PIL import Image

# Target file
image_path = "/home/niki/work/personal/universal-iiif-downloader/downloads/Vaticana/Urb.lat.1779/scans/pag_0006.jpg"

print(f"Testing path: {image_path}")
if not os.path.exists(image_path):
    print("❌ File not found!")
    exit(1)

try:
    img = Image.open(image_path)
    print(f"✅ Image opened. Size: {img.size}")

    # Simulate Request: /0,0,3000,3000/full/0/default.jpg
    parts = ["0,0,3000,3000", "full", "0", "default.jpg"]

    region = parts[0]
    size = parts[1]
    rotation = parts[2]

    # 1. CROP
    if region != "full":
        if "," in region:
            x, y, w, h = map(int, region.split(','))
            print(f"✂️ Cropping: {x},{y},{w},{h}")
            img = img.crop((x, y, x + w, y + h))

    print(f"✅ Post-crop size: {img.size}")

    # 2. RESIZE
    if size != "full":
        print(f"📏 Resizing: {size}")
        # (Skipping complex logic for this test if full)

    # 3. OUTPUT
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    print(f"✅ Success! Output bytes: {len(buf.getvalue())}")

except Exception as e:
    print(f"❌ Error: {e}")
