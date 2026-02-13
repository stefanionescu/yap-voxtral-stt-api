#!/usr/bin/env python
"""Reject legacy/backward-compatibility markers in runtime modules."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TARGETS = [
    ROOT / "src" / "runtime",
    ROOT / "src" / "messages",
    ROOT / "src" / "handlers",
    ROOT / "src" / "execution",
    ROOT / "src" / "server.py",
]

ALLOWLIST = {
    ROOT / "src" / "execution" / "compat.py",
}

PATTERNS = [
    re.compile(r"\blegacy\b", re.IGNORECASE),
    re.compile(r"\bdeprecated\b", re.IGNORECASE),
    re.compile(r"\bworkaround\b", re.IGNORECASE),
    re.compile(r"\bbackward(?:\s|-)?compat(?:ible|ibility)\b", re.IGNORECASE),
    re.compile(r"\bcompatibility\b", re.IGNORECASE),
]


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for target in TARGETS:
        if target.is_file():
            files.append(target)
            continue
        if target.is_dir():
            files.extend(sorted(target.rglob("*.py")))
    return files


def _collect_violations(path: Path) -> list[str]:
    if path in ALLOWLIST:
        return []
    text = path.read_text(encoding="utf-8")
    violations: list[str] = []
    lines = text.splitlines()
    rel = path.relative_to(ROOT)
    for idx, line in enumerate(lines, start=1):
        for pattern in PATTERNS:
            if pattern.search(line):
                violations.append(f"  {rel}:{idx} contains prohibited marker `{pattern.pattern}`")
                break
    return violations


def main() -> int:
    violations: list[str] = []
    for py_file in _iter_python_files():
        if "__pycache__" in py_file.parts:
            continue
        violations.extend(_collect_violations(py_file))

    if violations:
        print("Legacy/compatibility marker violations:", file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
