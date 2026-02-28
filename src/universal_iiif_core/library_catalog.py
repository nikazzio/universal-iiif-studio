"""Helpers for manuscript classification and catalog metadata enrichment."""

from __future__ import annotations

import json
import re
from html import unescape
from typing import Any
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup

from .logger import get_logger
from .utils import DEFAULT_HEADERS

logger = get_logger(__name__)

ITEM_TYPES = (
    "manoscritto",
    "libro a stampa",
    "incunabolo",
    "periodico",
    "musica/spartito",
    "mappa/atlante",
    "miscellanea",
    "non classificato",
)

_ITEM_TYPE_ALIASES = {
    "altro": "non classificato",
    "other": "non classificato",
    "unknown": "non classificato",
}

_TYPE_RULES: tuple[tuple[str, tuple[str, ...], float], ...] = (
    ("incunabolo", ("incunab",), 0.96),
    ("musica/spartito", ("spartito", "music", "musica", "chant", "corale"), 0.92),
    ("mappa/atlante", ("atlas", "atlante", "map", "cartograf"), 0.9),
    ("periodico", ("periodic", "journal", "rivista", "gazzetta", "newspaper"), 0.9),
    ("libro a stampa", ("stampa", "printed", "print", "typograph", "edition"), 0.88),
    ("manoscritto", ("manoscr", "manuscript", "codex", "ms "), 0.87),
    ("miscellanea", ("miscellanea", "raccolta", "collectanea"), 0.75),
)
_URL_RE = re.compile(r"https?://[^\s<>'\"()]+", flags=re.IGNORECASE)


def normalize_item_type(value: str | None) -> str:
    """Normalize legacy/unknown item type values to the canonical taxonomy."""
    text = (value or "").strip().lower()
    if not text:
        return "non classificato"
    text = _ITEM_TYPE_ALIASES.get(text, text)
    if text in ITEM_TYPES:
        return text
    return "non classificato"


