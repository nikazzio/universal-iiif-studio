import os
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from PIL import Image
import requests

from .utils import clean_dir, ensure_dir, get_json, DEFAULT_HEADERS
from .logger import get_logger, get_download_logger

# Download Configuration Constants
MAX_DOWNLOAD_RETRIES = 5
BASE_RETRY_DELAY = 1  # seconds
VATICAN_MIN_DELAY = 1.5  # seconds
VATICAN_MAX_DELAY = 4.0  # seconds
NORMAL_MIN_DELAY = 0.4  # seconds
NORMAL_MAX_DELAY = 1.2  # seconds
THROTTLE_BASE_WAIT = 15  # seconds for 429 errors

# Try to import img2pdf
try:
    import img2pdf
    HAS_IMG2PDF = True
except ImportError:
    HAS_IMG2PDF = False

logger = get_logger(__name__)


def _sanitize_filename(label: str) -> str:
    safe = "".join(
        [c for c in str(label) if c.isalnum() or c in (" ", ".", "_", "-")]
    )
    return safe.strip().replace(" ", "_")


class IIIFDownloader:
    def __init__(
        self,
        manifest_url,
        output_dir="downloads",
        output_name=None,
        workers=4,
        clean_cache=False,
        prefer_images=False,
        ocr_model=None,
        progress_callback=None,
        skip_pdf: bool = True,
        library: str = "Unknown",
    ):
        self.manifest_url = manifest_url
        self.workers = workers
        self.clean_cache = clean_cache
        self.prefer_images = prefer_images
        self.ocr_model = ocr_model
        self.progress_callback = progress_callback
        self.skip_pdf = skip_pdf
        self.library = library
        self.keep_temp = True # Always True now as we use permanent pages/
        
        # Determine MS ID for naming
        sanitized_label = _sanitize_filename(str(self.label if hasattr(self, 'label') else 'temp'))
        self.ms_id = (output_name[:-4] if output_name and output_name.endswith(".pdf") else output_name) or sanitized_label
        
        #Initialize download-specific logger
        self.logger = get_download_logger(self.ms_id)

        # Load Manifest
        self.logger.info(f"Fetching manifest from {manifest_url}")
        print(f"Fetching Manifest: {manifest_url}...")
        self.manifest = get_json(manifest_url)

        self.label = self.manifest.get("label", "unknown_manuscript")
        if isinstance(self.label, list):
            self.label = self.label[0] if self.label else "unknown_manuscript"

        # Determine MS ID for naming
        sanitized_label = _sanitize_filename(str(self.label))
        self.ms_id = (output_name[:-4] if output_name and output_name.endswith(".pdf") else output_name) or sanitized_label

        # Ensure library directory exists
        lib_dir = os.path.join(output_dir, self.library)
        ensure_dir(lib_dir)

        # Ensure document-specific directory
        self.doc_dir = os.path.join(lib_dir, self.ms_id)
        ensure_dir(self.doc_dir)

        # Paths within the doc directory
        self.output_path = os.path.join(self.doc_dir, f"{self.ms_id}.pdf")
        self.meta_path = os.path.join(self.doc_dir, "metadata.json")
        self.ocr_path = os.path.join(self.doc_dir, "transcription.json")

        # Permanent pages directory within doc_dir
        self.pages_dir = os.path.join(self.doc_dir, "pages")
        ensure_dir(self.pages_dir)
        
        # Temp dir (still used for temporary assembly but pages/ is primary)
        self.temp_dir = self.pages_dir 
        
        # Robustness Setup
        import threading
        self._lock = threading.Lock()
        self._backoff_until = 0
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        
        # Vatican Specifics (Stealth Mode)
        if "vatlib.it" in self.manifest_url.lower():
            # 1. Handshake: Visit the viewer page to get session cookies
            viewer_url = self.manifest_url.replace("/iiif/", "/view/").replace("/manifest.json", "")
            try:
                print(f"🕵️ BAV Handshake: Initializing session via {viewer_url}...")
                self.session.get(viewer_url, timeout=20)
                self.session.headers.update({
                    "Referer": viewer_url,
                    "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
                })
            except:
                print("⚠️ Handshake failed, proceeding with default headers.")
            
            # 2. Optimized Concurrency: Re-allow parallel workers but keep BAV-specific headers
            print(f"�️ BAV Mode: Using {self.workers} workers with session persistence and stealth headers.")

    def get_pdf_url(self):
        """Checks for a native PDF link in the manifest."""
        # Check 'rendering' (common in IIIF v2/v3)
        rendering = self.manifest.get("rendering", [])
        if isinstance(rendering, dict):
            rendering = [rendering]

        for item in rendering:
            if not isinstance(item, dict):
                continue
            fmt = item.get("format")
            url = (item.get("@id") or item.get("id") or "").lower()
            if fmt == "application/pdf" or url.endswith(".pdf"):
                return item.get("@id") or item.get("id")

        # Check 'seeAlso' (sometimes used)
        see_also = self.manifest.get("seeAlso", [])
        if isinstance(see_also, dict):
            see_also = [see_also]

        for item in see_also:
            if not isinstance(item, dict):
                continue
            fmt = item.get("format")
            url = (item.get("@id") or item.get("id") or "").lower()
            if fmt == "application/pdf" or url.endswith(".pdf"):
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

        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
        self.logger.info(f"Metadata saved to {self.meta_path}")
        print(f"Metadata saved: {self.meta_path}")

    def get_canvases(self):
        """Extracts canvases from the manifest (v2) or items (v3)."""
        # IIIF v2
        sequences = self.manifest.get('sequences', [])
        if sequences:
            return sequences[0].get('canvases', [])

        # IIIF v3
        items = self.manifest.get('items', [])
        if items:
            # In v3, top-level items are often canvases
            # (or they might be nested in a sequence-like structure,
            # but usually it's items directly for the main content)
            return items

        return []

    def download_page(self, canvas, index, folder):
        """Downloads a single canvas."""
        try:
            # 1. Parse Image Resource
            images = canvas.get('images') or canvas.get('items') or []
            if not images:
                return None

            # Support both Annotation (v2/v3) and direct resources
            img_obj = images[0]
            
            # Check for annotation type (v2 uses '@type', v3 uses 'type')
            annotation_type = img_obj.get('@type') or img_obj.get('type') or ''
            
            if 'Annotation' in annotation_type:  # Matches both 'oa:Annotation' (v2) and 'Annotation' (v3)
                resource = img_obj.get('resource') or img_obj.get('body')
            else:
                resource = img_obj  # Direct resource in some v3 manifests

            if not resource:
                return None

            service = resource.get('service')
            if isinstance(service, list):
                service = service[0]
            base_url = (service or {}).get('@id') or (service or {}).get('id')

            # Fallback for simple images (IIIF v2/v3 sometimes differs)
            if not base_url:
                val = resource.get('@id') or resource.get('id') or ''
                base_url = val.split('/full/')[0] if '/full/' in val else val

            # 2. Prioritize Resolutions (Smaller first for speed, then Max)
            # 1740px is a sweet spot for readability and file size.
            priorities = [
                (1740, "native"),
                (1740, "default"),
                ("max", "native"),
                ("max", "default"),
            ]

            urls_to_try = []
            if base_url:
                for size, qual in priorities:
                    urls_to_try.append(f"{base_url}/full/{size},/0/{qual}.jpg")

            filename = os.path.join(folder, f"pag_{index:04d}.jpg")

            # 3. Download & Retry with Exponential Backoff
            import random
            for attempt in range(MAX_DOWNLOAD_RETRIES):
                # Global Throttle Check
                now = time.time()
                if now < self._backoff_until:
                    wait_time = self._backoff_until - now
                    # Add a bit of jitter to the wait as well
                    time.sleep(wait_time + random.uniform(0.1, 0.5))

                # Human-like Jitter between requests
                if "vatlib.it" in self.manifest_url.lower():
                    delay = random.uniform(VATICAN_MIN_DELAY, VATICAN_MAX_DELAY)
                else:
                    delay = random.uniform(NORMAL_MIN_DELAY, NORMAL_MAX_DELAY)
                time.sleep(delay)

                for url in urls_to_try:
                    try:
                        r = self.session.get(url, timeout=30)
                        
                        if r.status_code == 200 and r.content:
                            with open(filename, 'wb') as f:
                                f.write(r.content)
                            return filename
                            
                        if r.status_code == 429:
                            with self._lock:
                                wait = (2 ** attempt) * THROTTLE_BASE_WAIT
                                new_until = time.time() + wait
                                if new_until > self._backoff_until:
                                    self._backoff_until = new_until
                                    self.logger.warning(f"Rate limited (429) on page {index}, pausing {wait}s")
                                    print(f"⚠️ Global Throttling (429) on page {index}. Pausing for {wait}s...")
                            break # Retry after global pause
                            
                        if r.status_code == 403:
                            self.logger.warning(f"403 Forbidden on page {index}")
                            print(f"🚫 403 Forbidden on page {index}. Cooling down.")
                            time.sleep(10)

                    except requests.RequestException:
                        continue 

                time.sleep(1 + attempt)

            self.logger.error(f"Failed to download page {index} after {MAX_DOWNLOAD_RETRIES} retries")
            print(f"Failed to download page {index} after retries.")
            return None

        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error processing page {index}: {e}")
            print(f"Error on page {index}: {e}")
            return None

    def create_pdf(self, files=None):
        """Combines images into a PDF. If files is None, uses current pages_dir."""
        if files is None:
            files = sorted([
                os.path.join(self.pages_dir, f) 
                for f in os.listdir(self.pages_dir) 
                if f.startswith("pag_") and f.endswith(".jpg")
            ])
            
        if not files:
            print("No pages found to create PDF.")
            return

        print(f"Generating PDF: {self.output_path}...")

        # Method A: img2pdf (Fast, precise)
        if HAS_IMG2PDF:
            try:
                with open(self.output_path, "wb") as f:
                    f.write(img2pdf.convert(files))
                print(f"✅ PDF created: {self.output_path}")
                return
            except (ValueError, OSError, TypeError) as e:
                print(f"img2pdf failed ({e}), falling back to PIL...")

        # Method B: Pillow (Slower, re-encodes)
        images = [Image.open(f).convert('RGB') for f in files]
        images[0].save(
            self.output_path,
            save_all=True,
            append_images=images[1:],
        )
        print(f"✅ PDF created: {self.output_path}")

    def run(self):
        self.extract_metadata()

        # Option: clear temp cache before downloading pages
        if self.clean_cache:
            clean_dir(self.temp_dir)

        # Native PDF check
        native_pdf = self.get_pdf_url()
        if native_pdf and not self.prefer_images:
            print(f"📄 Found Official PDF: {native_pdf}")
            print(
                f"⬇️  Downloading directly to {self.output_path} "
                f"(this might take a while)..."
            )
            try:
                with self.session.get(
                    native_pdf,
                    stream=True,
                    timeout=60,
                ) as r:
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
            except (requests.RequestException, OSError, ValueError) as e:
                print(
                    f"⚠️  Failed to download official PDF ({e}). "
                    f"Falling back to image assembly..."
                )

        canvases = self.get_canvases()
        print(f"Found {len(canvases)} pages.")

        ensure_dir(self.temp_dir)

        downloaded = [None] * len(canvases)

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_index = {
                executor.submit(
                    self.download_page,
                    canvas,
                    i,
                    self.temp_dir,
                ): i
                for i, canvas in enumerate(canvases)
            }

            for future in tqdm(
                as_completed(future_to_index),
                total=len(canvases),
                unit="pag",
            ):
                idx = future_to_index[future]
                downloaded[idx] = future.result()
                if self.progress_callback:
                    # Provide (current, total)
                    self.progress_callback(len([f for f in downloaded if f is not None]), len(canvases))

        valid = [f for f in downloaded if f]
        if valid:
            # Optional PDF creation
            if not self.skip_pdf:
                self.create_pdf(valid)

            # Optional Batch OCR
            if self.ocr_model:
                self.run_batch_ocr(valid)

            print("Done!")
        else:
            print("No pages downloaded.")

    def run_batch_ocr(self, image_files):
        """Performs OCR on all downloaded images and saves aggregated JSON."""
        from .ocr.processor import OCRProcessor, KRAKEN_AVAILABLE
        from .ocr.model_manager import ModelManager

        if not KRAKEN_AVAILABLE:
            print("⚠️ OCR requested but Kraken is not available.")
            return

        manager = ModelManager()
        model_path = manager.get_model_path(self.ocr_model)
        if not model_path.exists():
            # Try to find if it's a key or a filename
            installed = manager.list_installed_models()
            if self.ocr_model in installed:
                model_path = manager.get_model_path(self.ocr_model)
            else:
                print(f"⚠️ OCR model not found: {self.ocr_model}")
                return

        print(f"🔍 Running OCR with model: {self.ocr_model}...")
        proc = OCRProcessor(model_path)
        aggregated_results = {
            "metadata": {
                "manuscript_id": self.ms_id,
                "model": self.ocr_model,
                "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "pages": []
        }

        for i, img_path in enumerate(tqdm(image_files, desc="OCR Processing")):
            try:
                result = proc.process_image(img_path)
                if "error" not in result:
                    result["page_index"] = i + 1
                    result["filename"] = os.path.basename(img_path)
                    aggregated_results["pages"].append(result)
            except Exception as e:
                print(f"Error processing page {i+1}: {e}")

        with open(self.ocr_path, "w", encoding="utf-8") as f:
            json.dump(aggregated_results, f, indent=4, ensure_ascii=False)
        print(f"✅ OCR results saved: {self.ocr_path}")
