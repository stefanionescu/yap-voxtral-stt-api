#!/usr/bin/env python
"""Reject local imports in runtime-serving code.

Imports inside function/method bodies are frequently used as a form of lazy
loading. For this repository, keep runtime and realtime modules import-stable by
requiring imports at module scope.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_DIRS = [
    ROOT / "src" / "runtime",
    ROOT / "src" / "realtime",
]


class _Visitor(ast.NodeVisitor):
    def __init__(self, *, rel_path: str) -> None:
        self.rel_path = rel_path
        self.scope_depth = 0
        self.violations: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self.scope_depth += 1
        self.generic_visit(node)
        self.scope_depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self.scope_depth += 1
        self.generic_visit(node)
        self.scope_depth -= 1

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.scope_depth += 1
        self.generic_visit(node)
        self.scope_depth -= 1

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        if self.scope_depth > 0:
            self.violations.append(f"  {self.rel_path}:{node.lineno} local import is forbidden")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        if self.scope_depth > 0:
            self.violations.append(f"  {self.rel_path}:{node.lineno} local import is forbidden")


def _collect_file(path: Path) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    rel = str(path.relative_to(ROOT))
    v = _Visitor(rel_path=rel)
    v.visit(tree)
    return v.violations


def main() -> int:
    violations: list[str] = []
    for base in TARGET_DIRS:
        if not base.is_dir():
            continue
        for py_file in sorted(base.rglob("*.py")):
            if "__pycache__" in py_file.parts:
                continue
            violations.extend(_collect_file(py_file))

    if not violations:
        return 0

    print("Local import violations:", file=sys.stderr)
    for v in violations:
        print(v, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
