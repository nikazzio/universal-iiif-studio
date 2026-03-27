from __future__ import annotations

import re

from .base import BaseResolver

# Regex per catturare l'ARK ID dentro un URL lungo.
# Cerca "ark:/12148/" seguito da caratteri alfanumerici.
# Si ferma appena incontra uno slash, un punto interrogativo o la fine della stringa.
_ARK_CAPTURE_RE = re.compile(r"ark:/(12148)/([a-z0-9]+)", flags=re.IGNORECASE)

# Regex per validare un Short ID incollato direttamente (es. bpt6k9604118j)
# Deve iniziare con caratteri tipici Gallica (spesso b) ed essere lungo almeno 6 char.
_SHORT_ID_RE = re.compile(r"^[a-z0-9]{6,}$", flags=re.IGNORECASE)

# Bare IDs matching this pattern belong to Heidelberg (e.g. cpg123, cpl456).
# Exclude them from Gallica autodetection to avoid misrouting catalog shelfmarks.
# Pattern mirrors the known-prefix bare IDs in resolvers/heidelberg.py.
_HEIDELBERG_BARE_ID_RE = re.compile(r"^(?:cpg|cpl|cpgr|cpb)\d+$", flags=re.IGNORECASE)


class GallicaResolver(BaseResolver):
    """Resolver for Gallica (BnF) tailored to extract ARK IDs reliably.

    Supported Inputs:
    - View URL: https://gallica.bnf.fr/ark:/12148/bpt6k9604118j
    - Page URL: https://gallica.bnf.fr/ark:/12148/bpt6k9604118j/f1.image
    - Manifest: https://gallica.bnf.fr/iiif/ark:/12148/bpt6k9604118j/manifest.json
    - Short ID: bpt6k9604118j

    Returns:
    - Canonical IIIF Manifest URL
    """

    def can_resolve(self, url_or_id: str) -> bool:
        """Check if the input can be resolved by Gallica Resolver."""
        s = (url_or_id or "").strip()
        if not s:
            return False
        # Se è un dominio Gallica
        if "gallica.bnf.fr" in s:
            return True
        # Se contiene un pattern ARK esplicito
        if "ark:/" in s:
            return True
        # Se sembra uno short ID valido, ma non un ID Heidelberg (cpg123, hd16, ...)
        if _HEIDELBERG_BARE_ID_RE.fullmatch(s):
            return False
        return bool(_SHORT_ID_RE.match(s))

    def get_manifest_url(self, url_or_id: str) -> tuple[str | None, str | None]:
        """Extract the ID and reconstruct the canonical manifest URL."""
        s = (url_or_id or "").strip()
        if not s:
            return None, None

        # 1. Tentativo ARK Extraction (Il metodo più sicuro)
        # Funziona per qualsiasi URL che contenga "ark:/12148/..."
        match = _ARK_CAPTURE_RE.search(s)
        if match:
            # group(1) è 12148 (NAAN), group(2) è l'ID del documento (es. bpt6k...)
            repo_naan = match.group(1)
            doc_id = match.group(2)

            # FIX: Assicuriamoci che l'ID non abbia "code" sporche
            if "." in doc_id:
                doc_id = doc_id.split(".")[0]

            # Ricostruzione Canonica
            # Pattern ufficiale: https://gallica.bnf.fr/iiif/ark:/{NAAN}/{ID}/manifest.json
            manifest_url = f"https://gallica.bnf.fr/iiif/ark:/{repo_naan}/{doc_id}/manifest.json"
            return manifest_url, doc_id

        # 2. Tentativo Short ID
        # Se l'utente ha incollato solo "bpt6k9604118j" e non è un URL
        if _SHORT_ID_RE.match(s) and "/" not in s:
            doc_id = s
            # Assumiamo il repo standard BnF (12148)
            manifest_url = f"https://gallica.bnf.fr/iiif/ark:/12148/{doc_id}/manifest.json"
            return manifest_url, doc_id

        return None, None
