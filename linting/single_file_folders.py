#!/usr/bin/env python
"""Detect single-file packages that should be flattened to modules.

Flags any package under src/ that has __init__.py + exactly one other .py
module and NO subpackages. These should be converted to a single module file.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"


def _is_single_file_package(pkg_dir: Path) -> str | None:
    """Return the lone module name if pkg_dir is a single-file package, else None."""
    init = pkg_dir / "__init__.py"
    if not init.exists():
        return None

    py_files = [f for f in pkg_dir.iterdir() if f.suffix == ".py" and f.name != "__init__.py"]
    subdirs = [d for d in pkg_dir.iterdir() if d.is_dir() and (d / "__init__.py").exists()]

    if len(py_files) == 1 and len(subdirs) == 0:
        return py_files[0].name
    return None


def main() -> int:
    violations: list[str] = []

    if not SRC_DIR.is_dir():
        return 0

    for pkg_dir in sorted(SRC_DIR.rglob("*")):
        if not pkg_dir.is_dir():
            continue
        if not (pkg_dir / "__init__.py").exists():
            continue
        # Skip the src root itself
        if pkg_dir == SRC_DIR:
            continue

        lone_module = _is_single_file_package(pkg_dir)
        if lone_module:
            rel = pkg_dir.relative_to(ROOT)
            violations.append(f"  {rel}/ has only {lone_module} — flatten to a single module")

    if violations:
        print("Single-file folder violations:", file=sys.stderr)
        for v in violations:
            print(v, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
