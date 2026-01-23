import re

from ..logger import get_logger
from .base import BaseResolver

logger = get_logger(__name__)


class VaticanResolver(BaseResolver):
    """Resolver for Vatican Library IIIF manifests."""

    def can_resolve(self, url_or_id):
        """Determine if the input can be resolved as a Vatican Library manuscript."""
        s = url_or_id.strip()

        # 1. Standard URL check
        if "digi.vatlib.it" in s:
            return True

        # 2. Heuristic for shelfmarks
        # If it starts with MSS_, it's likely a cleaned Vatican ID
        if s.startswith("MSS_"):
            return True

        # Common Vatican fonds keys
        # We check for these specifically to correctly identify short inputs
        keywords = ["Vat", "Urb", "Pal", "Reg", "Barb", "Ott", "Borg", "Arch", "Cap"]

        # Check if any keyword is present
        # We need to be slightly stricter to avoid resolving random text
        # e.g. check for presence of digits (all shelfmarks have numbers)
        has_number = bool(re.search(r"\d", s))

        if not has_number:
            return False

        # If any keyword matches, consider it a Vatican shelfmark
        return any(re.search(rf"\b{k}", s, re.IGNORECASE) for k in keywords)

    def get_manifest_url(self, url_or_id):
        """Return (manifest_url, id) for a Vatican shelfmark or URL.

        Accepts full digi.vatlib.it manifest URLs, viewer URLs ending in an
        identifier, or short shelfmark strings which will be normalized to
        the `MSS_...` form used by the Vatican IIIF endpoint.
        """
        s = url_or_id.strip()

        # If it's a full URL
        if "digi.vatlib.it" in s:
            # Check if it is already a manifest URL
            if s.endswith("manifest.json"):
                parts = s.split("/")
                if len(parts) >= 2:
                    return s, parts[-2]
                return s, "unknown_id"

            # Assuming it is a viewer URL or similar ending in ID
            ms_id = s.strip("/").split("/")[-1]
            return f"https://digi.vatlib.it/iiif/{ms_id}/manifest.json", ms_id

        # Logic adapted from resolvers/discovery.py to ensure consistency with UI

        # 1. Remove all spaces
        clean_s = s.replace(" ", "")

        # 2. Case normalization (BAV often uses 'lat.' instead of 'Lat.')
        # We mimic the UI logic here for consistency
        clean_s = (
            clean_s.replace("Lat.", "lat.").replace("Gr.", "gr.").replace("Vat.", "vatic.").replace("Pal.", "pal.")
        )

        clean_id = clean_s if clean_s.startswith("MSS_") else f"MSS_{clean_s}"

        manifest_url = f"https://digi.vatlib.it/iiif/{clean_id}/manifest.json"

        logger.debug(f"Resolved Vatican shelfmark '{url_or_id}' to '{manifest_url}'")
        return manifest_url, clean_id
