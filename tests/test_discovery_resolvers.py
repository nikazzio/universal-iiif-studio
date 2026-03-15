"""Unit tests for resolver helpers (no network requests)."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from universal_iiif_core.resolvers.archive_org import ArchiveOrgResolver
from universal_iiif_core.resolvers.cambridge import CambridgeResolver
from universal_iiif_core.resolvers.discovery import resolve_shelfmark
from universal_iiif_core.resolvers.ecodices import EcodicesResolver
from universal_iiif_core.resolvers.gallica import GallicaResolver
from universal_iiif_core.resolvers.harvard import HarvardResolver
from universal_iiif_core.resolvers.heidelberg import HeidelbergResolver
from universal_iiif_core.resolvers.institut import InstitutResolver
from universal_iiif_core.resolvers.loc import LOCResolver
from universal_iiif_core.resolvers.oxford import OxfordResolver
from universal_iiif_core.resolvers.vatican import normalize_shelfmark


def test_normalize_vatican_variants():
    """Test Vatican shelfmark normalization with different formats."""
    assert normalize_shelfmark("Urb. lat. 123") == "MSS_Urb.lat.123"
    assert normalize_shelfmark("urb lat 123") == "MSS_Urb.lat.123"
    assert normalize_shelfmark("Vat.Lat.123") == "MSS_Vat.lat.123"


def test_resolve_shelfmark_vatican():
    """Test Vatican Resolver with normalized shelfmark."""
    url, doc_id = resolve_shelfmark("Vaticana", "Urb. lat. 123")
    assert url is not None and url.endswith("MSS_Urb.lat.123/manifest.json")
    assert doc_id == "MSS_Urb.lat.123"


def test_gallica_resolver_short_and_ark():
    """Test Gallica Resolver with short ID and full ARK URL."""
    r = GallicaResolver()
    manifest, doc = r.get_manifest_url("btv1b84260335")
    assert manifest == "https://gallica.bnf.fr/iiif/ark:/12148/btv1b84260335/manifest.json"
    assert doc == "btv1b84260335"

    full, doc2 = r.get_manifest_url("https://gallica.bnf.fr/ark:/12148/btv1b84260335")
    assert full == "https://gallica.bnf.fr/iiif/ark:/12148/btv1b84260335/manifest.json"
    assert doc2 == "btv1b84260335"


def test_oxford_uuid_case_insensitive():
    """Test Oxford Resolver with UUID in different cases."""
    r = OxfordResolver()
    upper = "080F88F5-7586-4B8A-8064-63AB3495393C"
    manifest, uid = r.get_manifest_url(upper)
    assert uid == "080f88f5-7586-4b8a-8064-63ab3495393c"
    assert manifest.endswith(f"{uid}.json")


def test_institut_resolver_id_and_viewer_url():
    """Test Institut resolver with numeric id and viewer URL."""
    resolver = InstitutResolver()

    manifest_url, doc_id = resolver.get_manifest_url("17837")
    assert manifest_url == "https://bibnum.institutdefrance.fr/iiif/17837/manifest"
    assert doc_id == "17837"

    manifest_url2, doc_id2 = resolver.get_manifest_url(
        "https://bibnum.institutdefrance.fr/viewer/17837?viewer=picture#page=7"
    )
    assert manifest_url2 == "https://bibnum.institutdefrance.fr/iiif/17837/manifest"
    assert doc_id2 == "17837"


def test_heidelberg_resolver_id_and_viewer_url():
    """Resolve Heidelberg viewer IDs into canonical IIIF manifests."""
    resolver = HeidelbergResolver()

    manifest_url, doc_id = resolver.get_manifest_url("cpg123")
    assert manifest_url == "https://digi.ub.uni-heidelberg.de/diglit/iiif/cpg123/manifest.json"
    assert doc_id == "cpg123"

    manifest_url2, doc_id2 = resolver.get_manifest_url("https://digi.ub.uni-heidelberg.de/diglit/cpl456")
    assert manifest_url2 == "https://digi.ub.uni-heidelberg.de/diglit/iiif/cpl456/manifest.json"
    assert doc_id2 == "cpl456"
    manifest_url3, doc_id3 = resolver.get_manifest_url("Cod. Pal. germ. 123")
    assert manifest_url3 == "https://digi.ub.uni-heidelberg.de/diglit/iiif/cpg123/manifest.json"
    assert doc_id3 == "cpg123"

    assert resolver.can_resolve("cpg123")
    assert resolver.can_resolve("Cod. Pal. germ. 123")
    assert not resolver.can_resolve("abc123")
    assert resolver.get_manifest_url("prefix cpg123 suffix") == (None, None)


def test_cambridge_resolver_id_and_viewer_url():
    """Resolve CUDL IDs and viewer URLs into canonical IIIF manifests."""
    resolver = CambridgeResolver()

    manifest_url, doc_id = resolver.get_manifest_url("MS-ADD-03996")
    assert manifest_url == "https://cudl.lib.cam.ac.uk/iiif/MS-ADD-03996"
    assert doc_id == "MS-ADD-03996"

    manifest_url2, doc_id2 = resolver.get_manifest_url("https://cudl.lib.cam.ac.uk/view/MS-ADD-03996")
    assert manifest_url2 == "https://cudl.lib.cam.ac.uk/iiif/MS-ADD-03996"
    assert doc_id2 == "MS-ADD-03996"
    manifest_url3, doc_id3 = resolver.get_manifest_url("MS Add.9597/9/1")
    assert manifest_url3 == "https://cudl.lib.cam.ac.uk/iiif/MS-ADD-09597-00009-00001"
    assert doc_id3 == "MS-ADD-09597-00009-00001"
    assert resolver.get_manifest_url("MS Add Dante") == (None, None)
    assert resolver.can_resolve("MS Add Dante") is False
    assert not resolver.can_resolve("csg-0001")


def test_ecodices_resolver_compound_id_and_page_url():
    """Normalize e-codices page URLs into compound manifest IDs."""
    resolver = EcodicesResolver()

    manifest_url, doc_id = resolver.get_manifest_url("csg-0001")
    assert manifest_url == "https://www.e-codices.unifr.ch/metadata/iiif/csg-0001/manifest.json"
    assert doc_id == "csg-0001"

    manifest_url2, doc_id2 = resolver.get_manifest_url("https://www.e-codices.unifr.ch/en/csg/0001")
    assert manifest_url2 == "https://www.e-codices.unifr.ch/metadata/iiif/csg-0001/manifest.json"
    assert doc_id2 == "csg-0001"
    assert resolver.can_resolve("foo-bar") is False


def test_harvard_resolver_extracts_drs_id():
    """Extract Harvard DRS identifiers from viewer URLs."""
    resolver = HarvardResolver()

    manifest_url, doc_id = resolver.get_manifest_url("https://iiif.lib.harvard.edu/manifests/view/drs:12345678")
    assert manifest_url == "https://iiif.lib.harvard.edu/manifests/drs:12345678"
    assert doc_id == "12345678"


def test_loc_resolver_strips_span_suffix():
    """Strip LOC span suffixes before building manifest URLs."""
    resolver = LOCResolver()

    manifest_url, doc_id = resolver.get_manifest_url("https://www.loc.gov/item/2021668145:sp1/")
    assert manifest_url == "https://www.loc.gov/item/2021668145/manifest.json"
    assert doc_id == "2021668145"
    assert not resolver.can_resolve("https://example.org/item/2021668145/")
    assert not resolver.can_resolve("https://notloc.gov/item/2021668145/")


def test_archive_org_resolver_identifier_details_and_manifest_url():
    """Resolve Archive.org identifiers and URLs into canonical IIIF manifests."""
    resolver = ArchiveOrgResolver()

    manifest_url, doc_id = resolver.get_manifest_url("b29000427_0001")
    assert manifest_url == "https://iiif.archive.org/iiif/b29000427_0001/manifest.json"
    assert doc_id == "b29000427_0001"

    manifest_url2, doc_id2 = resolver.get_manifest_url("https://archive.org/details/b29000427_0001")
    assert manifest_url2 == "https://iiif.archive.org/iiif/b29000427_0001/manifest.json"
    assert doc_id2 == "b29000427_0001"

    manifest_url3, doc_id3 = resolver.get_manifest_url("https://iiif.archive.org/iiif/b29000427_0001/manifest.json")
    assert manifest_url3 == "https://iiif.archive.org/iiif/b29000427_0001/manifest.json"
    assert doc_id3 == "b29000427_0001"
    assert not resolver.can_resolve("https://notarchive.org/details/b29000427_0001")
