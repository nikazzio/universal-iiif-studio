from __future__ import annotations

from pathlib import Path

from universal_iiif_core.config_manager import ConfigManager
from universal_iiif_core.pdf_profiles import (
    resolve_effective_profile,
    set_default_profile,
    set_document_override,
    set_global_profile,
)


def _cm(tmp_path: Path) -> ConfigManager:
    cfg = tmp_path / "config.json"
    return ConfigManager.load(path=cfg)


def test_default_profile_resolution_is_balanced(tmp_path: Path):
    """Balanced is the fallback when no global/doc overrides are set."""
    cm = _cm(tmp_path)
    name, profile = resolve_effective_profile(cm, doc_id="DOC1", library="Gallica")

    assert name == "balanced"
    assert profile["compression"] == "Standard"
    assert profile["image_source_mode"] == "local_balanced"


def test_global_custom_profile_can_be_default(tmp_path: Path):
    """A global custom profile can be promoted as default and resolved."""
    cm = _cm(tmp_path)
    set_global_profile(
        cm,
        name="research_highres",
        payload={
            "label": "Research High-Res",
            "compression": "High-Res",
            "image_source_mode": "remote_highres_temp",
            "jpeg_quality": 93,
        },
    )
    set_default_profile(cm, "research_highres")

    name, profile = resolve_effective_profile(cm, doc_id="DOC2", library="Vaticana")
    assert name == "research_highres"
    assert profile["image_source_mode"] == "remote_highres_temp"
    assert profile["jpeg_quality"] == 93


def test_document_override_wins_over_global_default(tmp_path: Path):
    """A document-level custom profile takes precedence over global default."""
    cm = _cm(tmp_path)
    set_document_override(
        cm,
        doc_id="DOC3",
        library="Gallica",
        custom_payload={
            "label": "Doc 3",
            "compression": "Light",
            "image_source_mode": "local_balanced",
            "jpeg_quality": 60,
        },
    )

    name, profile = resolve_effective_profile(cm, doc_id="DOC3", library="Gallica")
    assert name.startswith("doc-custom:")
    assert profile["compression"] == "Light"
    assert profile["jpeg_quality"] == 60
