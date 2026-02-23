from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, Final

from defusedxml import ElementTree as DefusedET

from .models import SearchResult, _DCData

SRU_NS: Final = {
    "srw": "http://www.loc.gov/zing/srw/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
}


class GallicaXMLParser:
    """Parser for Gallica SRU/OAI responses.

    This class does NOT perform network IO: callers should fetch bytes and
    pass them to `parse_sru` so that top-level services can handle timeouts
    and error logging.
    """

    @classmethod
    def parse_sru(cls, xml_bytes: bytes, resolver) -> list[SearchResult]:
        """Parse Gallica SRU XML bytes into a list of SearchResult entries."""
        root = DefusedET.fromstring(xml_bytes)

        records = root.findall(".//srw:record", SRU_NS)
        if not records:
            records = [elem for elem in root.iter() if elem.tag.endswith("record")]

        results: list[SearchResult] = []
        for rec in records:
            if item := cls._parse_record(rec, resolver):
                results.append(item)

        return results

    @classmethod
    def _parse_record(cls, record: ET.Element, resolver) -> SearchResult | None:
        fields = cls._extract_dc_data(record)

        valid_id, valid_ark = cls._extract_valid_identifier(fields.get("identifiers", []), resolver)
        if not valid_id:
            return None

        try:
            manifest_url, _ = resolver.get_manifest_url(valid_ark or valid_id)
            if not manifest_url:
                return None
        except Exception:
            return None

        thumbnail_url = f"https://gallica.bnf.fr/ark:/12148/{valid_id}.thumbnail"

        result: SearchResult = {
            "id": valid_id,
            "title": (fields.get("title") or "Senza titolo")[:200],
            "author": (fields.get("author") or "Autore sconosciuto")[:100],
            "manifest": manifest_url,
            "thumbnail": thumbnail_url,
            "thumb": thumbnail_url,
            "library": "Gallica",
            "raw": {},
        }

        if fields.get("date"):
            result["date"] = fields.get("date")
        desc = fields.get("description") or []
        if desc:
            result["description"] = "\n".join(desc)[:1000]
        publisher = fields.get("publisher")
        if publisher is not None:
            result["publisher"] = publisher[:200]
        language = fields.get("language")
        if language is not None:
            result["language"] = language
        if valid_ark:
            result["ark"] = valid_ark

        return result

    @staticmethod
    def _extract_valid_identifier(identifiers: list[str], resolver) -> tuple[str | None, str | None]:
        for ident in identifiers:
            if "ark:/" in ident and (idx := ident.find("ark:/")) != -1:
                ark = ident[idx:]
                doc_id = ark.split("/")[-1]
                return doc_id, ark

            if resolver.can_resolve(ident):
                return ident, f"ark:/12148/{ident}"

        return None, None

    @staticmethod
    def _extract_dc_data(record: ET.Element) -> _DCData:
        data: _DCData = {
            "title": "Senza titolo",
            "author": "Autore sconosciuto",
            "date": None,
            "description": [],
            "publisher": None,
            "language": None,
            "identifiers": [],
        }

        target_tags: Final = {
            "title",
            "creator",
            "date",
            "description",
            "publisher",
            "source",
            "language",
            "identifier",
        }

        for elem in record.iter():
            tag = elem.tag.split("}")[-1].lower()
            text = (elem.text or "").strip()
            if not text or tag not in target_tags:
                continue

            match tag:
                case "title" if data["title"] == "Senza titolo":
                    data["title"] = text
                case "creator" if data["author"] == "Autore sconosciuto":
                    data["author"] = text
                case "date" if not data["date"]:
                    data["date"] = text
                case "description":
                    data["description"].append(text)
                case "publisher" | "source" if not data["publisher"]:
                    data["publisher"] = text
                case "language" if not data["language"]:
                    data["language"] = text
                case "identifier":
                    data["identifiers"].append(text)

        return data


