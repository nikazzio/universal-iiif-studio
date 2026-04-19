"""Resolver for Internet Culturale (ICCU) — Italian national digital library aggregator.

Covers:
  - Biblioteca Medicea Laurenziana (Firenze)
  - Biblioteca Nazionale Marciana (Venezia)
  - BNCF (Firenze), BNCR (Roma)
  - ~50+ partner institutions via ICCU

Accepted inputs:
  - Full IC viewer URL:  https://www.internetculturale.it/it/16/search/viewresource?id=oai:...&teca=...
  - Magparser URL:       https://www.internetculturale.it/jmms/magparser?id=...&teca=...
  - OAI ID + teca:       oai:193.206.197.121:18:VE0049:CNMD0000299115 (requires teca separately)
  - Raw OAI string:      "oai:teca.bmlonline.it:21:XXXX:Plutei:..."

When only an OAI ID is provided (no teca), the resolver attempts to infer the teca
from the known OAI prefix → teca mapping table.
"""

from __future__ import annotations

import re

from .base import BaseResolver
from .mag_parser import build_magparser_url, extract_oai_and_teca_from_url

# Known OAI prefix → teca mappings (discoverable from IC search results).
# Key: substring that uniquely identifies the OAI host/path prefix.
# Value: teca identifier used in IC API calls.
_OAI_PREFIX_TO_TECA: dict[str, str] = {
    "193.206.197.121:18:VE0049": "marciana",  # Biblioteca Nazionale Marciana
    "teca.bmlonline.it": "Laurenziana - FI",  # Biblioteca Medicea Laurenziana
    "oai.bmlonline.it": "Laurenziana - FI",
    "www.internetculturale.sbn.it/Teca": "MagTeca - ICCU",  # Generic ICCU MagTeca
    "www.internetculturale.sbn.it": "MagTeca - ICCU",
}

_OAI_PREFIX_RE = re.compile(r"^oai:", re.IGNORECASE)
_IC_DOMAIN = "internetculturale.it"


def _infer_teca(oai_id: str) -> str | None:
    """Infer the teca identifier from the OAI ID prefix."""
    for prefix, teca in _OAI_PREFIX_TO_TECA.items():
        if prefix in oai_id:
            return teca
    return None


class InternetCulturaleResolver(BaseResolver):
    """Resolver for Internet Culturale (ICCU) MAG-based digital collections."""

    def can_resolve(self, url_or_id: str) -> bool:
        """Return True when the input is an IC URL or a known OAI identifier."""
        s = (url_or_id or "").strip()
        if not s:
            return False
        if _IC_DOMAIN in s:
            return True
        if _OAI_PREFIX_RE.match(s):
            return bool(_infer_teca(s))
        return False

    def get_manifest_url(self, url_or_id: str) -> tuple[str | None, str | None]:
        """Return (magparser_url, doc_id) for the given input.

        The magparser URL is used by IccuMagParser to fetch and convert the
        MAG XML document into a IIIF v2 manifest in the download pipeline.
        """
        s = (url_or_id or "").strip()
        if not s:
            return None, None

        oai_id, teca = extract_oai_and_teca_from_url(s)

        # If teca not in URL, try to infer from OAI ID
        if oai_id and not teca:
            teca = _infer_teca(oai_id)

        if not oai_id or not teca:
            return None, None

        manifest_url = build_magparser_url(oai_id, teca)
        doc_id = _make_doc_id(oai_id)
        return manifest_url, doc_id


def _make_doc_id(oai_id: str) -> str:
    """Build a short, filesystem-safe doc_id from an OAI identifier.

    Example:
        "oai:193.206.197.121:18:VE0049:CNMD0000299115" → "VE0049_CNMD0000299115"
        "oai:teca.bmlonline.it:21:XXXX:Plutei:IT:FI0100_Plutei_40.26_0004" → "bml_Plutei_40.26"
    """
    # Strip leading "oai:" prefix
    stripped = re.sub(r"^oai:", "", oai_id, flags=re.IGNORECASE)

    # BML pattern: teca.bmlonline.it:21:XXXX:Plutei:IT%3AFI0100_Plutei_40.26_0004
    if "bmlonline" in stripped:
        m = re.search(r"(?:Plutei|Ashburn|Acq|Conv|Conv_Soppr)[^:]*(?::[^:]+)?$", stripped, re.IGNORECASE)
        if m:
            return "bml_" + re.sub(r"[^a-zA-Z0-9._-]", "_", m.group(0))[:50]
        return "bml_" + re.sub(r"[^a-zA-Z0-9._-]", "_", stripped[-30:])

    # Marciana / SBN pattern: 193.206.197.121:18:VE0049:CNMD0000299115
    parts = stripped.split(":")
    if len(parts) >= 2:
        sbn_part = next((p for p in parts if re.match(r"[A-Z]{2}\d{4}", p)), None)
        last_part = parts[-1]
        if sbn_part and last_part != sbn_part:
            return f"{sbn_part}_{last_part}"[:60]
        return last_part[:60]

    return re.sub(r"[^a-zA-Z0-9._-]", "_", stripped)[:60]
