from __future__ import annotations

import re

from .base import BaseResolver

_DRS_RE = re.compile(r"drs:(?P<id>\d{6,12})", flags=re.IGNORECASE)
_IDS_RE = re.compile(r"ids:(?P<id>\d{6,12})", flags=re.IGNORECASE)
_NUMERIC_RE = re.compile(r"\b(?P<id>\d{6,12})\b")


class HarvardResolver(BaseResolver):
    """Resolver for Harvard IIIF manifests."""

    manifest_root = "https://iiif.lib.harvard.edu/manifests"

    def can_resolve(self, url_or_id: str) -> bool:
        """Return True for supported Harvard IIIF or catalog URLs."""
        text = (url_or_id or "").strip()
        if not text:
            return False
        lowered = text.lower()
        return "harvard.edu" in lowered or bool(_DRS_RE.search(text)) or bool(_IDS_RE.search(text))

    def get_manifest_url(self, url_or_id: str) -> tuple[str | None, str | None]:
        """Build the canonical Harvard manifest URL from a DRS or IDS identifier."""
        text = (url_or_id or "").strip()
        if not text:
            return None, None

        canonical_id = self._extract_canonical_id(text)
        if not canonical_id:
            return None, None

        return f"{self.manifest_root}/{canonical_id}", canonical_id

    @staticmethod
    def _extract_canonical_id(value: str) -> str | None:
        """Return the full canonical Harvard ID token (drs:NNNNN or ids:NNNNN).

        Preserves the identifier type so that drs: and ids: manifests are not
        conflated and library entries stay deduplicated across search and direct
        resolution paths.
        """
        if match := _DRS_RE.search(value):
            return f"drs:{match.group('id')}"
        if match := _IDS_RE.search(value):
            return f"ids:{match.group('id')}"
        if "harvard.edu" in value.lower() and (match := _NUMERIC_RE.search(value)):
            return f"drs:{match.group('id')}"
        return None
