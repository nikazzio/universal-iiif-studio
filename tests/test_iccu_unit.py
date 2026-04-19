"""Unit tests for the Internet Culturale (ICCU) provider."""

from pathlib import Path

from universal_iiif_core.resolvers.internetculturale import InternetCulturaleResolver
from universal_iiif_core.resolvers.mag_parser import (
    build_magparser_url,
    build_thumbnail_url,
    extract_oai_and_teca_from_url,
    is_iccu_magparser_url,
    parse_mag_xml,
    probe_magparser_url,
)


def _fixture_bytes() -> bytes:
    return (Path(__file__).parent / "fixtures" / "iccu_mag_sample.xml").read_bytes()


def test_parse_mag_xml_builds_iiif_v2_manifest():
    manifest = parse_mag_xml(_fixture_bytes())
    assert manifest["@context"] == "http://iiif.io/api/presentation/2/context.json"
    assert manifest["@type"] == "sc:Manifest"
    assert manifest["label"].startswith("III.")
    canvases = manifest["sequences"][0]["canvases"]
    assert len(canvases) == 3
    first = canvases[0]
    assert first["@type"] == "sc:Canvas"
    assert first["width"] == 1600
    assert first["height"] == 2100
    image_url = first["images"][0]["resource"]["@id"]
    assert image_url.startswith("https://www.internetculturale.it/jmms/cacheman/")
    assert image_url.endswith("/1.jpg")
    second_url = canvases[1]["images"][0]["resource"]["@id"]
    assert second_url.endswith("/2.jpg")
    assert image_url != second_url


def test_parse_mag_xml_extracts_metadata_block():
    manifest = parse_mag_xml(_fixture_bytes())
    labels = {m["label"]: m["value"] for m in manifest["metadata"]}
    assert labels["Biblioteca"] == "Biblioteca Medicea Laurenziana"
    assert labels["Città"] == "Firenze"
    assert labels["Codice SBN"] == "IT-FI0100"
    assert labels["Autore"] == "Alighieri, Jacopo"
    iccu = manifest["_iccu"]
    assert iccu["teca"] == "Laurenziana - FI"
    assert iccu["oai_id"].startswith("oai:teca.bmlonline.it")


def test_build_magparser_url_roundtrip():
    url = build_magparser_url("oai:x:y", "marciana", max_pages=10)
    oai, teca = extract_oai_and_teca_from_url(url)
    assert oai == "oai:x:y"
    assert teca == "marciana"
    assert "pag=10" in url
    assert is_iccu_magparser_url(url)


def test_build_thumbnail_url_includes_page():
    url = build_thumbnail_url("oai:a:b", "marciana", page_1based=7)
    assert "page=7" in url
    assert "teca=marciana" in url


def test_resolver_can_resolve_iccu_urls_and_oai_ids():
    r = InternetCulturaleResolver()
    assert r.can_resolve("https://www.internetculturale.it/it/16/search/viewresource?id=oai:x&teca=marciana")
    assert r.can_resolve("oai:teca.bmlonline.it:21:XXXX:Plutei:IT:FI0100_Plutei_40.26_0003")
    assert not r.can_resolve("https://gallica.bnf.fr/ark:/12148/btv1b84260335")
    assert not r.can_resolve("oai:unknown:host:1234")
    assert not r.can_resolve("")


def test_resolver_infers_teca_from_known_prefix():
    r = InternetCulturaleResolver()
    manifest_url, doc_id = r.get_manifest_url("oai:193.206.197.121:18:VE0049:CNMD0000299115")
    assert manifest_url is not None
    assert "teca=marciana" in manifest_url
    assert doc_id == "VE0049_CNMD0000299115"


def test_resolver_returns_none_when_teca_unknown():
    r = InternetCulturaleResolver()
    manifest_url, doc_id = r.get_manifest_url("oai:unknown:host:1234")
    assert manifest_url is None
    assert doc_id is None


class _StubSession:
    def __init__(self, status: int, content: bytes):
        self._status = status
        self._content = content

    def get(self, url, **_kwargs):
        outer = self

        class _Resp:
            content = outer._content
            status_code = outer._status

            def raise_for_status(self):
                if outer._status >= 400:
                    import requests

                    raise requests.HTTPError(f"status {outer._status}")

        return _Resp()


def test_probe_magparser_url_true_on_valid_xml():
    session = _StubSession(200, _fixture_bytes())
    url = build_magparser_url("oai:x:y", "Laurenziana - FI")
    assert probe_magparser_url(url, session=session) is True


def test_probe_magparser_url_false_on_empty_response():
    session = _StubSession(200, b"<?xml version='1.0'?><ignore/>")
    url = build_magparser_url("oai:x:y", "marciana")
    assert probe_magparser_url(url, session=session) is False


def test_probe_magparser_url_false_without_oai_or_teca():
    assert probe_magparser_url("https://www.internetculturale.it/jmms/magparser?foo=1") is False


def test_page_downloader_locates_direct_image_url():
    from universal_iiif_core.logic.downloader import PageDownloader

    canvas = {
        "@id": "x/canvas/0",
        "images": [
            {
                "resource": {
                    "@id": "https://www.internetculturale.it/jmms/thumbnail?id=x&teca=y&page=1",
                    "@type": "dctypes:Image",
                }
            }
        ],
    }
    assert PageDownloader._locate_direct_image_url(canvas) == (
        "https://www.internetculturale.it/jmms/thumbnail?id=x&teca=y&page=1"
    )


def test_page_downloader_returns_none_when_no_resource():
    from universal_iiif_core.logic.downloader import PageDownloader

    assert PageDownloader._locate_direct_image_url({"images": []}) is None
    assert PageDownloader._locate_direct_image_url("not a dict") is None
