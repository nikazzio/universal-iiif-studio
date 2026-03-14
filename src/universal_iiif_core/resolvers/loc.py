from __future__ import annotations

import re
from urllib.parse import urlparse

from .base import BaseResolver

_PATH_RE = re.compile(r"/(?:item|resource)/(?P<id>[^/?#]+)", flags=re.IGNORECASE)


class LOCResolver(BaseResolver):
    """Resolver for Library of Congress manifests."""

    manifest_root = "https://www.loc.gov/item"

    def can_resolve(self, url_or_id: str) -> bool:
        """Return True for supported Library of Congress item or resource URLs."""
        text = (url_or_id or "").strip()
        if not text:
            return False
        parsed = urlparse(text)
        hostname = (parsed.netloc or "").lower()
        is_loc_host = hostname == "loc.gov" or hostname.endswith(".loc.gov")
        return is_loc_host and bool(_PATH_RE.search(parsed.path or ""))

    def get_manifest_url(self, url_or_id: str) -> tuple[str | None, str | None]:
        """Build the canonical Library of Congress manifest URL."""
        text = (url_or_id or "").strip()
        if not text:
            return None, None

        item_id = self._extract_id(text)
        if not item_id:
            return None, None

        return f"{self.manifest_root}/{item_id}/manifest.json", item_id

    @staticmethod
    def _extract_id(value: str) -> str | None:
        parsed = urlparse(value)
        target = parsed.path or value
        if match := _PATH_RE.search(target):
            item_id = match.group("id")
        else:
            return None

        return re.sub(r":sp\d+$", "", item_id, flags=re.IGNORECASE)
