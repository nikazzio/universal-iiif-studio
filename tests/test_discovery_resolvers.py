"""
Test script for discovery resolvers (Gallica, Oxford, Vaticana).

Tests both the resolve_shelfmark() function and the search_*() APIs.
Run from project root: python -m tests.test_discovery_resolvers
"""
import sys
from pathlib import Path

from iiif_downloader.resolvers.discovery import (
    resolve_shelfmark,
    search_gallica,
    search_oxford,
)

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_gallica():
    print("\n--- Testing Gallica ---")
    print("Test resolve_shelfmark (ark):", resolve_shelfmark("Gallica (BnF)", "ark:/12148/btv1b10033406t"))
    print("Test resolve_shelfmark (short):", resolve_shelfmark("Gallica (BnF)", "btv1b10033406t"))

    results = search_gallica("Dante")
    print(f"Search results found: {len(results)}")
    if results:
        print("First result:", results[0])
    print("--- End Gallica ---\n")


def test_oxford():
    print("\n--- Testing Oxford ---")
    print("Test resolve_shelfmark (uuid):", resolve_shelfmark(
        "Bodleian (Oxford)", "080f88f5-7586-4b8a-8064-63ab3495393c"))

    results = search_oxford("Dante")
    print(f"Search results found: {len(results)}")
    if results:
        print("First result:", results[0])
    print("--- End Oxford ---\n")


if __name__ == "__main__":
    try:
        test_gallica()
    except (OSError, ValueError, RuntimeError) as e:
        print(f"Gallica failed: {e}")
        import traceback
        traceback.print_exc()

    try:
        test_oxford()
    except (OSError, ValueError, RuntimeError) as e:
        print(f"Oxford failed: {e}")
        import traceback
        traceback.print_exc()
