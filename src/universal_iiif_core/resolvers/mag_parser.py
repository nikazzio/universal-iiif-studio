"""Parser for Internet Culturale MAG/XML API.

Converts the ICCU MAG XML format (from /jmms/magparser) into a IIIF v2-compatible
manifest dict so the existing downloader pipeline can handle it without changes.

MAG = Metadati Amministrativi e Gestionali (ICCU standard for Italian digital libraries).

Image URL pattern (verified live):
  GET /jmms/thumbnail?type=normal&id={oai_id}&teca={teca}&page={1-based-n}
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import defusedxml.ElementTree as SafeET
import requests

from ..logger import get_logger

logger = get_logger(__name__)

_IC_BASE = "https://www.internetculturale.it"
_MAGPARSER_PATH = "/jmms/magparser"
_THUMBNAIL_PATH = "/jmms/thumbnail"

# Max pages to request in a single call — covers virtually all manuscripts.
_MAX_PAGES_PER_CALL = 2000

# Namespace used in MAG XML
_MAG_NS = {"mag": "urn:meta:internetculturale"}

# Pattern: "Biblioteca XYZ - Città - IT-XX0000"
_LOCALIZATION_RE = re.compile(r"^(?P<library>.+?)\s+-\s+(?P<city>[^-]+?)\s+-\s+(?P<sbn>IT-[A-Z]{2}\d+)\s*$")

# Pattern for BML-style shelfmark: IT:FI0100_Plutei_40.26_0004
_BML_IDENT_RE = re.compile(r"^[A-Z]{2}:[A-Z]{2}\d+_(?P<shelf>.+?)(?:_\d+)?$")

# Pattern for SBN-prefixed shelfmark: VE0049_It_09_0127_06278
_SBN_SHELF_RE = re.compile(r"^[A-Z]{2}\d{4}_(?P<shelf>.+)$")


@dataclass
class IccuMetadata:
    """Parsed bibliographic metadata from a MAG XML document."""

    title: str = ""
    authors: list[str] = field(default_factory=list)
    date: str = ""
    library: str = ""
    city: str = ""
    sbn_code: str = ""
    shelfmark: str = ""
    oai_id: str = ""
    teca: str = ""
    raw_identificativo: list[str] = field(default_factory=list)
    page_count: int = 0

    @property
    def library_label(self) -> str:
        """Human-readable library + city label."""
        if self.city and self.city not in self.library:
            return f"{self.library} ({self.city})"
        return self.library

    @property
    def full_reference(self) -> str:
        """Full manuscript reference for display."""
        parts = [self.library_label]
        if self.shelfmark:
            parts.append(self.shelfmark)
        return ", ".join(parts)


def build_magparser_url(oai_id: str, teca: str, max_pages: int = _MAX_PAGES_PER_CALL) -> str:
    """Build the magparser API URL for a given OAI ID and teca identifier."""
    params = urlencode(
        {
            "id": oai_id,
            "teca": teca,
            "mode": "all",
            "offset": "0",
            "pag": str(max_pages),
        }
    )
    return f"{_IC_BASE}{_MAGPARSER_PATH}?{params}"


def build_thumbnail_url(oai_id: str, teca: str, page_1based: int, quality: str = "normal") -> str:
    """Build the image URL for a specific page via the IC thumbnail endpoint.

    Args:
        oai_id: OAI identifier of the document.
        teca: Teca identifier (provider ID within IC).
        page_1based: Page number, 1-based (page 1 = first image).
        quality: "normal" (full-res), "preview" (medium), "web" (small).
    """
    params = urlencode(
        {
            "type": quality,
            "id": oai_id,
            "teca": teca,
            "page": str(page_1based),
        }
    )
    return f"{_IC_BASE}{_THUMBNAIL_PATH}?{params}"


def extract_oai_and_teca_from_url(url: str) -> tuple[str | None, str | None]:
    """Extract OAI ID and teca from a magparser or IC viewer URL.

    Handles:
      - magparser URLs: /jmms/magparser?id={oai}&teca={teca}
      - IC viewer URLs: /it/16/search/viewresource?id={oai}&teca={teca}
      - Raw OAI IDs passed directly
    """
    parsed = urlparse(url)
    if not parsed.scheme and "?" not in url:
        # Raw OAI ID — no teca extractable
        return url, None

    qs = parse_qs(parsed.query)
    oai_id = (qs.get("id") or [None])[0]
    teca = (qs.get("teca") or [None])[0]
    if not oai_id:
        teca_val = (qs.get("descSourceLevel2") or [None])[0]
        if teca_val:
            teca = teca_val
    return oai_id, teca


def _parse_localization(raw: str) -> tuple[str, str, str]:
    """Parse a localization string into (library, city, sbn_code).

    Example: "Biblioteca Medicea Laurenziana - Firenze - IT-FI0100"
    Returns: ("Biblioteca Medicea Laurenziana", "Firenze", "IT-FI0100")
    """
    m = _LOCALIZATION_RE.match(raw.strip())
    if m:
        return m.group("library").strip(), m.group("city").strip(), m.group("sbn").strip()
    # Fallback: split on " - "
    parts = [p.strip() for p in raw.split(" - ")]
    library = parts[0] if parts else raw
    city = parts[1] if len(parts) > 1 else ""
    sbn = parts[2] if len(parts) > 2 else ""
    return library, city, sbn


def _extract_shelfmark_from_title(title: str, library: str) -> str | None:
    """Extract shelfmark from titles like 'Venezia, Biblioteca ..., It. IX 127 (=6278)'."""
    if not title or not library:
        return None
    # Check if title contains the library name
    lib_short = library.split()[0] if library else ""
    if lib_short and lib_short.lower() in title.lower():
        # Find the last comma — everything after is the shelfmark
        parts = title.rsplit(",", 1)
        if len(parts) == 2:
            candidate = parts[1].strip()
            # Reject if too long (likely not a shelfmark)
            if 2 <= len(candidate) <= 80:
                return candidate
    return None


def _extract_shelfmark_from_identificativo(identificativi: list[str], sbn_code: str) -> str | None:
    """Try to extract a human-readable shelfmark from raw ICCU identifiers.

    Handles patterns like:
    - "IT:FI0100_Plutei_40.26_0004" → "Plutei 40.26"
    - "VE0049_It_09_0127_06278" → raw (complex decode needed)
    - "CNMD0000299115 VE0049_It_09_0127_06278 ARM0000580" → try the SBN-prefixed part
    """
    sbn_short = sbn_code.replace("IT-", "") if sbn_code else ""

    for raw in identificativi:
        # Multi-token: split and try each
        tokens = raw.split() if " " in raw else [raw]
        for token in tokens:
            # BML-style: IT:FI0100_Plutei_40.26_0004
            m = _BML_IDENT_RE.match(token)
            if m:
                shelf = m.group("shelf").replace("_", " ")
                return shelf

            # SBN-prefixed: VE0049_It_09_0127_06278 — only if matches our institution
            if sbn_short and token.startswith(sbn_short + "_"):
                m2 = _SBN_SHELF_RE.match(token)
                if m2:
                    return m2.group("shelf").replace("_", " ")

    return None


def _apply_info_field(meta: IccuMetadata, key: str, values: list[str]) -> None:
    """Apply a single MAG <info> key/values pair to a metadata object."""
    if key == "Titolo":
        meta.title = values[0]
    elif key == "Autore":
        meta.authors = values
    elif key == "Data di pubblicazione":
        meta.date = values[0]
    elif key == "Localizzazione":
        meta.library, meta.city, meta.sbn_code = _parse_localization(values[0])
    elif key == "Identificativo":
        meta.raw_identificativo = values


def _parse_bibinfo(bibinfo: ET.Element) -> IccuMetadata:
    """Extract metadata fields from a MAG <bibinfo> element."""
    meta = IccuMetadata()

    # OAI ID and teca
    tecaid_el = bibinfo.find("tecaid")
    if tecaid_el is not None and tecaid_el.text:
        meta.oai_id = tecaid_el.text.strip()

    provider_el = bibinfo.find("providerid")
    if provider_el is not None and provider_el.text:
        meta.teca = provider_el.text.strip()

    for info in bibinfo.findall("infos/info"):
        key = (info.get("key") or "").strip()
        values = [v.text.strip() for v in info.findall("value") if v.text]
        if values:
            _apply_info_field(meta, key, values)

    shelfmark = _extract_shelfmark_from_title(meta.title, meta.library)
    if not shelfmark:
        shelfmark = _extract_shelfmark_from_identificativo(meta.raw_identificativo, meta.sbn_code)
    meta.shelfmark = shelfmark or ""

    return meta


def _build_iiif_v2_manifest(meta: IccuMetadata, pages: list[dict[str, Any]]) -> dict[str, Any]:
    """Assemble a IIIF Presentation v2 manifest dict from ICCU metadata and pages."""
    manifest_id = build_magparser_url(meta.oai_id, meta.teca)

    iiif_metadata = [
        {"label": "Titolo", "value": meta.title},
        {"label": "Biblioteca", "value": meta.library},
        {"label": "Città", "value": meta.city},
        {"label": "Codice SBN", "value": meta.sbn_code},
        {"label": "Segnatura", "value": meta.shelfmark},
        {"label": "Data", "value": meta.date},
        {"label": "OAI ID", "value": meta.oai_id},
        {"label": "Provider ICCU", "value": meta.teca},
    ]
    if meta.authors:
        iiif_metadata.append({"label": "Autore", "value": "; ".join(meta.authors)})

    canvases = []
    for page in pages:
        idx = page["idx"]
        label = page.get("name") or f"Pagina {idx + 1}"
        w = page.get("w", 1000)
        h = page.get("h", 1000)
        image_url = build_thumbnail_url(meta.oai_id, meta.teca, idx + 1)
        canvas_id = f"{manifest_id}/canvas/{idx}"

        canvases.append(
            {
                "@id": canvas_id,
                "@type": "sc:Canvas",
                "label": label,
                "width": w,
                "height": h,
                "images": [
                    {
                        "@type": "oa:Annotation",
                        "motivation": "sc:painting",
                        "resource": {
                            "@id": image_url,
                            "@type": "dctypes:Image",
                            "format": "image/jpeg",
                            "width": w,
                            "height": h,
                        },
                        "on": canvas_id,
                    }
                ],
            }
        )

    return {
        "@context": "http://iiif.io/api/presentation/2/context.json",
        "@type": "sc:Manifest",
        "@id": manifest_id,
        "label": meta.title or meta.full_reference or "Documento ICCU",
        "attribution": f"Internet Culturale / ICCU — {meta.library_label}",
        "metadata": [m for m in iiif_metadata if m["value"]],
        "_iccu": {
            "oai_id": meta.oai_id,
            "teca": meta.teca,
            "library": meta.library,
            "city": meta.city,
            "sbn_code": meta.sbn_code,
            "shelfmark": meta.shelfmark,
        },
        "sequences": [
            {
                "@type": "sc:Sequence",
                "canvases": canvases,
            }
        ],
    }


def parse_mag_xml(xml_bytes: bytes) -> dict[str, Any]:
    """Parse MAG XML bytes and return a IIIF v2 manifest dict.

    Raises:
        ValueError: if the XML is malformed or missing required structure.
    """
    try:
        root = SafeET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError(f"MAG XML parse error: {exc}") from exc

    # Strip namespace for easier access
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]

    bibinfo = root.find("bibinfo")
    if bibinfo is None:
        raise ValueError("MAG XML missing <bibinfo> element")

    meta = _parse_bibinfo(bibinfo)

    pages: list[dict[str, Any]] = []
    for media in root.findall("medias/media"):
        for page in media.findall("pages/page"):
            try:
                pages.append(
                    {
                        "idx": int(page.get("idx", 0)),
                        "name": page.get("name", ""),
                        "w": int(page.get("w", 0)) or 1000,
                        "h": int(page.get("h", 0)) or 1000,
                    }
                )
            except (ValueError, TypeError):
                continue

    pages.sort(key=lambda p: p["idx"])
    meta.page_count = len(pages)

    logger.debug("ICCU MAG parsed: library=%r shelfmark=%r pages=%d", meta.library, meta.shelfmark, meta.page_count)

    return _build_iiif_v2_manifest(meta, pages)


def fetch_and_convert(magparser_url: str, session: requests.Session | None = None) -> dict[str, Any]:
    """Fetch a MAG XML document from Internet Culturale and convert to IIIF v2 manifest.

    Args:
        magparser_url: Full URL to the IC magparser endpoint.
        session: Optional requests session for connection reuse.

    Returns:
        IIIF v2 manifest dict.

    Raises:
        requests.RequestException: on network failure.
        ValueError: on invalid XML or missing required fields.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/xml,application/xml,*/*",
        "Referer": _IC_BASE,
    }

    requester = session or requests
    resp = requester.get(magparser_url, headers=headers, timeout=(10, 30))
    resp.raise_for_status()

    return parse_mag_xml(resp.content)


def is_iccu_magparser_url(url: str) -> bool:
    """Return True if the URL points to the IC magparser endpoint."""
    return "internetculturale.it" in url and "magparser" in url


__all__ = [
    "IccuMetadata",
    "build_magparser_url",
    "build_thumbnail_url",
    "extract_oai_and_teca_from_url",
    "fetch_and_convert",
    "is_iccu_magparser_url",
    "parse_mag_xml",
]
