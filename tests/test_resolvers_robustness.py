"""
Tests for resolver robustness: trailing slashes, IDs from wrong libraries, etc.
"""

import sys
from pathlib import Path

from iiif_downloader.resolvers.discovery import resolve_shelfmark

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_oxford_robustness():
    print("\n--- Testing Oxford Robustness ---")
    # Base UUID
    uuid = "cb1df5f1-7435-468b-8860-d56db988b929"

    urls = [
        uuid,
        f"https://digital.bodleian.ox.ac.uk/objects/{uuid}",
        f"https://digital.bodleian.ox.ac.uk/objects/{uuid}/",
        f"{uuid}.json",
    ]

    for u in urls:
        m_url, _d_id = resolve_shelfmark("Bodleian (Oxford)", u)
        print(f"Input: {u}")
        print(f"  Result ID: {_d_id}")
        if m_url and uuid in m_url:
            print("  ✅ Success")
        else:
            print(f"  ❌ Failed: {m_url}")


def test_vatican_cross_protection():
    print("\n--- Testing Vatican Cross-Protection ---")
    uuid = "cb1df5f1-7435-468b-8860-d56db988b929"

    m_url, d_id = resolve_shelfmark("Vaticana (BAV)", uuid)
    print(f"Input UUID to Vatican: {uuid}")
    if m_url is None and "Oxford" in d_id:
        print(f"  ✅ Protected: {d_id}")
    else:
        print(f"  ❌ Failed to protect: {m_url} (ID: {d_id})")


def test_gallica_bpt():
    print("\n--- Testing Gallica BPT ---")
    bpt_id = "bpt6k9761787t"
    m_url, _d_id = resolve_shelfmark("Gallica (BnF)", bpt_id)
    print(f"Input: {bpt_id}")
    if m_url and bpt_id in m_url:
        print("  ✅ Success")
    else:
        print(f"  ❌ Failed: {m_url}")


if __name__ == "__main__":
    test_oxford_robustness()
    test_vatican_cross_protection()
    test_gallica_bpt()
