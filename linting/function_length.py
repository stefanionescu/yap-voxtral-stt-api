#!/usr/bin/env python
"""Enforce maximum function length for runtime Python modules.

Checks functions and methods under src/ and fails when any function exceeds
60 code lines, excluding blank lines, comment-only lines, and docstrings.
"""

from __future__ import annotations

import ast
import sys
import tokenize
from pathlib import Path

FUNCTION_LIMIT = 60

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"


class _FunctionCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self._scope: list[str] = []
        self.functions: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._collect_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._collect_function(node)

    def _collect_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        qualified = ".".join((*self._scope, node.name)) if self._scope else node.name
        self.functions.append((qualified, node))
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()


def _comment_lines(filepath: Path) -> set[int]:
    comments: set[int] = set()
    try:
        with filepath.open("rb") as f:
            for tok in tokenize.tokenize(f.readline):
                if tok.type == tokenize.COMMENT:
                    comments.add(tok.start[0])
    except tokenize.TokenError:
        pass
    return comments


def _docstring_lines(tree: ast.AST) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if not getattr(node, "body", None):
            continue
        first = node.body[0]
        if not isinstance(first, ast.Expr):
            continue
        if not isinstance(first.value, ast.Constant):
            continue
        if not isinstance(first.value.value, str):
            continue
        for line_no in range(first.lineno, first.end_lineno + 1):
            lines.add(line_no)
    return lines


def _count_function_lines(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    raw_lines: list[str],
    comments: set[int],
    docstrings: set[int],
) -> int:
    count = 0
    for line_no in range(node.lineno, node.end_lineno + 1):
        if line_no in comments or line_no in docstrings:
            continue
        line = raw_lines[line_no - 1] if line_no - 1 < len(raw_lines) else ""
        if not line.strip():
            continue
        count += 1
    return count


def _collect_violations(filepath: Path) -> list[str]:
    try:
        source = filepath.read_text()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    comments = _comment_lines(filepath)
    docstrings = _docstring_lines(tree)
    raw_lines = source.splitlines()

    collector = _FunctionCollector()
    collector.visit(tree)

    violations: list[str] = []
    for qualified, node in collector.functions:
        size = _count_function_lines(node, raw_lines, comments, docstrings)
        if size > FUNCTION_LIMIT:
            rel = filepath.relative_to(ROOT)
            violations.append(f"  {rel}:{node.lineno} {qualified} -> {size} code lines (limit {FUNCTION_LIMIT})")
    return violations


def main() -> int:
    violations: list[str] = []
    if SRC_DIR.is_dir():
        for py_file in sorted(SRC_DIR.rglob("*.py")):
            violations.extend(_collect_violations(py_file))

    if violations:
        print("Function length violations:", file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