class IIIFManifestParser:
    """Parse already-fetched IIIF manifest JSON into SearchResult.

    Parsers operate on data only; network IO and logging belong to the
    surrounding service layer.
    """

    @staticmethod
    def parse_manifest(
        manifest: dict[str, Any], manifest_url: str, library: str | None = None, doc_id: str | None = None
    ) -> SearchResult | None:
        """Parse IIIF manifest JSON into a SearchResult entry."""
        title = IIIFManifestParser._extract_label(manifest, doc_id)
        meta_map = IIIFManifestParser._extract_metadata_map(manifest.get("metadata") or [])
        thumb_url = IIIFManifestParser._extract_thumbnail(manifest, manifest_url, doc_id)

        result: SearchResult = {
            "id": doc_id or (manifest.get("id") or manifest_url),
            "title": title[:200],
            "author": IIIFManifestParser._extract_author(meta_map)[:100],
            "manifest": manifest_url,
            "thumbnail": thumb_url or "",
            "thumb": thumb_url or "",
            "library": library or "",
            "raw": manifest,
        }
        IIIFManifestParser._apply_optional_metadata(result, meta_map)
        return result

    @staticmethod
    def _extract_label(manifest: dict[str, Any], doc_id: str | None) -> str:
        """Extract a human-readable label from IIIF manifest fields."""
        label = manifest.get("label") or manifest.get("title")
        if not label:
            return doc_id or "Senza titolo"
        if isinstance(label, dict):
            return IIIFManifestParser._first_dict_value(label, doc_id or "Senza titolo")
        if isinstance(label, list):
            return str(label[0]) if label else (doc_id or "Senza titolo")
        return str(label)

    @staticmethod
    def _first_dict_value(value_map: dict[str, Any], fallback: str) -> str:
        """Return first meaningful dict value supporting scalar and list values."""
        for value in value_map.values():
            if isinstance(value, list) and value:
                return str(value[0])
            if value:
                return str(value)
        return fallback

    @staticmethod
    def _extract_author(meta_map: dict[str, str]) -> str:
        """Extract preferred author field from parsed metadata map."""
        return meta_map.get("creator") or meta_map.get("author") or "Autore sconosciuto"

    @staticmethod
    def _apply_optional_metadata(result: SearchResult, meta_map: dict[str, str]) -> None:
        """Attach optional metadata fields to result when available."""
        if date := meta_map.get("date"):
            result["date"] = date
        if description := meta_map.get("description"):
            result["description"] = description[:1000]
        if publisher := meta_map.get("publisher") or meta_map.get("source"):
            result["publisher"] = publisher
        if language := meta_map.get("language"):
            result["language"] = language

    @staticmethod
    def _extract_metadata_map(metadata_obj: Any) -> dict[str, str]:
        out: dict[str, str] = {}
        if not isinstance(metadata_obj, list):
            return out

        for entry in metadata_obj:
            if not isinstance(entry, dict):
                continue
            k = entry.get("label") or entry.get("name") or ""
            v = entry.get("value") or entry.get("val") or ""
            if isinstance(k, dict):
                k = next(iter(k.values())) if k else ""
            if isinstance(v, dict):
                v = next(iter(v.values())) if v else ""
            if isinstance(v, list):
                v = v[0] if v else ""
            if k and v:
                out[str(k).lower()] = str(v)

        return out

    @staticmethod
    def _extract_thumbnail(manifest: dict[str, Any], manifest_url: str, doc_id: str | None) -> str | None:
        """Extract thumbnail URL from IIIF manifest JSON with fallbacks."""
        return (
            IIIFManifestParser._thumb_from_manifest_thumbnail(manifest)
            or IIIFManifestParser._thumb_from_v3_items(manifest)
            or IIIFManifestParser._thumb_from_v2_sequences(manifest)
            or IIIFManifestParser._thumb_from_heuristics(manifest_url, doc_id)
        )

    @staticmethod
    def _thumb_from_manifest_thumbnail(manifest: dict[str, Any]) -> str | None:
        """Extract thumbnail from top-level `thumbnail` field."""
        thumbnail_obj = manifest.get("thumbnail")
        if isinstance(thumbnail_obj, list):
            thumbnail_obj = thumbnail_obj[0] if thumbnail_obj else None

        if isinstance(thumbnail_obj, dict):
            return thumbnail_obj.get("id") or thumbnail_obj.get("@id") or thumbnail_obj.get("source")
        if isinstance(thumbnail_obj, str):
            return thumbnail_obj
        return None

    @staticmethod
    def _thumb_from_v3_items(manifest: dict[str, Any]) -> str | None:
        """Extract thumbnail from IIIF v3 items/annotations chain."""
        items = manifest.get("items")
        if not isinstance(items, list) or not items:
            return None

        first_item = items[0]
        if not isinstance(first_item, dict):
            return None

        if direct_thumb := IIIFManifestParser._thumb_from_item_thumbnail(first_item):
            return direct_thumb
        return IIIFManifestParser._thumb_from_annotation_body(first_item)

    @staticmethod
    def _thumb_from_item_thumbnail(item: dict[str, Any]) -> str | None:
        """Extract thumbnail directly from a v3 item object."""
        thumbnail_obj = item.get("thumbnail")
        if isinstance(thumbnail_obj, list):
            thumbnail_obj = thumbnail_obj[0] if thumbnail_obj else None
        if isinstance(thumbnail_obj, dict):
            return thumbnail_obj.get("id") or thumbnail_obj.get("@id")
        if isinstance(thumbnail_obj, str):
            return thumbnail_obj
        return None

    @staticmethod
    def _thumb_from_annotation_body(item: dict[str, Any]) -> str | None:
        """Extract thumbnail from first annotation body in v3 structure."""
        ann_items = item.get("items")
        if not isinstance(ann_items, list) or not ann_items or not isinstance(ann_items[0], dict):
            return None

        inner_items = ann_items[0].get("items")
        if not isinstance(inner_items, list) or not inner_items or not isinstance(inner_items[0], dict):
            return None

        body = inner_items[0].get("body")
        if isinstance(body, dict):
            return body.get("id") or body.get("@id")
        return None

    @staticmethod
    def _thumb_from_v2_sequences(manifest: dict[str, Any]) -> str | None:
        """Extract thumbnail from IIIF v2 sequence/canvas/image structure."""
        sequences = manifest.get("sequences")
        if not isinstance(sequences, list) or not sequences:
            return None

        canvases = sequences[0].get("canvases")
        if not isinstance(canvases, list) or not canvases:
            return None

        images = canvases[0].get("images")
        if not isinstance(images, list) or not images:
            return None

        resource = images[0].get("resource")
        if isinstance(resource, dict):
            return resource.get("@id") or resource.get("id")
        return None

    @staticmethod
    def _thumb_from_heuristics(manifest_url: str, doc_id: str | None) -> str | None:
        """Build thumbnail URL using known library URL conventions."""
        if not doc_id:
            return None
        if "bodleian" in manifest_url or "ox.ac.uk" in manifest_url:
            return f"https://iiif.bodleian.ox.ac.uk/iiif/thumbnail/{doc_id}.jpg"
        if "vatlib" in manifest_url:
            return manifest_url.replace("/manifest.json", "/full/!200,200/0/default.jpg")
        return None


__all__ = ["GallicaXMLParser", "IIIFManifestParser", "SRU_NS"]
