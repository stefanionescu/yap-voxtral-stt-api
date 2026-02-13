#!/usr/bin/env python
"""Enforce maximum code-line limits per runtime file.

Python files in src/ must not exceed 300 code lines.
Shell scripts in scripts/ and docker/ must not exceed 300 code lines.

Blank lines, comment-only lines, and docstring-only lines are excluded from
the count. __init__.py barrel-export files (only imports and __all__) are exempt.
"""

from __future__ import annotations

import ast
import sys
import tokenize
from pathlib import Path

SRC_LIMIT = 300
SHELL_LIMIT = 300

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
SCRIPTS_DIR = ROOT / "scripts"
DOCKER_DIR = ROOT / "docker"


def _comment_lines(filepath: Path) -> set[int]:
    """Return set of 1-based line numbers that are comment-only lines."""
    comments: set[int] = set()
    try:
        with filepath.open("rb") as f:
            for tok in tokenize.tokenize(f.readline):
                if tok.type == tokenize.COMMENT:
                    comments.add(tok.start[0])
    except tokenize.TokenError:
        pass
    return comments


def _docstring_lines(filepath: Path) -> set[int]:
    """Return set of 1-based line numbers occupied by module/class/function docstrings."""
    lines: set[int] = set()
    try:
        tree = ast.parse(filepath.read_text())
    except SyntaxError:
        return lines

    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        ):
            doc = node.body[0]
            for line_no in range(doc.lineno, doc.end_lineno + 1):
                lines.add(line_no)
    return lines


def _is_barrel_init(filepath: Path) -> bool:
    """Check if __init__.py is a barrel-export file (only imports, __all__, docstrings, pass)."""
    if filepath.name != "__init__.py":
        return False
    try:
        tree = ast.parse(filepath.read_text())
    except SyntaxError:
        return False
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if targets == ["__all__"]:
                continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        if isinstance(node, ast.Pass):
            continue
        return False
    return True


def _count_code_lines(filepath: Path) -> int:
    """Count non-blank, non-comment, non-docstring lines."""
    try:
        raw_lines = filepath.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return 0

    comments = _comment_lines(filepath)
    docstrings = _docstring_lines(filepath)

    count = 0
    for i, line in enumerate(raw_lines, start=1):
        if not line.strip():
            continue
        if i in comments:
            continue
        if i in docstrings:
            continue
        count += 1
    return count


def _count_shell_code_lines(filepath: Path) -> int:
    """Count non-blank, non-comment lines for shell scripts."""
    try:
        raw_lines = filepath.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return 0

    count = 0
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        count += 1
    return count


def main() -> int:
    violations: list[str] = []

    for directory, limit in [(SRC_DIR, SRC_LIMIT)]:
        if not directory.is_dir():
            continue
        for py_file in sorted(directory.rglob("*.py")):
            if _is_barrel_init(py_file):
                continue
            code_lines = _count_code_lines(py_file)
            if code_lines > limit:
                rel = py_file.relative_to(ROOT)
                violations.append(f"  {rel}: {code_lines} code lines (limit {limit})")

    for directory in (SCRIPTS_DIR, DOCKER_DIR):
        if not directory.is_dir():
            continue
        for sh_file in sorted(directory.rglob("*.sh")):
            code_lines = _count_shell_code_lines(sh_file)
            if code_lines > SHELL_LIMIT:
                rel = sh_file.relative_to(ROOT)
                violations.append(f"  {rel}: {code_lines} code lines (limit {SHELL_LIMIT})")

    if violations:
        print("File length violations:", file=sys.stderr)
        for v in violations:
            print(v, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