def flatten_iiif_value(value: Any) -> str:
    """Flatten common IIIF text containers into a readable string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        chunks = []
        for inner in value.values():
            flattened = flatten_iiif_value(inner)
            if flattened:
                chunks.append(flattened)
        return " | ".join(dict.fromkeys(chunks))
    if isinstance(value, (list, tuple)):
        chunks = []
        for inner in value:
            flattened = flatten_iiif_value(inner)
            if flattened:
                chunks.append(flattened)
        return " | ".join(dict.fromkeys(chunks))
    return str(value).strip()


def metadata_to_map(metadata_obj: Any) -> dict[str, str]:
    """Return normalized metadata map from IIIF metadata list."""
    out: dict[str, str] = {}
    if not isinstance(metadata_obj, list):
        return out
    for entry in metadata_obj:
        if not isinstance(entry, dict):
            continue
        key = flatten_iiif_value(entry.get("label") or entry.get("name") or entry.get("property"))
        val = flatten_iiif_value(entry.get("value") or entry.get("val"))
        if key and val:
            out[key.lower()] = val
    return out


def infer_item_type(
    label: str,
    description: str = "",
    metadata: dict[str, str] | None = None,
) -> tuple[str, float, str]:
    """Infer item type from label/description/metadata tokens."""
    metadata = metadata or {}
    corpus = " ".join(
        chunk
        for chunk in (
            label or "",
            description or "",
            metadata.get("type", ""),
            metadata.get("genre", ""),
            metadata.get("format", ""),
            metadata.get("material", ""),
            metadata.get("description", ""),
        )
        if chunk
    ).lower()
    for item_type, tokens, confidence in _TYPE_RULES:
        for token in tokens:
            if token in corpus:
                return item_type, confidence, f"match:{token}"
    return "non classificato", 0.2, "fallback:no-rule-match"


def extract_see_also_urls(see_also: Any) -> list[str]:
    """Extract normalized URLs from `seeAlso` values in string/dict/list formats."""
    if not see_also:
        return []
    urls: list[str] = []
    items = see_also if isinstance(see_also, list) else [see_also]
    for item in items:
        if isinstance(item, str):
            candidate = item.strip()
        elif isinstance(item, dict):
            candidate = str(item.get("id") or item.get("@id") or item.get("url") or "").strip()
        else:
            candidate = ""
        if candidate:
            urls.append(candidate)
    # Preserve order while removing duplicates.
    return list(dict.fromkeys(urls))


def _compact_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _extract_urls_from_text(text: str) -> list[str]:
    if not text:
        return []
    out = []
    for raw in _URL_RE.findall(text):
        cleaned = raw.rstrip(".,;:)")
        if cleaned:
            out.append(cleaned)
    return list(dict.fromkeys(out))


def _extract_urls_from_iiif_value(value: Any) -> list[str]:
    urls: list[str] = []
    if value is None:
        return urls
    if isinstance(value, str):
        return _extract_urls_from_text(value.strip())
    if isinstance(value, dict):
        for key in ("id", "@id", "url", "homepage", "seeAlso", "related", "service", "rendering"):
            if key in value:
                urls.extend(_extract_urls_from_iiif_value(value.get(key)))
        return list(dict.fromkeys(urls))
    if isinstance(value, (list, tuple)):
        for item in value:
            urls.extend(_extract_urls_from_iiif_value(item))
        return list(dict.fromkeys(urls))
    return urls


def _extract_catalog_candidate_urls(manifest: dict[str, Any], metadata_map: dict[str, str]) -> list[str]:
    urls: list[str] = []

    for key in ("related", "homepage", "rendering", "service"):
        urls.extend(_extract_urls_from_iiif_value(manifest.get(key)))

    for key, value in metadata_map.items():
        normalized_key = re.sub(r"[^a-z0-9]+", "", key.lower())
        if any(
            token in normalized_key
            for token in ("relation", "source", "identifier", "url", "link", "catalog", "notice", "record")
        ):
            urls.extend(_extract_urls_from_text(value))

    return list(dict.fromkeys(urls))


def _is_oai_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    query = parsed.query.lower()
    return (
        "oai.bnf.fr" in host
        or "oaihandler" in path
        or "/oai2/" in path
        or "verb=getrecord" in query
        or "metadataprefix=oai_dc" in query
    )


def _is_vatican_detail_url(url: str) -> bool:
    parsed = urlparse(url)
    return "digi.vatlib.it" in parsed.netloc.lower() and "/mss/detail/" in parsed.path.lower()


def _is_gallica_catalog_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    if "archivesetmanuscrits.bnf.fr" in host and "ark:/12148" in path:
        return True
    if "gallica.bnf.fr" in host and "ark:/12148" in path:
        return not any(path.endswith(ext) for ext in (".thumbnail", ".highres", ".lowres", ".medres"))
    return False


def _is_oxford_detail_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    return "digital.bodleian.ox.ac.uk" in host and any(token in path for token in ("/objects/", "/record/", "/iiif/"))


def _is_detail_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return (
        _is_vatican_detail_url(url)
        or _is_gallica_catalog_url(url)
        or _is_oxford_detail_url(url)
        or "/detail/" in path
    )


def _is_search_url(url: str) -> bool:
    text = (url or "").lower()
    return any(token in text for token in ("advanced-search", "/search", "ricerca", "discover", "query="))


def _is_derivative_media_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in (".thumbnail", ".highres", ".lowres", ".medres", ".image"))


def _score_url_features(url: str, *, from_see_also: bool) -> int:
    score = 0
    for predicate, delta in (
        (_is_oai_url, -500),
        (_is_vatican_detail_url, 320),
        (_is_gallica_catalog_url, 250),
        (_is_oxford_detail_url, 220),
        (_is_detail_url, 170),
        (_is_search_url, -160),
        (_is_derivative_media_url, -90),
    ):
        if predicate(url):
            score += delta

    if from_see_also:
        score += 15
    if urlparse(url).scheme.lower() == "https":
        score += 5
    return score


def _url_score(url: str, *, from_see_also: bool, tokens: list[str]) -> int:
    score = _score_url_features(url, from_see_also=from_see_also)
    compact_url = _compact_token(url)
    if any(token and token in compact_url for token in tokens):
        score += 80
    return score


def choose_primary_detail_url(
    see_also_urls: list[str],
    shelfmark: str = "",
    doc_id: str = "",
    *,
    fallback_urls: list[str] | None = None,
) -> str:
    """Choose the most relevant catalog URL for this manuscript."""
    candidates: list[tuple[str, bool]] = []
    candidates.extend((url, True) for url in (see_also_urls or []))
    candidates.extend((url, False) for url in (fallback_urls or []))
    if not candidates:
        return ""

    tokens = []
    for raw in (shelfmark, doc_id):
        text = (raw or "").strip()
        if not text:
            continue
        token = _compact_token(text.removeprefix("MSS_").removeprefix("MSS."))
        if token:
            tokens.append(token)

    deduped: list[tuple[str, bool]] = []
    seen: set[str] = set()
    for url, from_see_also in candidates:
        candidate = (url or "").strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        deduped.append((candidate, from_see_also))

    best_url = deduped[0][0]
    best_score = _url_score(best_url, from_see_also=deduped[0][1], tokens=tokens)
    for url, from_see_also in deduped[1:]:
        score = _url_score(url, from_see_also=from_see_also, tokens=tokens)
        if score > best_score:
            best_url = url
            best_score = score
    return best_url


def _derive_vatican_detail_url(manifest_url: str, doc_id: str = "") -> str:
    parsed = urlparse(manifest_url or "")
    if "digi.vatlib.it" not in parsed.netloc.lower():
        return ""

    detail_id = ""
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 3 and parts[-1].lower() == "manifest.json" and "iiif" in (part.lower() for part in parts):
        detail_id = unquote(parts[-2]).strip()
    if not detail_id:
        detail_id = str(doc_id or "").strip()
    if not detail_id:
        return ""

    detail_id = re.sub(r"^mss[_\.]", "", detail_id, flags=re.IGNORECASE).strip()
    if not detail_id:
        return ""
    return f"https://digi.vatlib.it/mss/detail/{detail_id}"


def _extract_meta_contents(html: str, keys: list[str]) -> list[str]:
    values: list[str] = []
    for key in keys:
        escaped = re.escape(key)
        for pattern in (
            rf'<meta[^>]+(?:property|name|itemprop)=["\']{escaped}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name|itemprop)=["\']{escaped}["\']',
        ):
            matches = re.findall(pattern, html, flags=re.IGNORECASE | re.DOTALL)
            for raw in matches:
                cleaned = _clean_reference_candidate(raw)
                if cleaned:
                    values.append(cleaned)
    return list(dict.fromkeys(values))


def _extract_json_ld_objects(html: str) -> list[Any]:
    objs: list[Any] = []
    matches = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for raw in matches:
        payload = raw.strip()
        if not payload:
            continue
        try:
            parsed = json.loads(payload)
        except Exception:
            logger.debug("Invalid JSON-LD payload encountered during catalog enrichment", exc_info=True)
            continue
        if isinstance(parsed, list):
            objs.extend(parsed)
        else:
            objs.append(parsed)
    return objs


def _extract_json_ld_value(objects: list[Any], keys: tuple[str, ...]) -> str:
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        for key in keys:
            value = flatten_iiif_value(obj.get(key))
            if value and not _is_generic_site_title(value):
                return value
    return ""


def _extract_host_specific_fields(url: str) -> dict[str, str]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path
    out: dict[str, str] = {}

    if "digi.vatlib.it" in host:
        out["repository"] = "Biblioteca Apostolica Vaticana"
        if "/mss/detail/" in path.lower():
            out["detail_identifier"] = path.rstrip("/").split("/")[-1]
    elif "archivesetmanuscrits.bnf.fr" in host or "gallica.bnf.fr" in host:
        out["repository"] = "Bibliotheque nationale de France"
        match = re.search(r"ark:/12148/([a-z0-9]+)", path.lower())
        if match:
            out["ark_identifier"] = match.group(1)
    elif "digital.bodleian.ox.ac.uk" in host:
        out["repository"] = "Bodleian Libraries"

    out["source_host"] = host
    return out


def _normalize_external_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (key or "").lower()).strip("_")


def _extract_numbered_references(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if not normalized:
        return []
    normalized = re.sub(r"(?i)\bbibliographic references?\s*:\s*", "", normalized).strip()
    refs: list[str] = []
    for raw in re.findall(r"(\d+\)\s*.+?)(?=(?:\s+\d+\)\s)|$)", normalized):
        cleaned = _clean_reference_candidate(raw)
        if cleaned and not _is_generic_site_title(cleaned):
            refs.append(cleaned)
    return list(dict.fromkeys(refs))


def _extract_vatican_bibliographic_refs(html: str) -> list[str]:
    refs: list[str] = []
    soup = BeautifulSoup(html, "html.parser")
    detail_body = soup.find(id="region-detail-body")
    if detail_body:
        text_refs = _extract_numbered_references(detail_body.get_text("\n", strip=True))
        if text_refs:
            refs.extend(text_refs)
    if not refs:
        # Fallback for simpler/static markup variants.
        for raw in re.findall(r">\s*(\d+\)\s*[^<]{20,500})<", html, flags=re.IGNORECASE):
            cleaned = _clean_reference_candidate(raw)
            if cleaned and not _is_generic_site_title(cleaned):
                refs.append(cleaned)
    return list(dict.fromkeys(refs))[:5]


def _merge_external_metadata(metadata_map: dict[str, str], external_fields: dict[str, str]) -> dict[str, str]:
    merged = dict(metadata_map)
    for raw_key, raw_value in external_fields.items():
        value = str(raw_value or "").strip()
        normalized = _normalize_external_key(raw_key)
        if not value or not normalized:
            continue
        if normalized in {"shelfmark", "collocation", "segnatura", "date", "issued", "language"}:
            if not str(merged.get(normalized) or "").strip():
                merged[normalized] = value
            continue
        ext_key = normalized if normalized.startswith("ext_") else f"ext_{normalized}"
        if not str(merged.get(ext_key) or "").strip():
            merged[ext_key] = value
    return merged


def extract_external_catalog_data(url: str, timeout: int = 8) -> dict[str, Any]:
    """Extract catalog reference text and extra metadata from an external page."""
    if not url:
        return {"reference_text": "", "external_fields": {}}
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        response.raise_for_status()
    except Exception:
        logger.debug("Reference fetch failed for %s", url, exc_info=True)
        return {"reference_text": "", "external_fields": {}}

    html = response.text
    reference_text = _extract_reference_from_html(html)
    json_ld = _extract_json_ld_objects(html)
    external_fields = _extract_host_specific_fields(url)
    host = urlparse(url).netloc.lower()

    if "digi.vatlib.it" in host:
        refs = _extract_vatican_bibliographic_refs(html)
        if refs:
            external_fields["bibliographic_references_count"] = str(len(refs))
            external_fields["bibliographic_reference_1"] = refs[0][:240]
            if len(refs) > 1:
                external_fields["bibliographic_reference_2"] = refs[1][:240]

    author = _extract_json_ld_value(json_ld, ("author", "creator"))
    if not author:
        author = next(iter(_extract_meta_contents(html, ["author", "citation_author", "dc.creator"])), "")
    if author:
        external_fields["author"] = author[:240]

    description = _extract_json_ld_value(json_ld, ("description",))
    if not description:
        description = next(iter(_extract_meta_contents(html, ["description", "dc.description"])), "")
    if description and not _is_generic_site_title(description):
        external_fields["description"] = description[:240]

    return {
        "reference_text": reference_text,
        "external_fields": external_fields,
    }


def extract_external_reference(url: str, timeout: int = 8) -> str:
    """Extract a short human reference string from external catalog page."""
    return str(extract_external_catalog_data(url, timeout=timeout).get("reference_text") or "")


def _extract_reference_from_html(html: str) -> str:
    candidates: list[str] = _extract_meta_contents(
        html,
        [
            "og:title",
            "twitter:title",
            "title",
            "dc.title",
            "citation_title",
            "dcterms.title",
        ],
    )
    for pattern in (r"<h1[^>]*>(.*?)</h1>", r"<h2[^>]*>(.*?)</h2>", r"<title[^>]*>(.*?)</title>"):
        for raw in re.findall(pattern, html, flags=re.IGNORECASE | re.DOTALL):
            cleaned = _clean_reference_candidate(raw)
            if cleaned:
                candidates.append(cleaned)

    json_ld_title = _extract_json_ld_value(_extract_json_ld_objects(html), ("headline", "name", "title"))
    if json_ld_title:
        candidates.append(json_ld_title)

    for candidate in candidates:
        if not _is_generic_site_title(candidate):
            return candidate[:240]

    # If all candidates are generic placeholders (site headers), ignore them.
    return ""


def _pick_best_reference_chunk(chunks: list[str]) -> str:
    best = chunks[0]
    best_score = -999
    for part in chunks:
        normalized = re.sub(r"[^a-z0-9]+", "", part.lower())
        words = len(part.split())
        score = words * 12 + len(part)
        if _is_generic_site_title(part):
            score -= 120
        if normalized in {"manuscript", "manoscritto", "detail", "dettaglio", "image", "immagine"}:
            score -= 80
        if score > best_score:
            best = part
            best_score = score
    return best


def _clean_reference_candidate(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = unescape(re.sub(r"\s+", " ", text)).strip(" -|")
    # Keep the most descriptive chunk from separators commonly used in page titles.
    chunks = [part.strip() for part in re.split(r"\s[\-\|\u2013]\s", text) if part.strip()]
    if len(chunks) > 1:
        text = _pick_best_reference_chunk(chunks)
    return text


def _is_generic_site_title(text: str) -> bool:
    compact = re.sub(r"[^a-z0-9]+", "", text.lower())
    if compact in {
        "digivatlib",
        "digitalvaticanlibrary",
        "gallica",
        "bnfgallica",
        "oaihandler",
        "oaipmhrepository",
        "oaipmhrepositoryforgallica",
        "repositoryforgallica",
        "bibliothequenationaledefrance",
        "bibliotecaapostolicavaticana",
        "searchanddiscovermanuscripts",
        "searchanddiscovermanuscript",
        "ricercaescoprimanoscritti",
        "advancedsearch",
    }:
        return True
    if "advancedsearch" in compact:
        return True
    if "search" in compact and (
        "manuscript" in compact or "manuscripts" in compact or "manoscritt" in compact or "discover" in compact
    ):
        return True
    return len(text.split()) <= 3 and any(
        token in compact
        for token in (
            "digivatlib",
            "gallica",
            "vatlib",
            "bibliotecaapostolica",
            "oaihandler",
            "searchanddiscovermanuscript",
        )
    )


def is_generic_catalog_text(text: str) -> bool:
    """Public helper to identify site-level placeholder strings."""
    return _is_generic_site_title(text)


def _select_manifest_title(raw_label: str, metadata_map: dict[str, str], shelfmark: str, doc_id: str) -> str:
    """Choose a meaningful title from label/metadata with sane fallbacks."""
    label = (raw_label or "").strip()
    metadata_title = _extract_metadata_title(metadata_map)

    if label and not _is_generic_site_title(label):
        return label
    if metadata_title:
        return metadata_title
    if shelfmark:
        return shelfmark
    if doc_id:
        return doc_id
    return label or "Senza titolo"


def _extract_metadata_title(metadata_map: dict[str, str]) -> str:
    """Extract title-like metadata fields from IIIF metadata map."""
    preferred_keys = ("title", "titre", "titolo", "dc:title", "dc.title")
    for key in preferred_keys:
        value = (metadata_map.get(key) or "").strip()
        if value and not _is_generic_site_title(value):
            return value

    for key, value in metadata_map.items():
        normalized_key = re.sub(r"[^a-z0-9]+", "", key.lower())
        if normalized_key in {"title", "titre", "titolo", "dctitle"}:
            candidate = str(value or "").strip()
            if candidate and not _is_generic_site_title(candidate):
                return candidate
    return ""


def _prefer_reference_title(reference_text: str, label: str, shelfmark: str, doc_id: str) -> bool:
    """Return True when external reference is descriptive enough to be the main title."""
    candidate = (reference_text or "").strip()
    if not candidate or _is_generic_site_title(candidate):
        return False

    compact_candidate = re.sub(r"[^a-z0-9]+", "", candidate.lower())
    for fallback in (label, shelfmark, doc_id):
        compact_fallback = re.sub(r"[^a-z0-9]+", "", str(fallback or "").lower())
        if compact_fallback and compact_candidate == compact_fallback:
            return False
    return True


def parse_manifest_catalog(
    manifest: dict[str, Any],
    manifest_url: str = "",
    doc_id: str = "",
    *,
    enrich_external_reference: bool = False,
) -> dict[str, Any]:
    """Build normalized catalog metadata from a IIIF manifest."""
    raw_label = flatten_iiif_value(manifest.get("label") or manifest.get("title"))
    description = flatten_iiif_value(manifest.get("description"))
    metadata_map = metadata_to_map(manifest.get("metadata") or [])
    metadata_candidate_urls = _extract_catalog_candidate_urls(manifest, metadata_map)
    shelfmark = (
        metadata_map.get("shelfmark") or metadata_map.get("collocation") or metadata_map.get("segnatura") or doc_id
    )
    label = _select_manifest_title(raw_label, metadata_map, shelfmark, doc_id)
    attribution = flatten_iiif_value(manifest.get("attribution") or manifest.get("requiredStatement"))
    see_also_urls = extract_see_also_urls(manifest.get("seeAlso"))
    source_detail_url = choose_primary_detail_url(
        see_also_urls,
        shelfmark,
        doc_id,
        fallback_urls=metadata_candidate_urls,
    )
    derived_vatican_detail_url = _derive_vatican_detail_url(manifest_url, doc_id)
    if derived_vatican_detail_url and (
        not source_detail_url
        or _is_oai_url(source_detail_url)
        or (
            "digi.vatlib.it" in urlparse(source_detail_url).netloc.lower()
            and not _is_vatican_detail_url(source_detail_url)
        )
    ):
        source_detail_url = derived_vatican_detail_url
    reference_text = ""
    external_fields: dict[str, str] = {}
    if enrich_external_reference and source_detail_url and not _is_oai_url(source_detail_url):
        external_data = extract_external_catalog_data(source_detail_url)
        reference_text = str(external_data.get("reference_text") or "")
        fields = external_data.get("external_fields") or {}
        if isinstance(fields, dict):
            external_fields = {str(k): str(v) for k, v in fields.items()}
    if reference_text and _is_generic_site_title(reference_text):
        reference_text = ""
    if not reference_text and source_detail_url and _is_detail_url(source_detail_url):
        parsed = urlparse(source_detail_url)
        if parsed.path:
            reference_text = parsed.path.rstrip("/").split("/")[-1].replace(".", " ")
            reference_text = reference_text.strip()

    merged_metadata_map = _merge_external_metadata(metadata_map, external_fields)
    date_label = merged_metadata_map.get("date") or merged_metadata_map.get("issued") or ""
    language_label = merged_metadata_map.get("language") or ""
    item_type, item_type_confidence, item_type_reason = infer_item_type(label, description, merged_metadata_map)
    catalog_title = reference_text if _prefer_reference_title(reference_text, label, shelfmark, doc_id) else label
    manifest_id = str(manifest.get("@id") or manifest.get("id") or manifest_url or "").strip()

    return {
        "manifest_id": manifest_id,
        "label": label,
        "description": description,
        "attribution": attribution,
        "shelfmark": shelfmark,
        "date_label": date_label,
        "language_label": language_label,
        "see_also_urls": see_also_urls,
        "source_detail_url": source_detail_url,
        "reference_text": reference_text,
        "catalog_title": catalog_title,
        "item_type": item_type,
        "item_type_confidence": item_type_confidence,
        "item_type_reason": item_type_reason,
        "external_fields": external_fields,
        "metadata_map": merged_metadata_map,
        "metadata_json": json.dumps(merged_metadata_map, ensure_ascii=False),
    }
