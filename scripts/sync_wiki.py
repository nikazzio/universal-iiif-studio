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

MARKDOWN_LINK_RE = re.compile(r"(!?\[[^\]]*]\()([^)]+)(\))")


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


def _split_target(target: str) -> tuple[str, str]:
    if "#" in target:
        base, anchor = target.split("#", 1)
        return base, f"#{anchor}"
    return target, ""


def _is_external_link(target: str) -> bool:
    lowered = target.lower()
    return lowered.startswith(("http://", "https://", "mailto:", "#"))


def _repo_relative_path(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _rewrite_markdown_links(
    *,
    content: str,
    src: Path,
    source_root: Path,
    repo_root: Path,
    repo_slug: str,
    repo_ref: str,
) -> tuple[str, list[str]]:
    failures: list[str] = []

    def replace(match: re.Match[str]) -> str:
        prefix, target, suffix = match.groups()
        if _is_external_link(target):
            return match.group(0)

        base, anchor = _split_target(target.strip())
        if not base:
            return match.group(0)

        resolved = (src.parent / base).resolve()
        if not resolved.exists():
            failures.append(f"{src}: link target does not exist: {target}")
            return match.group(0)

        try:
            wiki_rel = resolved.relative_to(source_root)
            new_base = os.path.relpath(wiki_rel.as_posix(), start=src.parent.relative_to(source_root).as_posix())
            return f"{prefix}{new_base}{anchor}{suffix}"
        except ValueError:
            try:
                repo_rel = _repo_relative_path(resolved, repo_root)
            except ValueError:
                failures.append(f"{src}: link target is outside repository root: {target}")
                return match.group(0)
            absolute = f"https://github.com/{repo_slug}/blob/{repo_ref}/{repo_rel}{anchor}"
            return f"{prefix}{absolute}{suffix}"

    rewritten = MARKDOWN_LINK_RE.sub(replace, content)
    return rewritten, failures


def _sync_files(
    *,
    source_root: Path,
    wiki_dir: Path,
    repo_root: Path,
    repo_slug: str,
    repo_ref: str,
    prune: bool,
) -> tuple[int, int]:
    copied = 0
    removed = 0
    keep_rel_paths: set[Path] = set()
    failures: list[str] = []

    for src in _iter_source_files(source_root):
        rel = src.relative_to(source_root)
        keep_rel_paths.add(rel)
        dst = wiki_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)

        if src.suffix.lower() == ".md":
            content = src.read_text(encoding="utf-8")
            rendered, rewrite_failures = _rewrite_markdown_links(
                content=content,
                src=src,
                source_root=source_root,
                repo_root=repo_root,
                repo_slug=repo_slug,
                repo_ref=repo_ref,
            )
            failures.extend(rewrite_failures)
            current = dst.read_text(encoding="utf-8") if dst.exists() else None
            if current != rendered:
                dst.write_text(rendered, encoding="utf-8")
                copied += 1
            continue

        if not dst.exists() or src.read_bytes() != dst.read_bytes():
            shutil.copy2(src, dst)
            copied += 1

    if failures:
        details = "\n".join(f"- {item}" for item in failures)
        raise SystemExit(f"Wiki source validation failed:\n{details}")

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
        "--repo-ref",
        default="main",
        help="Repository ref used when rewriting absolute GitHub links.",
    )
    parser.add_argument(
        "--commit-message",
        default="docs(wiki): sync from docs/wiki",
        help="Commit message used when changes are detected.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run synchronization checks without creating commits or pushing.",
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


def _validate_source_root(source_root: Path) -> None:
    if not source_root.exists():
        raise SystemExit(f"source-root not found: {source_root}")
    if not source_root.is_dir():
        raise SystemExit(f"source-root must be a directory: {source_root}")
    if not (source_root / "Home.md").exists():
        raise SystemExit(f"Home.md is required in source-root: {source_root / 'Home.md'}")


def _resolve_repo_slug(explicit_repo: str | None) -> str:
    repo_slug = (explicit_repo or _detect_repo_slug() or "").strip()
    if not repo_slug:
        raise SystemExit("Unable to determine repository slug. Pass --repo owner/repo.")
    return repo_slug


def _print_run_context(*, repo_slug: str, source_root: Path, wiki_dir: Path, repo_ref: str) -> None:
    print(f"Repository: {repo_slug}")
    print(f"Repository ref: {repo_ref}")
    print(f"Source root: {source_root}")
    print(f"Wiki dir: {wiki_dir}")


def _clone_or_update_wiki_or_exit(*, remote_url: str, wiki_dir: Path) -> None:
    try:
        _clone_or_update_wiki(remote_url=remote_url, wiki_dir=wiki_dir)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        msg = "Failed to clone or update wiki repository. Verify that the wiki is enabled and credentials are valid."
        if stderr:
            msg = f"{msg}\n{stderr}"
        raise SystemExit(msg) from exc


def _handle_dry_run(*, wiki_dir: Path, copied: int, removed: int, push_requested: bool) -> int:
    has_changes = _has_changes(wiki_dir)
    print("DRY RUN: no commit, no push.")
    print(f"Files copied: {copied}, files removed: {removed}")
    if has_changes:
        print("DRY RUN: wiki changes detected.")
    else:
        print("DRY RUN: wiki already up to date.")
    if push_requested:
        print("DRY RUN: --push ignored.")
    return 0


def _commit_and_maybe_push(*, args: argparse.Namespace, wiki_dir: Path, copied: int, removed: int) -> int:
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
        return 0

    print("Push skipped. Re-run with --push to publish changes.")
    return 0


def main() -> int:
    """Run wiki synchronization from local source files to the wiki git repository."""
    args = _parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    source_root = (repo_root / args.source_root).resolve()
    wiki_dir = Path(args.wiki_dir).resolve()
    _validate_source_root(source_root)
    repo_slug = _resolve_repo_slug(args.repo)
    _print_run_context(repo_slug=repo_slug, source_root=source_root, wiki_dir=wiki_dir, repo_ref=args.repo_ref)

    token = os.getenv("GITHUB_TOKEN")
    remote_url = _build_wiki_remote(repo_slug, token)
    _clone_or_update_wiki_or_exit(remote_url=remote_url, wiki_dir=wiki_dir)

    copied, removed = _sync_files(
        source_root=source_root,
        wiki_dir=wiki_dir,
        repo_root=repo_root,
        repo_slug=repo_slug,
        repo_ref=str(args.repo_ref),
        prune=bool(args.prune),
    )

    if args.dry_run:
        return _handle_dry_run(wiki_dir=wiki_dir, copied=copied, removed=removed, push_requested=args.push)

    return _commit_and_maybe_push(args=args, wiki_dir=wiki_dir, copied=copied, removed=removed)


if __name__ == "__main__":
    raise SystemExit(main())
