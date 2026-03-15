from __future__ import annotations

import re
from urllib.parse import urlparse

from .base import BaseResolver

_DETAILS_RE = re.compile(r"/details/(?P<identifier>[^/?#]+)", flags=re.IGNORECASE)
_HELPER_RE = re.compile(r"/iiif/helper/(?P<identifier>[^/?#]+)", flags=re.IGNORECASE)
_MANIFEST_RE = re.compile(r"/iiif/(?P<identifier>[^/?#]+)/manifest\.json$", flags=re.IGNORECASE)
_BARE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9._:-]*[0-9_-][A-Za-z0-9._:-]*$")


class ArchiveOrgResolver(BaseResolver):
    """Resolver for Internet Archive IIIF manifests."""

    manifest_root = "https://iiif.archive.org/iiif"

    def can_resolve(self, url_or_id: str) -> bool:
        """Return True for supported Archive.org item or IIIF URLs."""
        text = (url_or_id or "").strip()
        if not text:
            return False
        if self._looks_like_bare_identifier(text):
            return True
        parsed = urlparse(text)
        hostname = (parsed.netloc or "").lower()
        return hostname == "archive.org" or hostname.endswith(".archive.org")

    def get_manifest_url(self, url_or_id: str) -> tuple[str | None, str | None]:
        """Build the canonical Archive.org IIIF manifest URL."""
        text = (url_or_id or "").strip()
        if not text:
            return None, None

        identifier = self._extract_identifier(text)
        if not identifier:
            return None, None

        return f"{self.manifest_root}/{identifier}/manifest.json", identifier

    @staticmethod
    def _extract_identifier(value: str) -> str | None:
        direct = value.strip().strip("/")
        if (
            direct
            and "://" not in direct
            and "/" not in direct
            and " " not in direct
            and ArchiveOrgResolver._looks_like_bare_identifier(direct)
        ):
            return direct

        parsed = urlparse(value)
        path = parsed.path or ""
        if manifest_match := _MANIFEST_RE.search(path):
            return manifest_match.group("identifier")
        if details_match := _DETAILS_RE.search(path):
            return details_match.group("identifier")
        if helper_match := _HELPER_RE.search(path):
            return helper_match.group("identifier")
        return None

    @staticmethod
    def _looks_like_bare_identifier(value: str) -> bool:
        """Return True for IA-style bare identifiers, not generic free-text terms."""
        token = (value or "").strip().strip("/")
        if not token or "://" in token or "/" in token or " " in token:
            return False
        return bool(_BARE_IDENTIFIER_RE.fullmatch(token))
