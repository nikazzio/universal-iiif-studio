#!/usr/bin/env python
"""Utility to reset the user-data directories managed by the project."""

from __future__ import annotations

import argparse
import shutil
from collections.abc import Iterable
from pathlib import Path

from universal_iiif_core.config_manager import get_config_manager


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the cleanup helper."""
    parser = argparse.ArgumentParser(description="Reset downloads, temp and log folders managed by the project.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which folders would be removed without touching them",
    )
    parser.add_argument(
        "--include-data-local",
        action="store_true",
        help="Also remove the entire data/local tree (use with caution)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt",
    )
    parser.add_argument(
        "--extra",
        nargs="*",
        default=[],
        metavar="PATH",
        help="Additional directories to wipe (absolute or relative to project root)",
    )
    return parser.parse_args()


def ensure_safe_path(path: Path) -> Path:
    """Resolve a path safely and prevent root deletion."""
    resolved = path.expanduser().resolve()
    if resolved == resolved.anchor:
        raise ValueError("Refusing to delete the filesystem root")
    return resolved


def collect_targets(config, include_data_local: bool, extra: Iterable[str]) -> list[tuple[str, Path]]:
    """Gather the directories that the script will delete."""
    root = Path.cwd().resolve()
    samples = [
        ("root downloads", root / "downloads"),
        ("configured downloads", config.get_downloads_dir()),
        ("temp images", config.get_temp_dir()),
        ("logs", config.get_logs_dir()),
    ]
    if include_data_local:
        samples.append(("data/local tree", root / "data" / "local"))

    extras = [("extra", Path(item)) for item in extra if item]
    all_targets: list[tuple[str, Path]] = []
    seen: set[Path] = set()

    for name, candidate in [*samples, *extras]:
        try:
            resolved = ensure_safe_path(candidate)
        except ValueError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        all_targets.append((name, resolved))
    return all_targets


def summarize_targets(targets: list[tuple[str, Path]]) -> str:
    """Return a printable summary of the targets."""
    lines = [f"  - {name}: {path}" for name, path in targets]
    return "\n".join(lines)


def confirm_run() -> bool:
    """Ask the user for a yes/no confirmation."""
    answer = input("Proceed with deletion? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def remove_path(path: Path) -> None:
    """Remove a file or directory if it exists."""
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def main() -> int:
    """Entry point: orchestrate target collection and removal."""
    args = parse_args()
    config = get_config_manager()
    targets = collect_targets(config, args.include_data_local, args.extra)

    if not targets:
        print("No user-data directories detected.")
        return 0

    print("User-data cleanup targets:")
    print(summarize_targets(targets))

    if args.dry_run:
        print("Dry run: nothing changed.")
        return 0

    if not args.yes and not confirm_run():
        print("Aborted by user.")
        return 1

    failures = []
    for _name, path in targets:
        try:
            remove_path(path)
        except OSError as exc:
            failures.append((path, exc))

    if failures:
        print("Some targets could not be cleared:")
        for path, exc in failures:
            print(f"  {path}: {exc}")
        return 1

    print("Cleanup complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
