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


def _parse_result_block(block: str) -> SearchResult | None:
    """Parse a single `block-item-search-result` HTML block into a SearchResult."""
    # OAI ID: prefer dc_id span (raw, not URL-encoded); fallback to URL param
    m_dc_id = re.search(r"<span[^>]+dc_id[^>]*>(oai:[^<]+)</span>", block, re.IGNORECASE)
    if m_dc_id:
        oai_id = m_dc_id.group(1).strip()
    else:
        m_oai = _OAI_ID_RE.search(block)
        if not m_oai:
            return None
        oai_id = _decode_url_component(m_oai.group(1))

    # teca from descSourceLevel2 URL param in the thumbnail img src
    m_thumb_src = re.search(r'/jmms/thumbnail\?[^"\']*?teca=([^"\'& ]+)', block)
    if m_thumb_src:
        teca = _decode_url_component(m_thumb_src.group(1))
    else:
        # fallback: descSourceLevel2 in viewresource URL
        m_desc = _DESC_SOURCE_RE.search(block)
        teca = _decode_url_component(m_desc.group(1)) if m_desc else ""

    if not oai_id or not teca:
        return None

    # Title: h2.dc_title (distinct from h2.dc_creator which is the author)
    m_title = re.search(r"<h2[^>]+dc_title[^>]*>(.*?)</h2>", block, re.DOTALL | re.IGNORECASE)
    title = _clean_html(m_title.group(1)) if m_title else ""

    # Author: h2.dc_creator
    m_creator = re.search(r"<h2[^>]+dc_creator[^>]*>(.*?)</h2>", block, re.DOTALL | re.IGNORECASE)
    authors: list[str] = []
    if m_creator:
        for m_a in re.finditer(r"<a[^>]+>(.*?)</a>", m_creator.group(1), re.IGNORECASE):
            name = _clean_html(m_a.group(1)).strip(" ;")
            if name:
                authors.append(name)

    # Library: dc_descSourceLevel2 span
    m_lib = re.search(r"<span[^>]+dc_descSourceLevel2[^>]*>(.*?)</span>", block, re.IGNORECASE)
    library = _clean_html(m_lib.group(1)) if m_lib else teca.replace("+", " ")

    # Date: dc_issued span
    m_date = re.search(r"<span[^>]+dc_issued[^>]*>(.*?)</span>", block, re.IGNORECASE)
    date = _clean_html(m_date.group(1)) if m_date else ""

    # Material type: first dc_type span
    m_type = re.search(r"<span[^>]+dc_type[^>]*>(.*?)</span>", block, re.IGNORECASE)
    mat_type = _clean_html(m_type.group(1)) if m_type else ""

    # Thumbnail URL (reconstruct from src path using canonical format)
    thumb_url = ""
    if m_thumb_src:
        thumb_url = (
            f"https://www.internetculturale.it/jmms/thumbnail"
            f"?type=preview&id={quote_plus(oai_id)}&teca={quote_plus(teca)}"
        )

    manifest_url = build_magparser_url(oai_id, teca)
    viewer_url = (
        f"https://www.internetculturale.it/it/16/search/viewresource?id={quote_plus(oai_id)}&teca={quote_plus(teca)}"
    )

    description = f"{mat_type} – {library}" if mat_type else library

    return SearchResult(
        id=oai_id,
        title=title,
        author="; ".join(authors),
        date=date,
        description=description,
        library=library,
        thumbnail=thumb_url,
        thumb=thumb_url,
        manifest=manifest_url,
        manifest_status="pending",
        viewer_url=viewer_url,
        raw={"oai_id": oai_id, "teca": teca, "type": mat_type},
    )


def _parse_search_html(html: str) -> list[SearchResult]:
    """Parse IC search results page HTML into SearchResult list."""
    results: list[SearchResult] = []
    blocks = re.split(r"(?=<div[^>]+block-item-search-result)", html)
    for block in blocks:
        result = _parse_result_block(block)
        if result is not None:
            results.append(result)
    return results


def search_internetculturale(
    query: str,
    max_results: int = 20,
    page: int = 1,
    ic_type_filter: str = "all",
) -> list[SearchResult]:
    """Search Internet Culturale digital catalog.

    Args:
        query: Free-text search query.
        max_results: Maximum results to return (IC returns ~10 per page).
        page: Result page (1-based).
        ic_type_filter: Material type filter key — "all", "Manoscritto", "Libro moderno", etc.
                        "all" means no filter (search all material types).

    Returns:
        List of SearchResult with library, OAI ID, teca, manifest URL.
    """
    if not query or not query.strip():
        return []

    params: dict[str, str] = {
        "q": query.strip(),
        "instance": "magindice",
        "searchType": "avanzato",
    }
    if ic_type_filter and ic_type_filter != "all":
        params["channel__typeTipo"] = ic_type_filter

    if page > 1:
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
