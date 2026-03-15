from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from universal_iiif_core.logger import get_logger
from universal_iiif_core.resolvers.archive_org import ArchiveOrgResolver
from universal_iiif_core.resolvers.base import BaseResolver
from universal_iiif_core.resolvers.cambridge import CambridgeResolver
from universal_iiif_core.resolvers.ecodices import EcodicesResolver
from universal_iiif_core.resolvers.gallica import GallicaResolver
from universal_iiif_core.resolvers.generic import GenericResolver
from universal_iiif_core.resolvers.harvard import HarvardResolver
from universal_iiif_core.resolvers.heidelberg import HeidelbergResolver
from universal_iiif_core.resolvers.institut import InstitutResolver
from universal_iiif_core.resolvers.loc import LOCResolver
from universal_iiif_core.resolvers.oxford import OxfordResolver
from universal_iiif_core.resolvers.vatican import VaticanResolver

logger = get_logger(__name__)

SearchStrategy = Literal[
    "archive_org",
    "bodleian",
    "cambridge",
    "ecodices",
    "gallica",
    "harvard",
    "heidelberg",
    "institut",
    "loc",
    "vatican",
]
SearchMode = Literal["direct", "fallback", "search_first"]


@dataclass(frozen=True)
class ProviderFilterOption:
    """Single selectable value for a provider-specific discovery filter."""

    label: str
    value: str


@dataclass(frozen=True)
class ProviderFilter:
    """Discovery filter metadata exposed by a provider."""

    key: str
    label: str
    options: tuple[ProviderFilterOption, ...]


@dataclass(frozen=True)
class IIIFProvider:
    """Shared metadata and capabilities for an IIIF discovery provider."""

    key: str
    label: str
    aliases: tuple[str, ...]
    resolver_cls: type[BaseResolver]
    search_strategy: SearchStrategy | None = None
    search_mode: SearchMode = "direct"
    filters: tuple[ProviderFilter, ...] = ()
    not_found_hint: str = "Verifica la segnatura."
    placeholder: str = "Inserisci ID, URL o testo libero"
    include_in_ui: bool = True
    sort_order: int = 100
    metadata: dict[str, str] = field(default_factory=dict)

    def resolver(self) -> BaseResolver:
        """Build a fresh resolver instance for direct manifest resolution."""
        return self.resolver_cls()

    def supports_search(self) -> bool:
        """Return True when the provider exposes a search strategy."""
        return self.search_strategy is not None

    def supports_direct_resolution(self) -> bool:
        """Return True when the provider has a dedicated resolver."""
        return self.resolver_cls is not GenericResolver


_GALLICA_FILTER = ProviderFilter(
    key="gallica_type",
    label="Filtro (Gallica)",
    options=(
        ProviderFilterOption("Tutti i materiali", "all"),
        ProviderFilterOption("Solo manoscritti", "manuscrit"),
        ProviderFilterOption("Solo libri a stampa", "printed"),
    ),
)


