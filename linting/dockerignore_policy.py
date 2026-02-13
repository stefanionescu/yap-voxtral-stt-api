#!/usr/bin/env python
"""Enforce repository Docker ignore policy declared in linting/policy.toml."""

from __future__ import annotations

import sys
from typing import Any
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "linting" / "policy.toml"


def _first_effective_line(path: Path) -> str | None:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        return line
    return None


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _repo_path(value: Any, *, field: str, violations: list[str]) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        violations.append(f"  linting/policy.toml: `{field}` entries must be non-empty strings")
        return None
    candidate = Path(value.strip())
    if candidate.is_absolute():
        violations.append(f"  linting/policy.toml: `{field}` entry `{value}` must be repository-relative")
        return None
    if ".." in candidate.parts:
        violations.append(f"  linting/policy.toml: `{field}` entry `{value}` must not contain `..`")
        return None
    resolved = (ROOT / candidate).resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        violations.append(f"  linting/policy.toml: `{field}` entry `{value}` resolves outside repository root")
        return None
    return resolved


def _path_set(values: Any, *, field: str, violations: list[str]) -> set[Path]:
    if values is None:
        return set()
    if not isinstance(values, list):
        violations.append(f"  linting/policy.toml: `{field}` must be an array")
        return set()

    paths: set[Path] = set()
    for value in values:
        resolved = _repo_path(value, field=field, violations=violations)
        if resolved is not None:
            paths.add(resolved)
    return paths


def _load_policy() -> tuple[dict[str, Any], list[str]]:
    violations: list[str] = []
    if not POLICY_PATH.exists():
        violations.append("  linting/policy.toml: missing required policy file")
        return {}, violations

    try:
        policy_doc = tomllib.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        violations.append(f"  linting/policy.toml: failed to parse TOML ({exc})")
        return {}, violations

    dockerignore = policy_doc.get("dockerignore")
    if not isinstance(dockerignore, dict):
        violations.append("  linting/policy.toml: missing required `[dockerignore]` table")
        return {}, violations
    return dockerignore, violations


def main() -> int:
    policy, violations = _load_policy()

    mode = policy.get("mode") if policy else None
    if mode is not None and not isinstance(mode, str):
        violations.append("  linting/policy.toml: `dockerignore.mode` must be a string")
        mode = None

    first_effective_rule = policy.get("first_effective_rule", "**") if policy else "**"
    if not isinstance(first_effective_rule, str):
        violations.append("  linting/policy.toml: `dockerignore.first_effective_rule` must be a string")
        first_effective_rule = "**"

    allow_only_listed = policy.get("allow_only_listed", True) if policy else True
    if not isinstance(allow_only_listed, bool):
        violations.append("  linting/policy.toml: `dockerignore.allow_only_listed` must be a boolean")
        allow_only_listed = True

    required = _path_set(
        policy.get("required_files") if policy else None, field="dockerignore.required_files", violations=violations
    )
    forbidden = _path_set(
        policy.get("forbidden_files") if policy else None,
        field="dockerignore.forbidden_files",
        violations=violations,
    )
    allowed_extra = _path_set(
        policy.get("allowed_extra_files") if policy else None,
        field="dockerignore.allowed_extra_files",
        violations=violations,
    )

    discovered = set(ROOT.rglob(".dockerignore"))

    for path in sorted(forbidden):
        if path.exists():
            violations.append(f"  {_rel(path)}: forbidden .dockerignore path for this repository policy")

    for path in sorted(required):
        if not path.exists():
            violations.append(f"  {_rel(path)}: missing required .dockerignore path")
            continue
        first_line = _first_effective_line(path)
        if first_line != first_effective_rule:
            violations.append(
                f"  {_rel(path)}: first effective rule must be `{first_effective_rule}` (deny-all default)"
            )

    if allow_only_listed:
        extras = discovered - required - forbidden - allowed_extra
        for path in sorted(extras):
            violations.append(f"  {_rel(path)}: unexpected .dockerignore path for this repository policy")

    if violations:
        header = "Docker ignore policy violations"
        if isinstance(mode, str) and mode:
            header += f" (mode={mode})"
        print(f"{header}:", file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
