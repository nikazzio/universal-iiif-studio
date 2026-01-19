import argparse
import sys

# pylint: disable=broad-exception-caught
from .logger import get_logger, setup_logging
from .logic import IIIFDownloader
from .resolvers.gallica import GallicaResolver
from .resolvers.generic import GenericResolver
from .resolvers.oxford import OxfordResolver
from .resolvers.vatican import VaticanResolver

logger = get_logger(__name__)


def resolve_url(input_str):
    """Finds the right resolver for the input."""
    resolvers = [
        VaticanResolver(),
        GallicaResolver(),
        OxfordResolver(),
        GenericResolver(),
    ]
    for res in resolvers:
        if res.can_resolve(input_str):
            result = res.get_manifest_url(input_str)
            # Check if valid manifest returned
            if result[0]:
                return result
    return None, None


def wizard_mode():
    """Interactive mode for better usability."""
    print("\n" + "=" * 40)
    print(" 🌍  UNIVERSAL IIIF DOWNLOADER  🌍")
    print("=" * 40 + "\n")

    url = input("Paste the URL (Manifest or Viewer link): ").strip()
    if not url:
        print("No URL provided. Exiting.")
        sys.exit(1)

    out_name = input("Output filename (optional, press Enter for auto): ").strip()
    ocr_model = input("OCR Model (optional, e.g. 'kraken', press Enter to skip): ").strip()

    return url, out_name, ocr_model


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Universal IIIF Downloader")
    parser.add_argument(
        "url",
        nargs="?",
        help="URL of the manuscript or manifest",
    )
    parser.add_argument("-o", "--output", help="Output PDF filename")
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=4,
        help="Concurrent downloads",
    )
    parser.add_argument(
        "--clean-cache",
        action="store_true",
        help="Clean cache",
    )
    parser.add_argument(
        "--prefer-images",
        action="store_true",
        help="Force image download even if official PDF exists",
    )
    parser.add_argument(
        "--ocr",
        help="Kraken model filename to run OCR after download",
    )
    parser.add_argument(
        "--create-pdf",
        action="store_true",
        help="Explicitly generate a PDF from the downloaded images",
    )

    args = parser.parse_args()

    # Wizard Mode if no URL
    if not args.url:
        url, out_name, ocr_model = wizard_mode()
        workers = 4
        clean = False
        prefer_images = False
        create_pdf = False
    else:
        url = args.url
        out_name = args.output
        workers = args.workers
        clean = args.clean_cache
        prefer_images = args.prefer_images
        ocr_model = args.ocr
        create_pdf = args.create_pdf

    # Resolve
    try:
        manifest_url, suggested_id = resolve_url(url)
        if not manifest_url:
            # If no specific resolver worked, treat input as manifest URL
            manifest_url = url
            suggested_id = None

        print(f"✅ Target Manifest: {manifest_url}")
        if suggested_id:
            print(f"🆔 Suggested ID: {suggested_id}")

        # Downloader
        downloader = IIIFDownloader(
            manifest_url=manifest_url,
            output_name=out_name,
            workers=workers,
            clean_cache=clean,
            prefer_images=prefer_images,
            ocr_model=ocr_model,
        )
        downloader.run()

        if create_pdf:
            downloader.create_pdf()

    except Exception as e:
        logger.exception("Fatal error during CLI execution")
        print(f"\n❌ Error: {e}")
        print("💡 Tip: 'Intelligent Support' tried to guess the Manifest from your URL.")
        print("   If this failed, please paste the direct link to the 'manifest.json'.")
        sys.exit(1)
