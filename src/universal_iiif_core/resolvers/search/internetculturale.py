"""Internet Culturale (ICCU) search via HTML scraping.

Searches the IC manuscript catalog at:
  https://www.internetculturale.it/it/16/search?q={query}&instance=magindice
  &searchType=avanzato&channel__typeTipo=Manoscritto

Returns SearchResult entries with full metadata including library, shelfmark,
OAI ID and teca — all required to resolve and download the document.
"""

from __future__ import annotations

import re
from html import unescape
from typing import Final
from urllib.parse import quote_plus, urlencode

import requests

from universal_iiif_core.logger import get_logger
from universal_iiif_core.resolvers.mag_parser import build_magparser_url
from universal_iiif_core.resolvers.models import SearchResult

from ._common import DISCOVERY_TIMEOUT, REAL_BROWSER_HEADERS, get_search_http_client

logger = get_logger(__name__)

_IC_SEARCH_URL: Final = "https://www.internetculturale.it/it/16/search"

# Extracts: id=oai%3A...  and  teca=...  from viewresource href
_OAI_ID_RE = re.compile(r"id=(oai%3A[^&\"']+)", re.IGNORECASE)
_TECA_RE = re.compile(r"[?&]teca=([^&\"']+)", re.IGNORECASE)
_DESC_SOURCE_RE = re.compile(r"descSourceLevel2=([^&\"']+)", re.IGNORECASE)

# Extract title from <h2> following the image link
_TITLE_BLOCK_RE = re.compile(
    r'viewresource\?[^"\']*?id=(oai%3A[^"\'&]+)[^"\']*?teca=([^"\'&]+)[^>]*?>.*?</a>.*?'
    r"<h2[^>]*>(.*?)</h2>.*?"
    r"Rilevanza:\s*([\d.]+)",
    re.DOTALL | re.IGNORECASE,
)

# Extract date/description from text block after h2
_DATE_RE = re.compile(r"\[?\d{3,4}\]?(?:\s*[-–]\s*\[?\d{3,4}\]?)?|\d{4}\s*sec\.", re.IGNORECASE)

# Matches "Biblioteca XYZ - descSourceLevel2=..." to get library from descSourceLevel2
_DESC_LEVEL2_CLEAN_RE = re.compile(r"[+%]20|%2B", re.IGNORECASE)


def _decode_url_component(s: str) -> str:
    """URL-decode a component, replacing %XX and + with their characters."""
    from urllib.parse import unquote_plus

    return unquote_plus(s)


def _clean_html(s: str) -> str:
    """Strip HTML tags and unescape HTML entities."""
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _extract_date(text: str) -> str:
    m = _DATE_RE.search(text)
    return m.group(0).strip() if m else ""


def _parse_search_html(html: str) -> list[SearchResult]:
    """Parse IC search results page HTML into SearchResult list."""
    results: list[SearchResult] = []

    # Split HTML into result blocks by the viewresource anchor
    # Each block starts with a thumbnail img link to viewresource
    blocks = re.split(r"(?=<a[^>]+viewresource\?)", html)

    for block in blocks:
        # Extract OAI ID
        m_oai = _OAI_ID_RE.search(block)
        if not m_oai:
            continue
        raw_oai = m_oai.group(1)
        oai_id = _decode_url_component(raw_oai)

        # Extract teca (try multiple patterns)
        m_teca = _TECA_RE.search(block)
        teca = _decode_url_component(m_teca.group(1)) if m_teca else ""
        if not teca:
            m_desc = _DESC_SOURCE_RE.search(block)
            if m_desc:
                teca = _decode_url_component(m_desc.group(1))

        if not oai_id or not teca:
            continue

        # Extract title from <h2> tag
        m_h2 = re.search(r"<h2[^>]*>(.*?)</h2>", block, re.DOTALL | re.IGNORECASE)
        title = _clean_html(m_h2.group(1)) if m_h2 else ""

        # Extract author (inside <a> tags after h2)
        authors: list[str] = []
        if m_h2:
            after_h2 = block[m_h2.end() :]
            for m_a in re.finditer(r"<a[^>]+channel__creator[^>]+>(.*?)</a>", after_h2, re.IGNORECASE):
                authors.append(_clean_html(m_a.group(1)))

        # Extract text snippet (description block)
        m_desc_block = re.search(
            r"</h2>(.*?)(?:<ul|<div|$)", block[m_h2.end() if m_h2 else 0 :], re.DOTALL | re.IGNORECASE
        )
        description_text = _clean_html(m_desc_block.group(1)) if m_desc_block else ""

        # Extract date
        date = _extract_date(description_text) or _extract_date(title)

        # Library from teca label (descSourceLevel2 is the display name)
        library = teca.replace("+", " ").replace("%20", " ")
        m_desc2 = _DESC_SOURCE_RE.search(block)
        if m_desc2:
            library = _decode_url_component(m_desc2.group(1)).replace("+", " ")

        # Thumbnail
        m_thumb = re.search(r'thumbnail\?[^"\']*?id=([^"\'&]+)[^"\']*?teca=([^"\'&]+)"', block)
        thumb_url = ""
        if m_thumb:
            thumb_url = (
                f"https://www.internetculturale.it/jmms/thumbnail"
                f"?type=preview&id={m_thumb.group(1)}&teca={m_thumb.group(2)}"
            )

        # Build manifest URL (magparser)
        manifest_url = build_magparser_url(oai_id, teca) if oai_id and teca else ""

        # Viewer URL
        viewer_url = (
            f"https://www.internetculturale.it/it/16/search/viewresource"
            f"?id={quote_plus(oai_id)}&teca={quote_plus(teca)}"
        )

        result: SearchResult = {
            "id": oai_id,
            "title": title,
            "author": "; ".join(authors),
            "date": date,
            "description": description_text[:200],
            "library": library,
            "thumbnail": thumb_url,
            "thumb": thumb_url,
            "manifest": manifest_url,
            "manifest_status": "pending",
            "viewer_url": viewer_url,
            "raw": {
                "oai_id": oai_id,
                "teca": teca,
            },
        }
        results.append(result)

    return results


def search_internetculturale(
    query: str,
    max_results: int = 20,
    page: int = 1,
    tipo: str = "Manoscritto",
) -> list[SearchResult]:
    """Search Internet Culturale manuscript catalog.

    Args:
        query: Free-text search query.
        max_results: Maximum results to return (IC returns ~10 per page).
        page: Result page (1-based).
        tipo: Material type filter. "Manoscritto" for manuscripts, "" for all.

    Returns:
        List of SearchResult with library, shelfmark, OAI ID, teca, manifest URL.
    """
    if not query or not query.strip():
        return []

    params: dict[str, str] = {
        "q": query.strip(),
        "instance": "magindice",
        "searchType": "avanzato",
    }
    if tipo:
        params["channel__typeTipo"] = tipo

    # IC uses page offset via a different param
    results_per_page = 10
    offset = (page - 1) * results_per_page
    if offset:
        params["paginate_pageNum"] = str(page)

    url = f"{_IC_SEARCH_URL}?{urlencode(params)}"

    try:
        resp = get_search_http_client().get(
            url,
            headers=REAL_BROWSER_HEADERS,
            timeout=DISCOVERY_TIMEOUT,
            library_name="internetculturale",
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Internet Culturale search failed for %r: %s", query, exc)
        return []

    results = _parse_search_html(resp.text)
    logger.debug("IC search %r → %d raw results (page %d)", query, len(results), page)

    return results[:max_results]
