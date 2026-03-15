from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from universal_iiif_core.providers import IIIFProvider
from universal_iiif_core.resolvers.models import SearchResult

ResolutionStatus = Literal["manifest", "results", "not_found"]


@dataclass
class ProviderResolution:
    """Normalized discovery outcome for a selected provider."""

    provider: IIIFProvider
    status: ResolutionStatus
    manifest_url: str | None = None
    doc_id: str | None = None
    results: list[SearchResult] = field(default_factory=list)
    not_found_hint: str = ""

