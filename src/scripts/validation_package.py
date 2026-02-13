"""Package availability validation.

Designed to replace inline ``python -c`` checks in shell scripts.
"""

from __future__ import annotations

import sys
import importlib.util

REQUIRED_ARGC = 2


def is_package_available(package_name: str) -> bool:
    return importlib.util.find_spec(package_name) is not None


def main() -> int:
    if len(sys.argv) < REQUIRED_ARGC:
        print("Usage: python -m src.scripts.validation_package <package>", file=sys.stderr)
        return 1
    return 0 if is_package_available(sys.argv[1]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
