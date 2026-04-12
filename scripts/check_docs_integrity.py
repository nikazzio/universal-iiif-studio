#!/usr/bin/env python3
"""Validate key documentation invariants used by CI."""

from __future__ import annotations

from pathlib import Path


class ValidationError(RuntimeError):
    """Raised when documentation integrity checks fail."""


REQUIRED_FILES = [
    Path("README.md"),
    Path("docs/index.md"),
    Path("docs/DOCUMENTAZIONE.md"),
    Path("docs/ARCHITECTURE.md"),
    Path("docs/CONFIG_REFERENCE.md"),
    Path("docs/WIKI_MAINTENANCE.md"),
    Path("docs/wiki/Home.md"),
]

REQUIRED_README_LINKS = [
    "(docs/index.md)",
    "(docs/DOCUMENTAZIONE.md)",
    "(docs/ARCHITECTURE.md)",
    "(docs/CONFIG_REFERENCE.md)",
]

CRITICAL_CONFIG_KEYS = [
    "settings.network.global.max_concurrent_download_jobs",
    "settings.network.global.connect_timeout_s",
    "settings.network.global.read_timeout_s",
    "settings.network.global.transport_retries",
    "settings.network.global.per_host_concurrency",
    "settings.images.download_strategy_mode",
    "settings.images.stitch_mode_default",
    "settings.pdf.prefer_native_pdf",
    "settings.pdf.create_pdf_from_images",
    "settings.storage.partial_promotion_mode",
    "settings.viewer.mirador.require_complete_local_images",
]

ARCHITECTURE_MARKERS = [
    "studio_ui/routes/_studio/",
    "studio_ui/components/settings/panes/",
    "studio_ui/components/studio/export/",
]


def _must_exist(path: Path, failures: list[str]) -> None:
    if not path.exists():
        failures.append(f"Missing required documentation file: {path}")


def main() -> int:
    """Run documentation integrity validation."""
    failures: list[str] = []

    for path in REQUIRED_FILES:
        _must_exist(path, failures)

    readme_text = Path("README.md").read_text(encoding="utf-8")
    for link in REQUIRED_README_LINKS:
        if link not in readme_text:
            failures.append(f"README.md is missing required documentation link: {link}")

    config_reference = Path("docs/CONFIG_REFERENCE.md").read_text(encoding="utf-8")
    for key in CRITICAL_CONFIG_KEYS:
        if key not in config_reference:
            failures.append(f"docs/CONFIG_REFERENCE.md is missing critical key: {key}")

    architecture = Path("docs/ARCHITECTURE.md").read_text(encoding="utf-8")
    for marker in ARCHITECTURE_MARKERS:
        if marker not in architecture:
            failures.append(f"docs/ARCHITECTURE.md is missing current package marker: {marker}")

    if failures:
        details = "\n".join(f"- {item}" for item in failures)
        raise ValidationError(f"Documentation integrity check failed:\n{details}")

    print("Documentation integrity check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
