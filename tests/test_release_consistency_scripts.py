from __future__ import annotations

import pytest

from scripts import check_changelog_policy, check_release_consistency


def test_changelog_policy_requires_semantic_release_insertion_flag(tmp_path, monkeypatch):
    """CHANGELOG policy should fail fast when the insertion flag is missing."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        (
            "# Changelog\n\n"
            "## [v0.1.0] - 2026-03-11\n\n"
            "### Added\n\n- None.\n\n"
            "### Changed\n\n- None.\n\n"
            "### Fixed\n\n- None.\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(check_changelog_policy, "CHANGELOG_PATH", changelog)

    with pytest.raises(check_changelog_policy.ValidationError, match="insertion flag"):
        check_changelog_policy.main()


def test_changelog_policy_accepts_python_semantic_release_format(tmp_path, monkeypatch):
    """CHANGELOG policy should accept the default python-semantic-release v10 heading and commit links."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        (
            "# Changelog\n\n"
            "<!-- version list -->\n\n"
            "## v0.22.4 (2026-03-11)\n\n"
            "### Bug Fixes\n\n"
            "- Preserve changelog automation ([`74b4875`](https://example.invalid/commit/74b4875))\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(check_changelog_policy, "CHANGELOG_PATH", changelog)

    assert check_changelog_policy.main() == 0


def test_changelog_policy_accepts_historical_release_with_pr_and_commit_links(tmp_path, monkeypatch):
    """Historical auto-generated bullets may include both PR links and commit links."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        (
            "# Changelog\n\n"
            "<!-- version list -->\n\n"
            "## v0.10.2 (2026-02-23)\n\n"
            "### Bug Fixes\n\n"
            "- Repair toast dismiss behavior ([#19](https://example.invalid/pull/19), "
            "[`2d4579a`](https://example.invalid/commit/2d4579a))\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(check_changelog_policy, "CHANGELOG_PATH", changelog)

    assert check_changelog_policy.main() == 0


def test_changelog_policy_accepts_sparse_historical_release_without_sections(tmp_path, monkeypatch):
    """Some old releases only have a heading and detailed changes footer."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        (
            "# Changelog\n\n"
            "<!-- version list -->\n\n"
            "## v0.14.0 (2026-03-02)\n\n"
            "_This release is published under the MIT License._\n\n"
            "---\n\n"
            "**Detailed Changes**: [v0.13.4...v0.14.0](https://example.invalid/compare)\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(check_changelog_policy, "CHANGELOG_PATH", changelog)

    assert check_changelog_policy.main() == 0


def test_release_consistency_accepts_semantic_release_v10_config(tmp_path, monkeypatch):
    """Release consistency should accept synchronized versions and v10 changelog config."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "universal-iiif"
version = "0.22.3"

[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
version_variables = ["src/universal_iiif_core/__init__.py:__version__"]

[tool.semantic_release.changelog]
mode = "update"
insertion_flag = "<!-- version list -->"

[tool.semantic_release.changelog.default_templates]
changelog_file = "CHANGELOG.md"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    init_file = tmp_path / "src" / "universal_iiif_core" / "__init__.py"
    init_file.parent.mkdir(parents=True)
    init_file.write_text('__version__ = "0.22.3"\n', encoding="utf-8")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n<!-- version list -->\n", encoding="utf-8")
    workflow = tmp_path / ".github" / "workflows" / "release.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        (
            "name: Release\n"
            "jobs:\n"
            "  semantic-release:\n"
            "    steps:\n"
            '      - run: pip install "python-semantic-release>=10.5.3,<11"\n'
            "      - run: semantic-release version --push\n"
            "      - run: semantic-release publish\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(check_release_consistency, "PYPROJECT_PATH", pyproject)
    monkeypatch.setattr(check_release_consistency, "RUNTIME_VERSION_PATH", init_file)
    monkeypatch.setattr(check_release_consistency, "CHANGELOG_PATH", changelog)
    monkeypatch.setattr(check_release_consistency, "RELEASE_WORKFLOW_PATH", workflow)

    assert check_release_consistency.main() == 0


def test_release_consistency_rejects_version_mismatch(tmp_path, monkeypatch):
    """Release consistency should catch drift between pyproject and package version."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "universal-iiif"
version = "0.16.0"

[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
version_variables = ["src/universal_iiif_core/__init__.py:__version__"]

[tool.semantic_release.changelog]
mode = "update"
insertion_flag = "<!-- version list -->"

[tool.semantic_release.changelog.default_templates]
changelog_file = "CHANGELOG.md"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    init_file = tmp_path / "src" / "universal_iiif_core" / "__init__.py"
    init_file.parent.mkdir(parents=True)
    init_file.write_text('__version__ = "0.22.3"\n', encoding="utf-8")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n<!-- version list -->\n", encoding="utf-8")
    workflow = tmp_path / ".github" / "workflows" / "release.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        (
            "name: Release\n"
            "jobs:\n"
            "  semantic-release:\n"
            "    steps:\n"
            '      - run: pip install "python-semantic-release>=10.5.3,<11"\n'
            "      - run: semantic-release version --push\n"
            "      - run: semantic-release publish\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(check_release_consistency, "PYPROJECT_PATH", pyproject)
    monkeypatch.setattr(check_release_consistency, "RUNTIME_VERSION_PATH", init_file)
    monkeypatch.setattr(check_release_consistency, "CHANGELOG_PATH", changelog)
    monkeypatch.setattr(check_release_consistency, "RELEASE_WORKFLOW_PATH", workflow)

    with pytest.raises(check_release_consistency.ValidationError, match="Version mismatch"):
        check_release_consistency.main()
