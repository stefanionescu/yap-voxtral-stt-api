#!/usr/bin/env python
"""Detect prefix collisions among Python files in the same directory.

Flags directories under src/ where 2+ .py files share a common prefix
(e.g. user_service.py and user_model.py both start with "user").
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"

MIN_COLLISION = 2
MIN_PREFIX_PARTS = 2


def _get_prefix(filename: str) -> str | None:
    """Extract the first underscore-delimited segment of a filename."""
    stem = Path(filename).stem
    if stem.startswith("_"):
        return None
    parts = stem.split("_")
    if len(parts) < MIN_PREFIX_PARTS:
        return None
    return parts[0]


def main() -> int:
    violations: list[str] = []

    if not SRC_DIR.is_dir():
        return 0

    dirs_seen: set[Path] = set()
    for py_file in sorted(SRC_DIR.rglob("*.py")):
        dirs_seen.add(py_file.parent)

    for directory in sorted(dirs_seen):
        py_files = [f.name for f in directory.iterdir() if f.suffix == ".py" and f.name != "__init__.py"]
        if len(py_files) < MIN_COLLISION:
            continue

        prefix_groups: dict[str, list[str]] = defaultdict(list)
        for name in py_files:
            prefix = _get_prefix(name)
            if prefix:
                prefix_groups[prefix].append(name)

        for prefix, files in sorted(prefix_groups.items()):
            if len(files) >= MIN_COLLISION:
                rel = directory.relative_to(ROOT)
                file_list = ", ".join(sorted(files))
                violations.append(f"  {rel}/: prefix '{prefix}' shared by {file_list}")

    if violations:
        print("Prefix collision violations:", file=sys.stderr)
        for v in violations:
            print(v, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
