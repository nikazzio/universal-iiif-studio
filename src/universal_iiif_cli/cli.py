import argparse
import sys

from universal_iiif_core import __version__
from universal_iiif_core.logger import get_logger, setup_logging
from universal_iiif_core.logic import IIIFDownloader
from universal_iiif_core.resolvers.gallica import GallicaResolver
from universal_iiif_core.resolvers.generic import GenericResolver
from universal_iiif_core.resolvers.oxford import OxfordResolver
from universal_iiif_core.resolvers.vatican import VaticanResolver

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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Universal IIIF Downloader")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
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
    parser.add_argument("--delete-job", metavar="JOB_ID", help="Delete a download job record from the DB by job_id")
    parser.add_argument(
        "--set-status", nargs=2, metavar=("ID", "STATUS"), help="Force update status (e.g. 'complete', 'error')"
    )
    return parser


def _render_library_table(mss, temp_dir):
    from pathlib import Path

    print(f"\n📚 Library Database ({len(mss)} items)\n" + "=" * 80)
    print(f"{'ID':<25} | {'Status':<12} | {'Progress':<12} | {'Library'}")
    print("-" * 80)

    for m in mss:
        ms_id = m["id"]
        status = m.get("status") or "unknown"
        total = m.get("total_canvases") or 0
        current = m.get("downloaded_canvases") or 0

        if status in {"downloading", "pending"}:
            t_path = temp_dir / ms_id
            current = len(list(t_path.glob("pag_*.jpg"))) if t_path.exists() else 0
        elif current == 0 and m.get("local_path"):
            l_path = Path(m["local_path"]) / "scans"
            if l_path.exists():
                current = len(list(l_path.glob("pag_*.jpg")))

        prog_str = f"{current}/{total}"
        icon = _status_icon(status)
        print(f"{icon} {ms_id:<22} | {status:<12} | {prog_str:<12} | {m.get('library', 'Unknown')}")

    print("\n")


def _status_icon(status: str) -> str:
    if status == "complete":
        return "✅"
    if status == "downloading":
        return "⏳"
    if status == "error":
        return "❌"
    return "⚪"


def _handle_list() -> None:
    from universal_iiif_core.config_manager import get_config_manager
    from universal_iiif_core.services.storage.vault_manager import VaultManager

    vault = VaultManager()
    cm = get_config_manager()
    temp_dir = cm.get_temp_dir()
    mss = vault.get_all_manuscripts()
    _render_library_table(mss, temp_dir)


def _handle_info(ms_id: str) -> None:
    from universal_iiif_core.services.storage.vault_manager import VaultManager

    vault = VaultManager()
    m = vault.get_manuscript(ms_id)
    if not m:
        print(f"❌ Manuscript not found: {ms_id}")
        sys.exit(1)

    print(f"\n📖 Manuscript Details: {ms_id}\n" + "=" * 50)
    for k, v in m.items():
        print(f"{k:<20}: {v}")
    print("\n")


def _handle_delete(ms_id: str) -> None:
    from universal_iiif_core.services.storage.vault_manager import VaultManager

    vault = VaultManager()
    if vault.delete_manuscript(ms_id):
        print(f"🗑️  Deleted manuscript record: {ms_id}")
    else:
        print(f"⚠️  Manuscript not found: {ms_id}")


def _handle_set_status(ms_id: str, new_status: str) -> None:
    from universal_iiif_core.services.storage.vault_manager import VaultManager

    vault = VaultManager()
    if not vault.get_manuscript(ms_id):
        print(f"❌ Manuscript not found: {ms_id}")
        sys.exit(1)

    valid_statuses = ["pending", "downloading", "complete", "error"]
    if new_status not in valid_statuses:
        print(f"⚠️  Warning: '{new_status}' is not a standard status ({', '.join(valid_statuses)})")

    vault.update_status(ms_id, new_status)
    print(f"✅ Updated {ms_id} status to: {new_status}")


def _handle_db_commands(args: argparse.Namespace) -> bool:
    if args.list:
        _handle_list()
        return True
    if args.info:
        _handle_info(args.info)
        return True
    if args.delete:
        _handle_delete(args.delete)
        return True
    if getattr(args, "delete_job", None):
        _handle_delete_job(args.delete_job)
        return True
    if args.set_status:
        ms_id, new_status = args.set_status
        _handle_set_status(ms_id, new_status)
        return True
    return False


def _handle_delete_job(job_id: str) -> None:
    """Remove a download job record from the internal download_jobs table.

    This is useful during development to remove stray test jobs.
    """
    from universal_iiif_core.services.storage.vault_manager import VaultManager

    vm = VaultManager()
    try:
        conn = vm._get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM download_jobs WHERE job_id = ?", (job_id,))
        conn.commit()
        print(f"🗑️  Deleted download job: {job_id}")
    except Exception as e:
        print(f"⚠️  Failed to delete download job {job_id}: {e}")
    finally:
        from contextlib import suppress

        if "conn" in locals() and conn:
            with suppress(Exception):
                conn.close()


def _resolve_download_args(args: argparse.Namespace):
    if not args.url:
        url, out_name, ocr_model = wizard_mode()
        return url, out_name, 4, False, False, ocr_model, False
    return (
        args.url,
        args.output,
        args.workers,
        args.clean_cache,
        args.prefer_images,
        args.ocr,
        args.create_pdf,
    )


def _resolve_manifest(url: str):
    manifest_url, suggested_id, library = resolve_url(url)
    if manifest_url:
        return manifest_url, suggested_id, library

    if not url.startswith(("http://", "https://")):
        print(f"❌ Error: Invalid URL or ID '{url}'.")
        print("   Please provide a full URL (starting with http/https) or a supported Library ID.")
        print("   Supported IDs example: 'Vat.lat.3225' (Vaticana), 'btv1b...' (Gallica), or UUID (Oxford).")
        sys.exit(1)

    return url, None, "Unknown"


def main():
    """CLI entry point."""
    setup_logging()
    parser = _build_parser()
    args = parser.parse_args()

    if _handle_db_commands(args):
        sys.exit(0)

    url, out_name, workers, clean, prefer_images, ocr_model, create_pdf = _resolve_download_args(args)

    try:
        manifest_url, suggested_id, library = _resolve_manifest(url)
        print(f"✅ Target Manifest: {manifest_url}")
        print(f"🏛️  Library: {library}")
        if suggested_id:
            print(f"🆔 Suggested ID: {suggested_id}")

        from universal_iiif_core.config_manager import get_config_manager

        cm = get_config_manager()
        downloads_dir = cm.get_downloads_dir()

        downloader = IIIFDownloader(
            manifest_url=manifest_url,
            output_dir=downloads_dir,
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
