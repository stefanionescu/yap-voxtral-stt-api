#!/usr/bin/env python
"""Reject lazy module loading/export patterns in runtime Python modules."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"

FORBIDDEN_EXPORT_HOOKS = {"__getattr__", "__dir__", "__getattribute__"}


def _collect_violations(path: Path) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    rel = path.relative_to(ROOT)
    violations: list[str] = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in FORBIDDEN_EXPORT_HOOKS:
            violations.append(f"  {rel}:{node.lineno} forbidden lazy export hook `{node.name}`")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "importlib"
            and func.attr == "import_module"
        ):
            violations.append(f"  {rel}:{node.lineno} forbidden dynamic import via importlib.import_module")
        if isinstance(func, ast.Name) and func.id == "import_module":
            violations.append(f"  {rel}:{node.lineno} forbidden dynamic import via import_module")

    if path.name == "__init__.py":
        for parent in ast.walk(tree):
            if not isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(parent):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    violations.append(f"  {rel}:{node.lineno} local import in __init__.py is forbidden")
    return violations


def main() -> int:
    if not SRC_DIR.is_dir():
        print(f"[no-lazy-module-loading] Missing source directory: {SRC_DIR}", file=sys.stderr)
        return 1

    violations: list[str] = []
    for py_file in sorted(SRC_DIR.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        violations.extend(_collect_violations(py_file))

    if not violations:
        return 0

    print("Lazy module loading/export violations:", file=sys.stderr)
    for violation in violations:
        print(violation, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
