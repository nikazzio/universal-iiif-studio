import re

from ..exceptions import ResolverError
from ..logger import get_logger
from .base import BaseResolver

logger = get_logger(__name__)


_SHELF_RE = re.compile(
    r"^(?:MSS[_\s\-]*)?"
    r"(?P<coll>vat|urb|pal|reg|barb|ott|borg|arch|cap)"
    r"[\s\._\-:]*?(?P<series>lat|gr)?[\s\._\-:]*?(?P<number>\d+)$",
    flags=re.I,
)


def normalize_shelfmark(raw: str) -> str:
    """Normalize a Vatican shelfmark into canonical form.

    Examples accepted:
      - "Urb. lat. 123"
      - "Urb lat 123"
      - "urb-lat-123"
      - "Vatlat123"

    Returns canonical id like: "MSS_Urb.lat.123"

    Raises ResolverError on invalid input.
    """
    if not raw or not raw.strip():
        raise ResolverError("Empty shelfmark provided for Vaticana")

    s = raw.strip()
    # Remove leading MSS_ if provided (allow flexible input)
    s = re.sub(r"^MSS[_\s\-]*", "", s, flags=re.I)
    # Collapse multiple whitespace
    s = re.sub(r"\s+", " ", s)
    # Also remove dots that are not between letters/nums (we tolerate many variants)
    s = s.replace(".", " ")
    s = s.replace("/", " ")
    s = s.strip()

    m = _SHELF_RE.search(s)
    if not m:
        raise ResolverError(f"Cannot normalize Vatican shelfmark: '{raw}'")

    coll = m.group("coll").capitalize()
    series = m.group("series")
    number = m.group("number")

    normalized = f"MSS_{coll}.{series.lower()}.{number}" if series else f"MSS_{coll}.{number}"

    logger.debug("Normalized VAT shelfmark %r -> %r", raw, normalized)
    return normalized


class VaticanResolver(BaseResolver):
    """Resolver for Vatican Library IIIF manifests."""

    def can_resolve(self, url_or_id: str) -> bool:  # pragma: no cover - trivial branching
        """Return True when the input looks like a Vatican URL or shelfmark."""
        s = (url_or_id or "").strip()
        if "digi.vatlib.it" in s:
            return True
        if s.upper().startswith("MSS_"):
            return True
        return bool(_SHELF_RE.search(s))

    def get_manifest_url(self, url_or_id: str) -> tuple[str | None, str | None]:
        """Build Vatican manifest URL and normalized document id from input."""
        s = (url_or_id or "").strip()

        if not s:
            return None, None

        # If user pasted a digi.vatlib.it URL, extract the manuscript id via regex
        if "digi.vatlib.it" in s:
            m = re.search(r"digi\.vatlib\.it/iiif/(?P<id>[^/]+)/manifest\.json", s)
            if m:
                ms_id = m.group("id")
                return s, ms_id

            # fallback: last path segment
            ms_id = s.strip("/").split("/")[-1]
            return f"https://digi.vatlib.it/iiif/{ms_id}/manifest.json", ms_id

        # Otherwise normalize shelfmark and build manifest URL
        normalized = normalize_shelfmark(s)
        manifest_url = f"https://digi.vatlib.it/iiif/{normalized}/manifest.json"
        return manifest_url, normalized
