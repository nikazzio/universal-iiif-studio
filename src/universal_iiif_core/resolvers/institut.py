from __future__ import annotations

import re
from urllib.parse import urlparse

from .base import BaseResolver

_NUMERIC_ID_RE = re.compile(r"^\d{3,}$")
_VIEWER_RE = re.compile(r"/viewer/(?P<id>\d+)", flags=re.IGNORECASE)
_MANIFEST_RE = re.compile(r"/iiif/(?P<id>\d+)/manifest/?$", flags=re.IGNORECASE)
_RECORD_RE = re.compile(r"/records/item/(?P<id>\d+)(?:[-/].*)?$", flags=re.IGNORECASE)


class InstitutResolver(BaseResolver):
    """Resolver for Institut de France (bibnum.institutdefrance.fr)."""

    base_url = "https://bibnum.institutdefrance.fr"

    def can_resolve(self, url_or_id: str) -> bool:
        """Return True when the input is a Bibnum URL or a numeric document ID."""
        text = (url_or_id or "").strip()
        if not text:
            return False
        if "bibnum.institutdefrance.fr" in text.lower():
            return True
        return bool(_NUMERIC_ID_RE.fullmatch(text))

    def get_manifest_url(self, url_or_id: str) -> tuple[str | None, str | None]:
        """Return canonical IIIF manifest URL and extracted Bibnum numeric id."""
        text = (url_or_id or "").strip()
        if not text:
            return None, None

        if _NUMERIC_ID_RE.fullmatch(text):
            return self._build_manifest_url(text), text

        doc_id = self._extract_doc_id(text)
        if not doc_id:
            return None, None

        return self._build_manifest_url(doc_id), doc_id

    @classmethod
    def _build_manifest_url(cls, doc_id: str) -> str:
        return f"{cls.base_url}/iiif/{doc_id}/manifest"

    @staticmethod
    def _extract_doc_id(value: str) -> str | None:
        parsed = urlparse(value)
        path = parsed.path or value
        search_space = path if path else value

        for pattern in (_MANIFEST_RE, _VIEWER_RE, _RECORD_RE):
            if match := pattern.search(search_space):
                return match.group("id")

        return None
