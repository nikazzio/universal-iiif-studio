"""Small helpers for serving IIIF manifests.

These keep the manifest rewriting logic isolated and testable so the
API route remains concise and easy to read.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from universal_iiif_core.iiif_logic import rewrite_image_urls, total_canvases

__all__ = ["load_manifest", "rewrite_image_urls", "total_canvases"]


def load_manifest(path: Path) -> dict[str, Any]:
    """Load a JSON manifest from disk.

    Args:
        path: Path to the manifest file.

    Returns:
        Parsed manifest as a dictionary.
    """
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)
