import os
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from PIL import Image
import requests

from .utils import get_json, ensure_dir, DEFAULT_HEADERS

# Try to import img2pdf
try:
    import img2pdf
    HAS_IMG2PDF = True
except ImportError:
    HAS_IMG2PDF = False

class IIIFDownloader:
    def __init__(self, manifest_url, output_dir="downloads", output_name=None, workers=4, clean_cache=False, keep_temp=False, prefer_images=False):
        self.manifest_url = manifest_url
        self.workers = workers
        self.clean_cache = clean_cache
        self.keep_temp = keep_temp
        self.prefer_images = prefer_images
        
        # Load Manifest
        print(f"Fetching Manifest: {manifest_url}...")
        self.manifest = get_json(manifest_url)
        
        self.label = self.manifest.get("label", "unknown_manuscript")
        if isinstance(self.label, list): 
             self.label = self.label[0] if self.label else "unknown_manuscript"

        # Determine Output Filename
        if not output_name:
             sanitized_label = "".join([c for c in str(self.label) if c.isalnum() or c in (' ', '.', '_', '-')]).strip().replace(" ", "_")
             output_name = f"{sanitized_label}.pdf"
        
        # Ensure output dir
        ensure_dir(output_dir)
        self.output_path = os.path.join(output_dir, output_name)
        self.ms_id = os.path.splitext(os.path.basename(output_name))[0]
        
        # Temp dir
        self.temp_dir = os.path.join("temp_images", self.ms_id)
        
    def get_pdf_url(self):
        """Checks for a native PDF link in the manifest."""
        # Check 'rendering' (common in IIIF v2/v3)
        rendering = self.manifest.get("rendering", [])
        if isinstance(rendering, dict): rendering = [rendering]
        
        for item in rendering:
            if isinstance(item, dict) and (item.get("format") == "application/pdf" or item.get("@id", "").lower().endswith(".pdf")):
                return item.get("@id") or item.get("id")

        # Check 'seeAlso' (sometimes used)
        see_also = self.manifest.get("seeAlso", [])
        if isinstance(see_also, dict): see_also = [see_also]
        
        for item in see_also:
            if isinstance(item, dict) and (item.get("format") == "application/pdf" or item.get("@id", "").lower().endswith(".pdf")):
                return item.get("@id") or item.get("id")
                
        return None

    def extract_metadata(self):
        """Extracts and saves metadata."""
        metadata = {
            "id": self.ms_id,
            "title": self.label,
            "attribution": self.manifest.get("attribution"),
            "description": self.manifest.get("description"),
            "manifest_url": self.manifest_url,
            "download_date": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        meta_path = os.path.splitext(self.output_path)[0] + "_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
        print(f"Metadata saved: {meta_path}")

    def get_canvases(self):
        """Extracts canvases from the manifest."""
        # Simple support for Sequence -> Canvases
        sequences = self.manifest.get('sequences', [])
        if not sequences:
            return []
        return sequences[0].get('canvases', [])

    def download_page(self, canvas, index, folder):
        """Downloads a single canvas."""
        try:
            # 1. Parse Image Resource
            images = canvas.get('images', [])
            if not images:
                 return None
            
            resource = images[0]['resource']
            base_url = resource.get('service', {}).get('@id')
            
            # Fallback for simple images (IIIF v2/v3 sometimes differs)
            if not base_url:
                 val = resource.get('@id', '')
                 base_url = val.split('/full/')[0] if '/full/' in val else val

            # 2. Prioritize Resolutions (Smaller first for speed, then Max)
            # 1740px is a sweet spot for readability and file size.
            priorities = [
                 (1740, "native"), (1740, "default"), 
                 ("max", "native"), ("max", "default")
            ]
            
            urls_to_try = []
            if base_url:
                for size, qual in priorities:
                    urls_to_try.append(f"{base_url}/full/{size},/0/{qual}.jpg")

            filename = os.path.join(folder, f"pag_{index:04d}.jpg")
            
            # 3. Download & Retry
            for attempt in range(3):
                for url in urls_to_try:
                    try:
                        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=20)
                        if r.status_code == 200 and r.content:
                            with open(filename, 'wb') as f:
                                f.write(r.content)
                            return filename
                    except Exception:
                        continue # Try next URL/Attempt
                
                time.sleep(1 + attempt) # Backoff
            
            print(f"Failed to download page {index} after retries.")
            return None
            
        except Exception as e:
            print(f"Error on page {index}: {e}")
            return None

    def create_pdf(self, files):
        """Combines downloaded images into a single PDF."""
        print(f"Generating PDF: {self.output_path}...")
        
        # Method A: img2pdf (Fast, precise)
        if HAS_IMG2PDF:
            try:
                with open(self.output_path, "wb") as f:
                    f.write(img2pdf.convert(files))
                print("✅ PDF successfully created with img2pdf.")
                return
            except Exception as e:
                print(f"img2pdf failed ({e}), falling back to PIL...")
        
        # Method B: Pillow (Slower, re-encodes)
        if files:
            images = [Image.open(f).convert('RGB') for f in files]
            images[0].save(self.output_path, save_all=True, append_images=images[1:])
            print("✅ PDF successfully created with Pillow.")

    def run(self):
        self.extract_metadata()
        
        # Native PDF check
        native_pdf = self.get_pdf_url()
        if native_pdf and not self.prefer_images:
            print(f"📄 Found Official PDF: {native_pdf}")
            print(f"⬇️  Downloading directly to {self.output_path} (this might take a while)...")
            try:
                with requests.get(native_pdf, stream=True, headers=DEFAULT_HEADERS) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get('content-length', 0))
                    with open(self.output_path, 'wb') as f, tqdm(
                        desc="Downloading PDF",
                        total=total_size,
                        unit='iB',
                        unit_scale=True,
                        unit_divisor=1024,
                    ) as bar:
                        for chunk in r.iter_content(chunk_size=8192):
                            size = f.write(chunk)
                            bar.update(size)
                print("✅ Download complete!")
                return
            except Exception as e:
                print(f"⚠️  Failed to download official PDF ({e}). Falling back to image assembly...")

        canvases = self.get_canvases()
        print(f"Found {len(canvases)} pages.")
        
        ensure_dir(self.temp_dir)
        
        downloaded = [None] * len(canvases)
        
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_index = {
                executor.submit(self.download_page, canvas, i, self.temp_dir): i
                for i, canvas in enumerate(canvases)
            }
            
            for future in tqdm(as_completed(future_to_index), total=len(canvases), unit="pag"):
                idx = future_to_index[future]
                downloaded[idx] = future.result()

        valid = [f for f in downloaded if f]
        if valid:
            self.create_pdf(valid)
            print("Done!")
        else:
            print("No pages downloaded.")
            
        if not self.keep_temp:
             import shutil
             shutil.rmtree(self.temp_dir)
