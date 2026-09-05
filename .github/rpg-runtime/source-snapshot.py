#!/usr/bin/env python3
"""Create one offline, container-readable snapshot of a PFB worktree."""

from __future__ import annotations

import argparse
import shutil
import stat
import subprocess
from pathlib import Path


def git(source: Path, *arguments: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(source), *arguments])


def snapshot(source: Path, output: Path) -> None:
    source = source.resolve(strict=True)
    if output.exists() or source == output.resolve():
        raise ValueError("MKXP_SOURCE_SNAPSHOT_OUTPUT_INVALID")
    # file:// uses only the existing local object store. A depth-one, no-checkout
    # clone copies the exact commit and no history; unlike a worktree .git file
    # or shared clone, it has no host-only gitdir/alternates dependency.
    subprocess.run([
        "git", "clone", "--quiet", "--no-checkout", "--depth=1", "--no-tags",
        "--single-branch", source.as_uri(), str(output),
    ], check=True)
    if git(output, "rev-parse", "HEAD") != git(source, "rev-parse", "HEAD"):
        raise ValueError("MKXP_SOURCE_SNAPSHOT_IDENTITY_INVALID")
    git(output, "read-tree", "HEAD")
    gitlinks = set()
    for entry in git(source, "ls-files", "--stage", "-z").split(b"\0"):
        if entry.startswith(b"160000 "):
            gitlinks.add(entry.split(b"\t", 1)[1])
    paths = set(git(source, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0"))
    for raw in sorted(paths - {b""}):
        relative = raw.decode("utf-8")
        original = source / relative
        target = output / relative
        if raw in gitlinks:
            if Path(git(original, "rev-parse", "--show-toplevel").decode().strip()).resolve() != original.resolve():
                raise ValueError("MKXP_SOURCE_SUBMODULE_UNAVAILABLE")
            snapshot(original, target)
            continue
        try:
            info = original.lstat()
        except FileNotFoundError:
            continue  # Preserve a tracked deletion in the working tree.
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)):
            raise ValueError("MKXP_SOURCE_FILE_INVALID")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target, follow_symlinks=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    snapshot(args.source, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
