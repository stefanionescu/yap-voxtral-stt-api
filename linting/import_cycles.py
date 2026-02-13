#!/usr/bin/env python3
"""Detect Python import cycles inside the src package.

This script performs static import analysis over repository modules and fails
when a strongly connected component (SCC) contains more than one module (or a
self-import). It is designed to complement import-linter boundary contracts.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict

SRC_DIR = Path("src")
INTERNAL_ROOT = "src"


@dataclass(frozen=True)
class ModuleFile:
    """Resolved Python module metadata."""

    path: Path
    module: str


def _collect_modules(root_dir: Path) -> list[ModuleFile]:
    """Collect module names for all Python files under root_dir."""
    modules: list[ModuleFile] = []
    for path in sorted(root_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root_dir).with_suffix("")
        parts = list(rel.parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        module = INTERNAL_ROOT if not parts else f"{INTERNAL_ROOT}." + ".".join(parts)
        modules.append(ModuleFile(path=path, module=module))
    return modules


def _build_known_modules(module_files: list[ModuleFile]) -> set[str]:
    """Build a set containing modules and package prefixes."""
    known = {entry.module for entry in module_files}
    for module in list(known):
        parts = module.split(".")
        for idx in range(1, len(parts)):
            known.add(".".join(parts[:idx]))
    return known


def _nearest_known_module(module_name: str, known_modules: set[str]) -> str | None:
    """Resolve module_name to the nearest known internal module/package."""
    candidate = module_name
    while candidate:
        if candidate in known_modules:
            return candidate
        if "." not in candidate:
            return None
        candidate = candidate.rsplit(".", 1)[0]
    return None


def _resolve_import_from(current_module: str, level: int, target: str | None) -> str:
    """Resolve a relative import target from current_module."""
    parts = current_module.split(".")
    if level <= 0:
        return target or ""
    base = parts[:-level] if level <= len(parts) else []
    if target:
        base.extend(target.split("."))
    return ".".join(base)


def _parse_import_edges(module_files: list[ModuleFile], known_modules: set[str]) -> dict[str, set[str]]:
    """Parse import edges between internal modules."""
    edges: dict[str, set[str]] = defaultdict(set)
    for entry in module_files:
        module = entry.module
        source_text = entry.path.read_text(encoding="utf-8")
        tree = ast.parse(source_text, filename=str(entry.path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    if not target.startswith(f"{INTERNAL_ROOT}.") and target != INTERNAL_ROOT:
                        continue
                    resolved = _nearest_known_module(target, known_modules)
                    if resolved:
                        edges[module].add(resolved)
            elif isinstance(node, ast.ImportFrom):
                target = _resolve_import_from(module, node.level, node.module) if node.level > 0 else node.module or ""
                if not target.startswith(f"{INTERNAL_ROOT}.") and target != INTERNAL_ROOT:
                    continue
                resolved = _nearest_known_module(target, known_modules)
                if resolved:
                    edges[module].add(resolved)
    return edges


def _find_strongly_connected_components(edges: dict[str, set[str]], modules: set[str]) -> list[list[str]]:
    """Return SCCs using Tarjan's algorithm."""
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    index_by_node: dict[str, int] = {}
    lowlink_by_node: dict[str, int] = {}
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        index_by_node[node] = index
        lowlink_by_node[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for neighbor in edges.get(node, set()):
            if neighbor not in index_by_node:
                visit(neighbor)
                lowlink_by_node[node] = min(lowlink_by_node[node], lowlink_by_node[neighbor])
            elif neighbor in on_stack:
                lowlink_by_node[node] = min(lowlink_by_node[node], index_by_node[neighbor])

        if lowlink_by_node[node] == index_by_node[node]:
            component: list[str] = []
            while stack:
                popped = stack.pop()
                on_stack.remove(popped)
                component.append(popped)
                if popped == node:
                    break
            components.append(component)

    for module in sorted(modules):
        if module not in index_by_node:
            visit(module)

    return components


def _format_cycle_component(component: list[str], edges: dict[str, set[str]]) -> str:
    """Render a cycle component for diagnostics."""
    ordered = sorted(component)
    lines = [f"- cycle ({len(ordered)} modules):"]
    for module in ordered:
        neighbors = sorted(target for target in edges.get(module, set()) if target in component)
        if neighbors:
            lines.append(f"  {module} -> {', '.join(neighbors)}")
        else:
            lines.append(f"  {module}")
    return "\n".join(lines)


def main() -> int:
    """CLI entrypoint."""
    if not SRC_DIR.is_dir():
        print(f"[import-cycles] Missing source directory: {SRC_DIR}", file=sys.stderr)
        return 1

    module_files = _collect_modules(SRC_DIR)
    known_modules = _build_known_modules(module_files)
    graph_edges = _parse_import_edges(module_files, known_modules)
    module_names = {entry.module for entry in module_files}

    components = _find_strongly_connected_components(graph_edges, module_names)
    cycle_components = [comp for comp in components if len(comp) > 1]
    self_cycles = [module for module, targets in graph_edges.items() if module in targets]

    if not cycle_components and not self_cycles:
        print(
            f"[import-cycles] OK: no import cycles across {len(module_names)} modules "
            f"({sum(len(targets) for targets in graph_edges.values())} edges)."
        )
        return 0

    print("[import-cycles] Import cycle(s) detected:", file=sys.stderr)
    for component in sorted(cycle_components, key=lambda comp: (-len(comp), sorted(comp)[0])):
        print(_format_cycle_component(component, graph_edges), file=sys.stderr)

    if self_cycles:
        for module in sorted(set(self_cycles)):
            print(f"- self-cycle: {module} imports itself", file=sys.stderr)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
