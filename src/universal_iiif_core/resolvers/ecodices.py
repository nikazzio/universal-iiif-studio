from __future__ import annotations

import re
from urllib.parse import urlparse

from .base import BaseResolver

_PATH_RE = re.compile(r"/(?:(?:en|de|fr|it)/)?(?P<library>[a-z0-9]+)/(?P<shelfmark>[a-z0-9._-]+)", flags=re.IGNORECASE)
_MANIFEST_RE = re.compile(
    r"/metadata/iiif/(?P<compound>[a-z0-9._-]+-[a-z0-9._-]+)/manifest\.json$",
    flags=re.IGNORECASE,
)
_DIRECT_COMPOUND_ID_RE = re.compile(
    r"^(?:[a-z0-9._-]+-)?[a-z0-9._-]+-\d{3,}$",
    flags=re.IGNORECASE,
)


class EcodicesResolver(BaseResolver):
    """Resolver for e-codices manifests."""

    manifest_root = "https://www.e-codices.unifr.ch/metadata/iiif"

    def can_resolve(self, url_or_id: str) -> bool:
        """Return True for supported e-codices URLs or compound IDs."""
        text = (url_or_id or "").strip()
        if not text:
            return False
        lowered = text.lower()
        if "e-codices.unifr.ch" in lowered or "e-codices.ch" in lowered:
            return True
        return bool(_DIRECT_COMPOUND_ID_RE.fullmatch(text))

    def get_manifest_url(self, url_or_id: str) -> tuple[str | None, str | None]:
        """Build the canonical e-codices manifest URL."""
        text = (url_or_id or "").strip()
        if not text:
            return None, None

        compound_id = self._extract_compound_id(text)
        if not compound_id:
            return None, None

        return f"{self.manifest_root}/{compound_id}/manifest.json", compound_id

    @staticmethod
    def _extract_compound_id(value: str) -> str | None:
        direct = _DIRECT_COMPOUND_ID_RE.fullmatch(value)
        if direct:
            return direct.group(0).lower()

        parsed = urlparse(value)
        path = parsed.path or ""
        if manifest_match := _MANIFEST_RE.search(path):
            return manifest_match.group("compound").lower()

        if path_match := _PATH_RE.search(path):
            library = path_match.group("library").lower()
            shelfmark = path_match.group("shelfmark").lower()
            return f"{library}-{shelfmark}"

        return None
