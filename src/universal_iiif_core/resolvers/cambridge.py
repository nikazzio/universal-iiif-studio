from __future__ import annotations

import re

from .base import BaseResolver

_DIRECT_CAMBRIDGE_ID_RE = re.compile(r"(?=.*[A-Z])[A-Z0-9]+(?:-[A-Z0-9]+){2,}")
_URL_CAMBRIDGE_ID_RE = re.compile(r"([A-Za-z0-9]+(?:-[A-Za-z0-9]+)+)")
_CAMBRIDGE_SHELFMARK_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_CAMBRIDGE_SHELFMARK_PREFIX_RE = re.compile(r"^\s*MS\b", flags=re.IGNORECASE)
# Splits a mixed alpha-numeric token like "FF1" into its alpha and numeric parts.
_ALPHANUM_SPLIT_RE = re.compile(r"^(?P<alpha>[A-Za-z]+)(?P<num>\d+)$")


class CambridgeResolver(BaseResolver):
    """Resolver for Cambridge University Digital Library manifests."""

    base_url = "https://cudl.lib.cam.ac.uk/iiif"

    def can_resolve(self, url_or_id: str) -> bool:
        """Return True for supported CUDL URLs or direct shelfmark-style IDs."""
        text = (url_or_id or "").strip()
        if not text:
            return False
        if "cudl.lib.cam.ac.uk" in text.lower():
            return True
        return bool(self._extract_id(text))

    def get_manifest_url(self, url_or_id: str) -> tuple[str | None, str | None]:
        """Build the canonical CUDL manifest URL from a URL or direct identifier."""
        text = (url_or_id or "").strip()
        if not text:
            return None, None

        doc_id = self._extract_id(text)
        if not doc_id:
            return None, None

        return f"{self.base_url}/{doc_id}", doc_id

    @staticmethod
    def _extract_id(value: str) -> str | None:
        if "cudl.lib.cam.ac.uk" not in value.lower():
            candidate = value.strip().upper()
            if _DIRECT_CAMBRIDGE_ID_RE.fullmatch(candidate):
                parts = candidate.split("-")
                if parts and parts[0] == "MS":
                    return CambridgeResolver._canonicalize_ms_shelfmark(parts)
                return candidate
            normalized = CambridgeResolver._normalize_shelfmark(candidate)
            return normalized if normalized and _DIRECT_CAMBRIDGE_ID_RE.fullmatch(normalized) else None

        trimmed = value.split("?", 1)[0].split("#", 1)[0].rstrip("/")
        parts = [part for part in trimmed.split("/") if part]
        if not parts:
            return None

        candidate = parts[-1]
        match = _URL_CAMBRIDGE_ID_RE.fullmatch(candidate)
        return match.group(1).upper() if match else None

    @staticmethod
    def _normalize_shelfmark(value: str) -> str | None:
        if not _CAMBRIDGE_SHELFMARK_PREFIX_RE.match(value):
            return None
        tokens = [token.upper() for token in _CAMBRIDGE_SHELFMARK_TOKEN_RE.findall(value)]
        return CambridgeResolver._canonicalize_ms_shelfmark(tokens)

    @staticmethod
    def _canonicalize_ms_shelfmark(tokens: list[str]) -> str | None:
        if not tokens or tokens[0] != "MS" or len(tokens) < 3:
            return None
        # Expand mixed alpha-numeric collection tokens (e.g. "FF1" → ["FF", "1"])
        # so that shelfmarks like "MS Ff1.27" are handled identically to "MS Ff.1.27".
        expanded: list[str] = [tokens[0]]
        for token in tokens[1:]:
            m = _ALPHANUM_SPLIT_RE.fullmatch(token)
            if m:
                expanded.append(m.group("alpha").upper())
                expanded.append(m.group("num"))
            else:
                expanded.append(token)
        tokens = expanded
        if not tokens[1].isalpha():
            return None
        suffix = tokens[2:]
        if not suffix or not all(token.isdigit() for token in suffix):
            return None
        canonical_tokens = [token.zfill(5) if token.isdigit() else token for token in tokens]
        return "-".join(canonical_tokens)
