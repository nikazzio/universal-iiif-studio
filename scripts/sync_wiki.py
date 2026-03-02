#!/usr/bin/env python3
"""Sync GitHub Wiki content from local docs/wiki sources.

Usage examples:
  python scripts/sync_wiki.py --repo owner/repo
  python scripts/sync_wiki.py --repo owner/repo --push
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path


def _run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        capture_output=True,
    )


def _detect_repo_slug() -> str | None:
    try:
        remote = _run(["git", "config", "--get", "remote.origin.url"], check=False).stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    if not remote:
        return None

    https_match = re.search(r"github\.com[:/](?P<slug>[^/]+/[^/.]+)(?:\.git)?$", remote)
    if https_match:
        return https_match.group("slug")
    return None


def _build_wiki_remote(repo_slug: str, token: str | None) -> str:
    if token:
        return f"https://x-access-token:{token}@github.com/{repo_slug}.wiki.git"
    return f"https://github.com/{repo_slug}.wiki.git"


def _clone_or_update_wiki(*, remote_url: str, wiki_dir: Path) -> None:
    if (wiki_dir / ".git").exists():
        _run(["git", "fetch", "--all"], cwd=wiki_dir)
        branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=wiki_dir).stdout.strip()
        _run(["git", "pull", "--ff-only", "origin", branch], cwd=wiki_dir)
        return

    wiki_dir.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "clone", remote_url, str(wiki_dir)])


def _iter_source_files(source_root: Path) -> list[Path]:
    return sorted(path for path in source_root.rglob("*") if path.is_file())


def _sync_files(*, source_root: Path, wiki_dir: Path, prune: bool) -> tuple[int, int]:
    copied = 0
    removed = 0
    keep_rel_paths: set[Path] = set()

    for src in _iter_source_files(source_root):
        rel = src.relative_to(source_root)
        keep_rel_paths.add(rel)
        dst = wiki_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists() or src.read_bytes() != dst.read_bytes():
            shutil.copy2(src, dst)
            copied += 1

    if prune:
        for path in sorted(wiki_dir.rglob("*"), reverse=True):
            rel = path.relative_to(wiki_dir)
            if rel.parts and rel.parts[0] == ".git":
                continue
            if path.is_file() and rel not in keep_rel_paths:
                path.unlink()
                removed += 1
            if path.is_dir():
                with_context = [p for p in path.iterdir() if p.name != ".git"]
                if not with_context:
                    path.rmdir()

    return copied, removed


def _configure_git_identity(*, wiki_dir: Path, name: str, email: str) -> None:
    _run(["git", "config", "user.name", name], cwd=wiki_dir)
    _run(["git", "config", "user.email", email], cwd=wiki_dir)


def _has_changes(wiki_dir: Path) -> bool:
    status = _run(["git", "status", "--porcelain"], cwd=wiki_dir).stdout.strip()
    return bool(status)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync docs/wiki to GitHub wiki repository.")
    parser.add_argument("--repo", help="GitHub repository slug in 'owner/repo' format.")
    parser.add_argument("--source-root", default="docs/wiki", help="Source docs directory to mirror.")
    parser.add_argument(
        "--wiki-dir",
        default=".cache/wiki-sync",
        help="Local clone directory for the wiki repo.",
    )
    parser.add_argument(
        "--commit-message",
        default="docs(wiki): sync from docs/wiki",
        help="Commit message used when changes are detected.",
    )
    parser.add_argument("--push", action="store_true", help="Push commit to remote wiki repository.")
    parser.add_argument(
        "--prune",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Delete wiki files not present in source-root (default: true).",
    )
    parser.add_argument(
        "--git-user-name",
        default=os.getenv("WIKI_GIT_USER_NAME", "github-actions[bot]"),
        help="Git author name for sync commits.",
    )
    parser.add_argument(
        "--git-user-email",
        default=os.getenv("WIKI_GIT_USER_EMAIL", "41898282+github-actions[bot]@users.noreply.github.com"),
        help="Git author email for sync commits.",
    )
    return parser.parse_args()


def main() -> int:
    """Run wiki synchronization from local source files to the wiki git repository."""
    args = _parse_args()

    source_root = Path(args.source_root).resolve()
    wiki_dir = Path(args.wiki_dir).resolve()

    if not source_root.exists():
        raise SystemExit(f"source-root not found: {source_root}")
    if not source_root.is_dir():
        raise SystemExit(f"source-root must be a directory: {source_root}")
    if not (source_root / "Home.md").exists():
        raise SystemExit(f"Home.md is required in source-root: {source_root / 'Home.md'}")

    repo_slug = (args.repo or _detect_repo_slug() or "").strip()
    if not repo_slug:
        raise SystemExit("Unable to determine repository slug. Pass --repo owner/repo.")

    token = os.getenv("GITHUB_TOKEN")
    remote_url = _build_wiki_remote(repo_slug, token)

    try:
        _clone_or_update_wiki(remote_url=remote_url, wiki_dir=wiki_dir)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        msg = (
            "Failed to clone or update wiki repository. "
            "Verify that the wiki is enabled and credentials are valid."
        )
        if stderr:
            msg = f"{msg}\n{stderr}"
        raise SystemExit(msg) from exc

    copied, removed = _sync_files(source_root=source_root, wiki_dir=wiki_dir, prune=bool(args.prune))
    _configure_git_identity(wiki_dir=wiki_dir, name=args.git_user_name, email=args.git_user_email)
    _run(["git", "add", "-A"], cwd=wiki_dir)

    if not _has_changes(wiki_dir):
        print("Wiki already up to date.")
        print(f"Files copied: {copied}, files removed: {removed}")
        return 0

    _run(["git", "commit", "-m", args.commit_message], cwd=wiki_dir)
    print("Committed wiki changes.")
    print(f"Files copied: {copied}, files removed: {removed}")

    if args.push:
        branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=wiki_dir).stdout.strip()
        _run(["git", "push", "origin", branch], cwd=wiki_dir)
        print("Pushed wiki changes.")
    else:
        print("Push skipped. Re-run with --push to publish changes.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
