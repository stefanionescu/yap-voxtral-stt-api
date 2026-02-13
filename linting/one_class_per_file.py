#!/usr/bin/env python
"""Enforce one top-level non-dataclass class per runtime Python file."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"


def _is_dataclass_decorator(decorator: ast.expr) -> bool:
    target: ast.expr = decorator.func if isinstance(decorator, ast.Call) else decorator
    if isinstance(target, ast.Name):
        return target.id == "dataclass"
    if isinstance(target, ast.Attribute):
        return target.attr == "dataclass"
    return False


def _is_dataclass_class(node: ast.ClassDef) -> bool:
    return any(_is_dataclass_decorator(decorator) for decorator in node.decorator_list)


def _collect_top_level_classes(filepath: Path) -> list[str]:
    try:
        source = filepath.read_text()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    classes: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if _is_dataclass_class(node):
            continue
        classes.append(node.name)
    return classes


def main() -> int:
    violations: list[str] = []

    if SRC_DIR.is_dir():
        for py_file in sorted(SRC_DIR.rglob("*.py")):
            classes = _collect_top_level_classes(py_file)
            if len(classes) > 1:
                rel = py_file.relative_to(ROOT)
                class_names = ", ".join(classes)
                violations.append(f"  {rel}: {len(classes)} classes ({class_names})")

    if violations:
        print("One non-dataclass-class-per-file violations:", file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