PROVIDERS: tuple[IIIFProvider, ...] = (
    IIIFProvider(
        key="Vaticana",
        label="Vaticana (BAV)",
        aliases=("vaticana", "vaticana (bav)", "vatican"),
        resolver_cls=VaticanResolver,
        search_strategy="vatican",
        search_mode="fallback",
        not_found_hint=(
            "Verifica la segnatura. Prova formati come 'Urb.lat.1779' "
            "o inserisci solo il numero (es. '1223')."
        ),
        placeholder="es. Urb.lat.1779",
        sort_order=10,
    ),
    IIIFProvider(
        key="Gallica",
        label="Gallica (BnF)",
        aliases=("gallica", "gallica (bnf)", "bnf"),
        resolver_cls=GallicaResolver,
        search_strategy="gallica",
        search_mode="search_first",
        filters=(_GALLICA_FILTER,),
        not_found_hint="Verifica l'ID ARK, l'URL o la ricerca testuale.",
        placeholder="es. btv1b84260335",
        sort_order=20,
    ),
    IIIFProvider(
        key="Institut de France",
        label="Institut de France (Bibnum)",
        aliases=("institut de france", "institut de france (bibnum)", "institut", "bibnum"),
        resolver_cls=InstitutResolver,
        search_strategy="institut",
        search_mode="fallback",
        not_found_hint="Verifica la segnatura. Usa ID numerico (es. '17837'), URL viewer o una ricerca testuale.",
        placeholder="es. 17837",
        sort_order=30,
    ),
    IIIFProvider(
        key="Bodleian",
        label="Bodleian (Oxford)",
        aliases=("bodleian", "bodleian (oxford)", "oxford"),
        resolver_cls=OxfordResolver,
        search_strategy="bodleian",
        not_found_hint="Verifica l'UUID o incolla un URL Digital Bodleian valido.",
        placeholder="es. 080f88f5-7586-4b8a-8064-63ab3495393c",
        sort_order=40,
    ),
    IIIFProvider(
        key="Heidelberg",
        label="Universitaetsbibliothek Heidelberg",
        aliases=("heidelberg", "universitaetsbibliothek heidelberg", "universitätsbibliothek heidelberg"),
        resolver_cls=HeidelbergResolver,
        search_strategy="heidelberg",
        search_mode="fallback",
        not_found_hint=(
            "Per ora la ricerca libera Heidelberg puo richiedere il browser del catalogo. "
            "Apri la ricerca Heidelberg, poi incolla qui ID o URL del record."
        ),
        placeholder="es. cpg123",
        sort_order=50,
        metadata={
            "browser_search_url": (
                "https://www.ub.uni-heidelberg.de/cgi-bin/search.cgi?query={query}&q=homepage&sprache=ger&wo=w"
            ),
            "browser_search_label": "Apri ricerca Heidelberg nel browser",
            "helper_text": "Ricerca libera variabile: usa ID/URL, oppure apri Heidelberg nel browser e incollali qui.",
        },
    ),
    IIIFProvider(
        key="Cambridge",
        label="Cambridge University Digital Library",
        aliases=("cambridge", "cambridge university digital library", "cudl"),
        resolver_cls=CambridgeResolver,
        search_strategy="cambridge",
        search_mode="fallback",
        not_found_hint=(
            "Per ora la ricerca libera richiede il browser CUDL. "
            "Apri la ricerca Cambridge, poi incolla qui signature o URL del record."
        ),
        placeholder="es. MS-ADD-03996",
        sort_order=60,
        metadata={
            "browser_search_url": "https://cudl.lib.cam.ac.uk/search?keyword={query}",
            "browser_search_label": "Apri ricerca Cambridge nel browser",
            "helper_text": "Ricerca libera limitata: usa signature/URL, oppure apri CUDL nel browser e incollali qui.",
        },
    ),
    IIIFProvider(
        key="e-codices",
        label="e-codices",
        aliases=("e-codices", "ecodices"),
        resolver_cls=EcodicesResolver,
        search_strategy="ecodices",
        not_found_hint="Incolla un URL e-codices o un ID composto tipo 'csg-0001'.",
        placeholder="es. csg-0001",
        sort_order=70,
    ),
    IIIFProvider(
        key="Harvard",
        label="Harvard University",
        aliases=("harvard", "harvard university"),
        resolver_cls=HarvardResolver,
        search_strategy="harvard",
        search_mode="fallback",
        not_found_hint="Incolla un URL Harvard IIIF/Hollis con DRS ID.",
        placeholder="es. https://iiif.lib.harvard.edu/manifests/view/drs:12345678",
        sort_order=80,
    ),
    IIIFProvider(
        key="Library of Congress",
        label="Library of Congress",
        aliases=("library of congress", "loc"),
        resolver_cls=LOCResolver,
        search_strategy="loc",
        search_mode="fallback",
        not_found_hint="Incolla un URL loc.gov/item/... valido.",
        placeholder="es. https://www.loc.gov/item/2021668145/",
        sort_order=90,
    ),
    IIIFProvider(
        key="Archive.org",
        label="Internet Archive",
        aliases=("archive.org", "internet archive", "archive"),
        resolver_cls=ArchiveOrgResolver,
        search_strategy="archive_org",
        search_mode="search_first",
        not_found_hint="Incolla un URL archive.org/details/... o un manifest iiif.archive.org valido.",
        placeholder="es. https://archive.org/details/b29000427_0001",
        sort_order=95,
    ),
    IIIFProvider(
        key="Unknown",
        label="Altro / URL Diretto",
        aliases=("unknown", "generic", "altro / url diretto"),
        resolver_cls=GenericResolver,
        not_found_hint="Incolla un URL diretto a un manifest IIIF.",
        placeholder="es. https://example.org/manifest.json",
        sort_order=999,
    ),
)

