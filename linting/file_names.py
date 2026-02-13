#!/usr/bin/env python
"""Enforce repository file naming conventions.

Python:
  - snake_case filenames for tracked .py files under src/, tests/, linting/

Shell:
  - kebab-case filenames for tracked .sh files under scripts/
"""

from __future__ import annotations

import re
import sys
import shutil
from pathlib import Path
import subprocess  # noqa: S404

ROOT = Path(__file__).resolve().parents[1]

PY_ALLOWED = {"__init__.py", "__main__.py"}
PY_RE = re.compile(r"^[a-z][a-z0-9_]*\.py$")

SH_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.sh$")


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
    violations: list[str] = []

    for rel in _git_tracked_paths():
        p = Path(rel)
        name = p.name

        if rel.startswith(("src/", "tests/", "linting/")) and name.endswith(".py"):
            if name in PY_ALLOWED:
                continue
            if not PY_RE.match(name):
                violations.append(f"  {rel} (expected snake_case .py filename)")
            continue

        if rel.startswith("scripts/") and name.endswith(".sh") and not SH_RE.match(name):
            violations.append(f"  {rel} (expected kebab-case .sh filename)")

    if violations:
        print("File naming violations:", file=sys.stderr)
        for v in violations:
            print(v, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
