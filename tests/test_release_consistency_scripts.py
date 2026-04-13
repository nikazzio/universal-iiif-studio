from __future__ import annotations

import pytest

from scripts import check_release_consistency


def test_release_consistency_accepts_tag_only_config(tmp_path, monkeypatch):
    """Release consistency should accept tag-only setup (no changelog, no commit)."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "universal-iiif"
version = "0.22.3"

[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
version_variables = ["src/universal_iiif_core/__init__.py:__version__"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    init_file = tmp_path / "src" / "universal_iiif_core" / "__init__.py"
    init_file.parent.mkdir(parents=True)
    init_file.write_text('__version__ = "0.22.3"\n', encoding="utf-8")
    workflow = tmp_path / ".github" / "workflows" / "release.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        (
            "name: Release\n"
            "jobs:\n"
            "  semantic-release:\n"
            "    steps:\n"
            '      - run: pip install "python-semantic-release>=10.5.3,<11"\n'
            "      - run: semantic-release version --no-commit --push\n"
            "      - run: semantic-release publish\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(check_release_consistency, "PYPROJECT_PATH", pyproject)
    monkeypatch.setattr(check_release_consistency, "RUNTIME_VERSION_PATH", init_file)
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
""".strip()
        + "\n",
        encoding="utf-8",
    )
    init_file = tmp_path / "src" / "universal_iiif_core" / "__init__.py"
    init_file.parent.mkdir(parents=True)
    init_file.write_text('__version__ = "0.22.3"\n', encoding="utf-8")
    workflow = tmp_path / ".github" / "workflows" / "release.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        (
            "name: Release\n"
            "jobs:\n"
            "  semantic-release:\n"
            "    steps:\n"
            '      - run: pip install "python-semantic-release>=10.5.3,<11"\n'
            "      - run: semantic-release version --no-commit --push\n"
            "      - run: semantic-release publish\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(check_release_consistency, "PYPROJECT_PATH", pyproject)
    monkeypatch.setattr(check_release_consistency, "RUNTIME_VERSION_PATH", init_file)
    monkeypatch.setattr(check_release_consistency, "RELEASE_WORKFLOW_PATH", workflow)

    with pytest.raises(check_release_consistency.ValidationError, match="Version mismatch"):
        check_release_consistency.main()


def test_release_consistency_rejects_missing_no_commit_flag(tmp_path, monkeypatch):
    """Release workflow must use --no-commit to avoid pushing version bump commits to main."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "universal-iiif"
version = "0.22.3"

[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
version_variables = ["src/universal_iiif_core/__init__.py:__version__"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    init_file = tmp_path / "src" / "universal_iiif_core" / "__init__.py"
    init_file.parent.mkdir(parents=True)
    init_file.write_text('__version__ = "0.22.3"\n', encoding="utf-8")
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
    monkeypatch.setattr(check_release_consistency, "RELEASE_WORKFLOW_PATH", workflow)

    with pytest.raises(check_release_consistency.ValidationError, match="--no-commit"):
        check_release_consistency.main()
