"""Search subpackage — per-provider search implementations.

Re-exports every public search function so that existing imports from
``resolvers.discovery`` (which re-exports from here) continue to work.
"""

from __future__ import annotations

from .archive_org import archive_manifest_is_usable, search_archive_org
from .bodleian import search_bodleian
from .cambridge import search_cambridge
from .ecodices import search_ecodices
from .estense import search_estense
from .gallica import search_gallica, search_gallica_by_id
from .harvard import search_harvard
from .heidelberg import search_heidelberg
from .institut import search_institut
from .internetculturale import search_internetculturale
from .loc import search_loc
from .vatican import search_vatican

__all__ = [
    "archive_manifest_is_usable",
    "search_archive_org",
    "search_bodleian",
    "search_cambridge",
    "search_ecodices",
    "search_estense",
    "search_gallica",
    "search_gallica_by_id",
    "search_harvard",
    "search_heidelberg",
    "search_institut",
    "search_internetculturale",
    "search_loc",
    "search_vatican",
]