_PROVIDER_BY_KEY = {provider.key: provider for provider in PROVIDERS}


def iter_providers(*, include_generic: bool = True, ui_only: bool = False) -> list[IIIFProvider]:
    """Return provider descriptors in stable UI/CLI order."""
    providers = sorted(PROVIDERS, key=lambda provider: (provider.sort_order, provider.label.lower()))
    if not include_generic:
        providers = [provider for provider in providers if provider.key != "Unknown"]
    if ui_only:
        providers = [provider for provider in providers if provider.include_in_ui]
    return providers


def get_provider(value: str | None, fallback: str = "Vaticana") -> IIIFProvider:
    """Resolve a provider from canonical values, labels, or aliases."""
    text = str(value or "").strip()
    if not text:
        return _PROVIDER_BY_KEY.get(fallback, _PROVIDER_BY_KEY["Unknown"])
    if text in _PROVIDER_BY_KEY:
        return _PROVIDER_BY_KEY[text]

    lowered = text.lower()
    for provider in PROVIDERS:
        if lowered == provider.label.lower():
            return provider
        if lowered in provider.aliases:
            return provider
    return _PROVIDER_BY_KEY.get(fallback, _PROVIDER_BY_KEY["Unknown"])


def is_known_provider(value: str | None) -> bool:
    """Return True when the supplied value maps to an explicit provider/alias."""
    text = str(value or "").strip()
    if not text:
        return False
    provider = get_provider(text, fallback="Unknown")
    if text == provider.key or text.lower() == provider.label.lower():
        return True
    return text.lower() in provider.aliases


def provider_library_options() -> list[tuple[str, str]]:
    """Build Discovery/Settings select options from provider metadata."""
    return [(provider.label, provider.key) for provider in iter_providers(ui_only=True)]


def normalize_provider_value(value: str | None, fallback: str = "Vaticana") -> str:
    """Normalize incoming provider names to canonical library values."""
    return get_provider(value, fallback=fallback).key


def resolve_with_provider(value: str, *, include_generic: bool = True) -> tuple[str | None, str | None, IIIFProvider]:
    """Resolve user input through the shared provider registry."""
    for provider in iter_providers(include_generic=include_generic):
        try:
            resolver = provider.resolver()
            if not resolver.can_resolve(value):
                continue
            manifest_url, doc_id = resolver.get_manifest_url(value)
        except Exception:
            logger.debug("Resolver failed during shared resolution for provider %s", provider.key, exc_info=True)
            continue
        if manifest_url:
            return manifest_url, doc_id, provider
    return None, None, _PROVIDER_BY_KEY["Unknown"]


__all__ = [
    "IIIFProvider",
    "PROVIDERS",
    "ProviderFilter",
    "ProviderFilterOption",
    "get_provider",
    "is_known_provider",
    "iter_providers",
    "normalize_provider_value",
    "provider_library_options",
    "resolve_with_provider",
]
