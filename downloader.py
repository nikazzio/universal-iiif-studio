import requests
import os
import argparse
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from tqdm import tqdm
import time

# Try to import img2pdf for better performance
try:
    import img2pdf
    HAS_IMG2PDF = True
except ImportError:
    HAS_IMG2PDF = False

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
}

def get_manifest_url(visualizer_url):
    """Extracts the manuscript ID and constructs the IIIF manifest URL."""
    ms_id = visualizer_url.strip("/").split("/")[-1]
    return f"https://digi.vatlib.it/iiif/{ms_id}/manifest.json"

def download_page(canvas, index, folder, headers, max_retries=3):
    """
    Downloads a single page image.
    Returns the path to the downloaded file if successful, else None.
    """
    try:
        # Determine the base image URL
        image_info = canvas['images'][0]['resource']
        if 'service' in image_info and '@id' in image_info['service']:
            base_url = image_info['service']['@id']
        else:
            base_url = image_info['@id'].split('/full/')[0]

        # Try high-quality but reasonable resolution (1740px) first, then max, then default
        urls_to_try = [
            f"{base_url}/full/1740,/0/native.jpg", # Best for reading, reasonable size
            f"{base_url}/full/1740,/0/default.jpg",
            f"{base_url}/full/max/0/native.jpg", # Can be huge
            f"{base_url}/full/max/0/default.jpg"
        ]

        filename = os.path.join(folder, f"pag_{index:04d}.jpg")
        
        for attempt in range(max_retries):
            for url in urls_to_try:
                try:
                    r = requests.get(url, headers=headers, timeout=30)
                    if r.status_code == 200 and "image" in r.headers.get('Content-Type', ''):
                        if len(r.content) == 0:
                            continue # Skip empty response

                        with open(filename, 'wb') as f:
                            f.write(r.content)
                        return filename
                except requests.RequestException:
                    pass # Try next URL or next attempt
            
            time.sleep(1 * (attempt + 1)) # Backoff

        print(f"\n[!] Failed to download page {index} after retries.")
        return None

    except Exception as e:
        print(f"\n[!] Error processing page {index}: {e}")
        return None

def create_pdf(image_files, output_pdf):
    """Creates a PDF from a list of image files."""
    if not image_files:
        print("No images to process.")
        return

    print(f"Generating PDF: {output_pdf}...")
    
    if HAS_IMG2PDF:
        print("Using img2pdf for efficient PDF creation...")
        try:
            with open(output_pdf, "wb") as f:
                f.write(img2pdf.convert(image_files))
            print("PDF created successfully!")
            return
        except Exception as e:
            print(f"img2pdf failed ({e}), falling back to PIL...")

    # Fallback to PIL
    print("Using PIL (loading images into memory)...")
    images = []
    try:
        for f in image_files:
            img = Image.open(f).convert('RGB')
            images.append(img)
        
        if images:
            images[0].save(output_pdf, save_all=True, append_images=images[1:])
            print("PDF created successfully!")
    except Exception as e:
        print(f"Error creating PDF with PIL: {e}")

def main():
    parser = argparse.ArgumentParser(description="Download Vatican Manuscripts as PDF.")
    parser.add_argument("url", help="URL of the manuscript viewer (e.g., https://digi.vatlib.it/view/MSS_Urb.lat.1779)")
    parser.add_argument("-o", "--output", help="Output PDF filename", default="manuscript.pdf")
    parser.add_argument("-k", "--keep-temp", action="store_true", help="Keep temporary image folder after PDF creation")
    parser.add_argument("--clean-cache", action="store_true", help="Remove all temporary files from previous runs immediately")
    parser.add_argument("-w", "--workers", type=int, default=4, help="Number of concurrent download threads (default: 4)")
    
    args = parser.parse_args()

    # Parse ID
    ms_id = args.url.strip("/").split("/")[-1]
    
    # Determine output filename
    output_filename = args.output
    if output_filename == "manuscript.pdf":
        output_filename = f"{ms_id}.pdf"

    # Ensure output is in "downloads" folder if no path specified
    if os.path.dirname(output_filename) == "":
        out_dir = "downloads"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        output_filename = os.path.join(out_dir, output_filename)
        print(f"Output folder set to: {out_dir}/")
    else:
        # If user specified a path (e.g. /tmp/foo.pdf), ensure dir exists
        out_dir = os.path.dirname(output_filename)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

    manifest_url = get_manifest_url(args.url)
    
    headers = DEFAULT_HEADERS.copy()
    headers['Referer'] = args.url

    print(f"Fetching manifest for {ms_id}...")
    try:
        response = requests.get(manifest_url, headers=headers)
        response.raise_for_status()
        manifest_data = response.json()
    except Exception as e:
        print(f"Error fetching manifest: {e}")
        return

    # Metadata Extraction
    metadata = {
        "id": ms_id,
        "title": manifest_data.get("label"),
        "attribution": manifest_data.get("attribution"),
        "description": manifest_data.get("description"),
        "manifest_url": manifest_url,
        "download_date": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Save metadata
    import json
    metadata_filename = f"{os.path.splitext(output_filename)[0]}_metadata.json"
    with open(metadata_filename, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)
    print(f"Metadata saved to: {metadata_filename}")

    canvases = manifest_data.get('sequences', [{}])[0].get('canvases', [])
    total_pages = len(canvases)
    print(f"Found {total_pages} pages.")

    # Temp Directory Management
    base_temp_dir = "temp_images"
    run_temp_dir = os.path.join(base_temp_dir, ms_id)
    
    if args.clean_cache:
        if os.path.exists(base_temp_dir):
            print(f"Cleaning all temporary cache in {base_temp_dir}...")
            shutil.rmtree(base_temp_dir)
        # If only cleaning, we might want to exit, or just continue with fresh start
    
    if os.path.exists(run_temp_dir):
        # We might want to resume, but for now let's clear to be safe or keep if resuming logic added later
        # User requested per-book organization. 
        # If we want to be safe, we clear THIS book's temp dir to avoid stale file issues
        if not args.keep_temp: 
             shutil.rmtree(run_temp_dir)
             os.makedirs(run_temp_dir)
    else:
        os.makedirs(run_temp_dir)

    downloaded_files = [None] * total_pages

    print(f"Downloading pages to {run_temp_dir} with {args.workers} workers...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_index = {
            executor.submit(download_page, canvas, i, run_temp_dir, headers): i 
            for i, canvas in enumerate(canvases)
        }

        for future in tqdm(as_completed(future_to_index), total=total_pages, unit="page"):
            index = future_to_index[future]
            path = future.result()
            downloaded_files[index] = path

    # Filter out failures
    valid_files = [f for f in downloaded_files if f is not None]
    
    if valid_files:
        create_pdf(valid_files, output_filename)
    else:
        print("No pages downloaded successfully.")

    if not args.keep_temp:
        print(f"Cleaning up temporary files for {ms_id}...")
        shutil.rmtree(run_temp_dir)
        # Try to remove base dir if empty
        try:
            os.rmdir(base_temp_dir)
        except OSError:
            pass # Directory not empty


if __name__ == "__main__":
    main()
