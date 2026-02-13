#!/usr/bin/env python
"""Detect folder shapes that should be flattened or removed.

Policy:
- A directory should not exist solely to wrap a *single* substantive child.
  Examples (violations):
  - one file (+ optional __init__.py / __pycache__)
  - one subdirectory (+ optional __init__.py / __pycache__)

Rationale:
- This repo avoids "one-file folders" and "one-folder wrappers" because they
  add import/path noise without providing structure.

Implementation notes:
- Operates only on git-tracked files to avoid failing due to local caches.
- Ignores `__init__.py` when counting substantive children.
"""

from __future__ import annotations

import sys
import shutil
from pathlib import Path
import subprocess  # noqa: S404

ROOT = Path(__file__).resolve().parents[1]

CHECK_ROOTS = ("src", "tests", "linting")
IGNORE_FILES = {"__init__.py"}
IGNORE_DIRS = {"__pycache__"}
MIN_PATH_PARTS = 2


def _git_tracked_paths() -> list[str]:
    git_bin = shutil.which("git")
    if not git_bin:
        return []
    proc = subprocess.run(  # noqa: S603
        [git_bin, "-C", str(ROOT), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        check=True,
        capture_output=True,
    )
    raw = proc.stdout.decode("utf-8", errors="replace")
    if not raw:
        return []
    parts = raw.split("\0")
    out: list[str] = []
    for rel in parts:
        if not rel:
            continue
        abs_path = ROOT / rel
        if abs_path.is_file():
            out.append(rel)
    return out


def main() -> int:
    children_files: dict[str, set[str]] = {}
    children_dirs: dict[str, set[str]] = {}

    def add_child(parent: str, *, file_child: str | None = None, dir_child: str | None = None) -> None:
        if file_child is not None:
            children_files.setdefault(parent, set()).add(file_child)
        if dir_child is not None:
            children_dirs.setdefault(parent, set()).add(dir_child)

    tracked = _git_tracked_paths()
    for rel in tracked:
        if not rel.startswith(tuple(f"{r}/" for r in CHECK_ROOTS)):
            continue
        parts = rel.split("/")
        if len(parts) < MIN_PATH_PARTS:
            continue

        # Walk parent directories and record the next segment as a direct child.
        for i in range(0, len(parts) - 1):
            parent_dir = "/".join(parts[: i + 1])
            child = parts[i + 1]
            if child in IGNORE_DIRS:
                continue
            if i + 1 == len(parts) - 1:
                add_child(parent_dir, file_child=child)
            else:
                add_child(parent_dir, dir_child=child)

    violations: list[str] = []

    for parent in sorted(set(children_files) | set(children_dirs)):
        # Skip root folders themselves (src/, tests/, linting/)
        if parent in CHECK_ROOTS:
            continue

        files = {f for f in children_files.get(parent, set()) if f not in IGNORE_FILES}
        dirs = {d for d in children_dirs.get(parent, set()) if d not in IGNORE_DIRS}

        total = len(files) + len(dirs)
        if total == 0:
            # Only ignored children (e.g., __init__.py) remain.
            violations.append(f"  {parent}/ has no substantive children — flatten/remove the folder")
            continue
        if total == 1:
            if files:
                only = next(iter(files))
                violations.append(f"  {parent}/ has only {only} — flatten to {parent}.py")
            else:
                only = next(iter(dirs))
                violations.append(f"  {parent}/ only wraps {only}/ — flatten/remove the wrapper folder")

    if violations:
        print("Single-file folder violations:", file=sys.stderr)
        for v in violations:
            print(v, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
