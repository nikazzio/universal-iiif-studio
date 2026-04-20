"""Resolver for Biblioteca Estense Digitale (Jarvis backend).

Estense Digital Library is the Modena Biblioteca Estense Universitaria IIIF
platform, served by the Jarvis backend at ``jarvis.edl.beniculturali.it``.
Unlike ICCU, it exposes full native IIIF Presentation (v2 and v3) with a
level-2 Image API (tile/zoom/rescale).

Accepted inputs:
  - Manifest v2: ``https://jarvis.edl.beniculturali.it/meta/iiif/{uuid}/manifest``
  - Manifest v3: ``https://jarvis.edl.beniculturali.it/meta/iiif/v3/{uuid}/manifest``
  - Mirador viewer wrapper URL: ``https://jarvis.edl.beniculturali.it/images/viewers/mirador/?manifest=...``
  - Bare UUID (8-4-4-4-12 hex) — resolved to the v2 manifest

``/beu/{public_id}`` URLs from ``edl.beniculturali.it`` and ``edl.cultura.gov.it``
are not resolvable without a live API call: the Scriptoria UI surfaces them
by redirecting the user through the search flow, which returns the UUID
directly.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlparse

from .base import BaseResolver

JARVIS_HOST = "jarvis.edl.beniculturali.it"
JARVIS_BASE = f"https://{JARVIS_HOST}"

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_MANIFEST_PATH_RE = re.compile(
    r"/meta/iiif/(?:v3/)?(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/manifest",
    re.IGNORECASE,
)


def build_manifest_url(uuid: str, *, v3: bool = False) -> str:
    """Build the Jarvis manifest URL for a given item UUID."""
    prefix = "v3/" if v3 else ""
    return f"{JARVIS_BASE}/meta/iiif/{prefix}{uuid}/manifest"


def build_viewer_url(uuid: str, *, v3: bool = True) -> str:
    """Build the Mirador viewer URL (v3 manifest by default)."""
    manifest = build_manifest_url(uuid, v3=v3)
    return f"{JARVIS_BASE}/images/viewers/mirador/?manifest={manifest}"


def build_cultural_item_url(uuid: str) -> str:
    """Build the HATEOAS cultural item URL used by the search adapter."""
    return f"{JARVIS_BASE}/meta/culturalItems/search/findByUuid?uuid={uuid}"


def extract_uuid(url_or_id: str) -> str | None:
    """Return the item UUID extracted from any accepted Estense input."""
    text = (url_or_id or "").strip()
    if not text:
        return None

    if _UUID_RE.match(text):
        return text.lower()

    parsed = urlparse(text)
    if JARVIS_HOST in (parsed.netloc or ""):
        m = _MANIFEST_PATH_RE.search(parsed.path)
        if m:
            return m.group("uuid").lower()
        nested = parse_qs(parsed.query).get("manifest") or []
        if nested:
            nested_url = unquote(nested[0])
            inner = urlparse(nested_url)
            m = _MANIFEST_PATH_RE.search(inner.path)
            if m:
                return m.group("uuid").lower()
    return None


class EstenseResolver(BaseResolver):
    """Resolver for Biblioteca Estense Digitale via the Jarvis backend."""

    def can_resolve(self, url_or_id: str) -> bool:
        """Return True when the input carries an Estense UUID or manifest URL."""
        return extract_uuid(url_or_id) is not None

    def get_manifest_url(self, url_or_id: str) -> tuple[str | None, str | None]:
        """Return (manifest_url_v2, uuid) when the input is recognised."""
        uuid = extract_uuid(url_or_id)
        if not uuid:
            return None, None
        return build_manifest_url(uuid), uuid
