from __future__ import annotations

import re
from urllib.parse import urlparse

from .base import BaseResolver

_DIRECT_ID_RE = re.compile(r"(?P<id>(?:cpg|cpl)\d{2,})$", flags=re.IGNORECASE)
_COD_PAL_GERM_RE = re.compile(r"\bcod\.?\s*pal\.?\s*germ\.?\s*(?P<num>\d{1,5})\b", flags=re.IGNORECASE)


class HeidelbergResolver(BaseResolver):
    """Resolver for Universitaetsbibliothek Heidelberg manifests."""

    manifest_root = "https://digi.ub.uni-heidelberg.de/diglit/iiif"

    def can_resolve(self, url_or_id: str) -> bool:
        """Return True for supported Heidelberg URLs or catalog IDs."""
        text = (url_or_id or "").strip()
        if not text:
            return False
        if "digi.ub.uni-heidelberg.de" in text.lower():
            return True
        return bool(self._extract_id(text))

    def get_manifest_url(self, url_or_id: str) -> tuple[str | None, str | None]:
        """Build the canonical Heidelberg manifest URL."""
        text = (url_or_id or "").strip()
        if not text:
            return None, None

        doc_id = self._extract_id(text)
        if not doc_id:
            return None, None

        return f"{self.manifest_root}/{doc_id}/manifest.json", doc_id

    @staticmethod
    def _extract_id(value: str) -> str | None:
        clean = value.strip()
        if match := _DIRECT_ID_RE.fullmatch(clean):
            return match.group(1).lower()
        if cod_match := _COD_PAL_GERM_RE.search(clean):
            return f"cpg{int(cod_match.group('num'))}"
        parsed = urlparse(clean)
        hostname = (parsed.netloc or "").lower()
        if hostname != "digi.ub.uni-heidelberg.de":
            return None
        if match := _DIRECT_ID_RE.search(parsed.path or ""):
            return match.group(1).lower()
        return None
