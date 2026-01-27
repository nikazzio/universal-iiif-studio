import re

from ..logger import get_logger
from .base import BaseResolver

logger = get_logger(__name__)

class VaticanResolver(BaseResolver):
    """Resolver for Vatican Library IIIF manifests."""

    def can_resolve(self, url_or_id):
        """Determine if the input can be resolved as a Vatican Library manuscript."""
        s = url_or_id.strip()

        if "digi.vatlib.it" in s:
            return True

        if s.startswith("MSS_"):
            return True

        # Standard keys for Vatican shelfmarks
        keywords = ["Vat", "Urb", "Pal", "Reg", "Barb", "Ott", "Borg", "Arch", "Cap"]
        has_number = bool(re.search(r"\d", s))

        if not has_number:
            return False

        return any(re.search(rf"\b{k}", s, re.IGNORECASE) for k in keywords)

    def get_manifest_url(self, url_or_id):
        """Return (manifest_url, id) for a Vatican shelfmark or URL.
        
        Explicitly supports the 'Vaticana' library standardization.
        """
        s = url_or_id.strip()

        if "digi.vatlib.it" in s:
            if s.endswith("manifest.json"):
                parts = s.split("/")
                if len(parts) >= 2:
                    return s, parts[-2]
                return s, "unknown_id"

            ms_id = s.strip("/").split("/")[-1]
            return f"https://digi.vatlib.it/iiif/{ms_id}/manifest.json", ms_id

        # Standardization logic
        clean_s = s.replace(" ", "")

        # Mapping to proper BAV prefixes
        clean_s = (
            clean_s.replace("Lat.", "lat.")
                   .replace("Gr.", "gr.")
                   .replace("Vat.", "vatic.")
                   .replace("Pal.", "pal.")
        )

        clean_id = clean_s if clean_s.startswith("MSS_") else f"MSS_{clean_s}"
        manifest_url = f"https://digi.vatlib.it/iiif/{clean_id}/manifest.json"

        logger.debug(f"Resolved 'Vaticana' shelfmark '{url_or_id}' -> '{clean_id}'")
        return manifest_url, clean_id
