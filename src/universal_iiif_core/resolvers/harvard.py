from __future__ import annotations

import re

from ..exceptions import ResolverError
from .base import BaseResolver

_DRS_RE = re.compile(r"drs:(?P<id>\d{6,12})", flags=re.IGNORECASE)
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
        return "harvard.edu" in lowered or bool(_DRS_RE.search(text))

    def get_manifest_url(self, url_or_id: str) -> tuple[str | None, str | None]:
        """Build the canonical Harvard manifest URL from an extracted DRS ID."""
        text = (url_or_id or "").strip()
        if not text:
            return None, None

        drs_id = self._extract_drs_id(text)
        if not drs_id:
            raise ResolverError("Cannot extract Harvard DRS ID from input.")

        return f"{self.manifest_root}/drs:{drs_id}", drs_id

    @staticmethod
    def _extract_drs_id(value: str) -> str | None:
        if match := _DRS_RE.search(value):
            return match.group("id")
        if "harvard.edu" in value.lower() and (match := _NUMERIC_RE.search(value)):
            return match.group("id")
        return None
