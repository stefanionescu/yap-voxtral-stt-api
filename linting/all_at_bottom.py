#!/usr/bin/env python
"""Enforce that __all__ is defined once and appears at the bottom of a module.

Rules (top-level only):
- If __all__ exists, it must be exactly one statement: `__all__ = [...]`
- No __all__ mutations (+=, .append/.extend calls, annotated/augmented assigns, etc.)
- __all__ must be the last top-level statement in the file.

Files without __all__ are skipped.
"""

from __future__ import annotations

import ast
import sys
import argparse
from pathlib import Path


def _is_name(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def _is_canonical_all_stmt(node: ast.stmt) -> bool:
    """Return True if *node* is the single allowed form of __all__ definition."""
    if isinstance(node, ast.Assign):
        return len(node.targets) == 1 and _is_name(node.targets[0], "__all__")
    if isinstance(node, ast.AnnAssign):
        return _is_name(node.target, "__all__") and node.value is not None
    return False


def _targets_all_non_simple(node: ast.stmt) -> bool:
    # Any non-canonical assignment/mutation of __all__ is forbidden.
    if isinstance(node, ast.Assign):
        return any(_is_name(t, "__all__") for t in node.targets) and not _is_canonical_all_stmt(node)
    if isinstance(node, ast.AnnAssign):
        return _is_name(node.target, "__all__") and not _is_canonical_all_stmt(node)
    if isinstance(node, ast.AugAssign):
        return _is_name(node.target, "__all__")
    if isinstance(node, ast.Delete):
        return any(_is_name(t, "__all__") for t in node.targets)
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        func = node.value.func
        return isinstance(func, ast.Attribute) and _is_name(func.value, "__all__")
    return False


def _describe_node(node: ast.stmt) -> str:
    if isinstance(node, ast.FunctionDef):
        label = f"function `{node.name}`"
    elif isinstance(node, ast.AsyncFunctionDef):
        label = f"async function `{node.name}`"
    elif isinstance(node, ast.ClassDef):
        label = f"class `{node.name}`"
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        label = "import"
    elif isinstance(node, ast.Assign):
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        label = f"assignment `{', '.join(names)}`" if names else "assignment"
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        label = f"assignment `{node.target.id}`"
    elif isinstance(node, ast.If):
        label = "if statement"
    elif isinstance(node, (ast.For, ast.While)):
        label = "loop"
    elif isinstance(node, ast.With):
        label = "with statement"
    elif isinstance(node, ast.Try):
        label = "try statement"
    else:
        label = type(node).__name__
    return label


def _references_all(value: ast.AST | None) -> bool:
    if value is None:
        return False
    return any(isinstance(n, ast.Name) and n.id == "__all__" for n in ast.walk(value))


def _collect_violations(filepath: Path, root: Path) -> list[str]:
    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    rel = filepath.relative_to(root)

    all_assigns: list[tuple[int, ast.stmt]] = []
    other_all_ops: list[ast.stmt] = []

    for idx, node in enumerate(tree.body):
        if _is_canonical_all_stmt(node):
            all_assigns.append((idx, node))
            continue
        if _targets_all_non_simple(node):
            other_all_ops.append(node)

    if not all_assigns and not other_all_ops:
        return []

    violations: list[str] = []

    if other_all_ops:
        for node in other_all_ops:
            violations.append(
                f"  {rel}:{node.lineno} non-canonical `__all__` usage; "
                "use exactly one `__all__` assignment at file bottom"
            )

    if len(all_assigns) != 1:
        if len(all_assigns) == 0:
            violations.append(f"  {rel}: `__all__` must be set once via a single top-level assignment (no mutations)")
            return violations
        for _, node in all_assigns:
            violations.append(f"  {rel}:{node.lineno} multiple `__all__` assignments")
        return violations

    all_idx, all_node = all_assigns[0]

    value = all_node.value if isinstance(all_node, (ast.Assign, ast.AnnAssign)) else None
    if _references_all(value):
        violations.append(
            f"  {rel}:{all_node.lineno} `__all__` must not be built from itself; use a single literal/definition"
        )

    # __all__ must be last top-level statement.
    for node in tree.body[all_idx + 1 :]:
        label = _describe_node(node)
        violations.append(f"  {rel}:{node.lineno} {label} defined after `__all__`")

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce that __all__ is defined once and placed at module bottom.")
    parser.add_argument(
        "--dirs",
        nargs="+",
        default=["src", "tests"],
        help="Directories to scan (default: src tests)",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root for relative path display (default: .)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    violations: list[str] = []

    for d in args.dirs:
        scan_dir = (root / d).resolve()
        if not scan_dir.is_dir():
            continue
        for py_file in sorted(scan_dir.rglob("*.py")):
            if "__pycache__" in py_file.parts:
                continue
            violations.extend(_collect_violations(py_file, root))

    if violations:
        print("__all__ placement violations:", file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
