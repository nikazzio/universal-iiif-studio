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
    """Finds the right resolver for the input and returns (manifest_url, id, library_name)."""
    resolvers = [
        (VaticanResolver(), "Vaticana (BAV)"),
        (GallicaResolver(), "Gallica (BnF)"),
        (OxfordResolver(), "Bodleian (Oxford)"),
        (GenericResolver(), "Generic"),
    ]
    for res, lib_name in resolvers:
        if res.can_resolve(input_str):
            result = res.get_manifest_url(input_str)
            # Check if valid manifest returned
            if result[0]:
                return result[0], result[1], lib_name
    return None, None, "Unknown"


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
    """CLI entry point."""
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

    # DB Management commands
    parser.add_argument("--list", action="store_true", help="List all manuscripts in the database")
    parser.add_argument("--info", metavar="ID", help="Show detailed info for a manuscript")
    parser.add_argument("--delete", metavar="ID", help="Delete a manuscript from the database by ID")
    parser.add_argument(
        "--set-status", nargs=2, metavar=("ID", "STATUS"), help="Force update status (e.g. 'complete', 'error')"
    )

    args = parser.parse_args()

    # Wizard Mode if no URL
    if args.list:
        from pathlib import Path

        from iiif_downloader.config_manager import get_config_manager
        from iiif_downloader.storage.vault_manager import VaultManager

        vault = VaultManager()
        cm = get_config_manager()
        temp_dir = cm.get_temp_dir()

        mss = vault.get_all_manuscripts()

        print(f"\n📚 Library Database ({len(mss)} items)\n" + "=" * 80)
        print(f"{'ID':<25} | {'Status':<12} | {'Progress':<12} | {'Library'}")
        print("-" * 80)

        for m in mss:
            ms_id = m["id"]
            status = m.get("status") or "unknown"
            total = m.get("total_canvases") or 0

            # Determine real progress
            if status == "downloading" or status == "pending":
                # Check temp dir for active downloads
                t_path = temp_dir / ms_id
                if t_path.exists():
                    current = len(list(t_path.glob("pag_*.jpg")))
                else:
                    current = 0
            else:
                # For complete/error, trust DB or check final path
                current = m.get("downloaded_canvases") or 0
                if current == 0 and m.get("local_path"):
                    # Fallback check if DB wasn't updated correctly
                    l_path = Path(m["local_path"]) / "scans"
                    if l_path.exists():
                        current = len(list(l_path.glob("pag_*.jpg")))

            prog_str = f"{current}/{total}"

            # Visual status
            icon = (
                "✅"
                if status == "complete"
                else "⏳"
                if status == "downloading"
                else "❌"
                if status == "error"
                else "⚪"
            )

            print(f"{icon} {ms_id:<22} | {status:<12} | {prog_str:<12} | {m.get('library', 'Unknown')}")

        print("\n")
        sys.exit(0)

    if args.info:
        from iiif_downloader.storage.vault_manager import VaultManager

        ms_id = args.info
        vault = VaultManager()
        m = vault.get_manuscript(ms_id)
        if not m:
            print(f"❌ Manuscript not found: {ms_id}")
            sys.exit(1)

        print(f"\n📖 Manuscript Details: {ms_id}\n" + "=" * 50)
        for k, v in m.items():
            print(f"{k:<20}: {v}")
        print("\n")
        sys.exit(0)

    if args.delete:
        from iiif_downloader.storage.vault_manager import VaultManager

        ms_id = args.delete
        vault = VaultManager()
        if vault.delete_manuscript(ms_id):
            print(f"🗑️  Deleted manuscript record: {ms_id}")
        else:
            print(f"⚠️  Manuscript not found: {ms_id}")
        sys.exit(0)

    if args.set_status:
        from iiif_downloader.storage.vault_manager import VaultManager

        ms_id, new_status = args.set_status
        vault = VaultManager()
        if not vault.get_manuscript(ms_id):
            print(f"❌ Manuscript not found: {ms_id}")
            sys.exit(1)

        valid_statuses = ["pending", "downloading", "complete", "error"]
        if new_status not in valid_statuses:
            print(f"⚠️  Warning: '{new_status}' is not a standard status ({', '.join(valid_statuses)})")

        vault.update_status(ms_id, new_status)
        print(f"✅ Updated {ms_id} status to: {new_status}")
        sys.exit(0)

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
        manifest_url, suggested_id, library = resolve_url(url)
        if not manifest_url:
            # If no specific resolver worked, treat input as manifest URL
            if not url.startswith(("http://", "https://")):
                print(f"❌ Error: Invalid URL or ID '{url}'.")
                print("   Please provide a full URL (starting with http/https) or a supported Library ID.")
                print("   Supported IDs example: 'Vat.lat.3225' (Vaticana), 'btv1b...' (Gallica), or UUID (Oxford).")
                sys.exit(1)
            manifest_url = url
            suggested_id = None
            library = "Unknown"

        print(f"✅ Target Manifest: {manifest_url}")
        print(f"🏛️  Library: {library}")
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
            library=library,
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
