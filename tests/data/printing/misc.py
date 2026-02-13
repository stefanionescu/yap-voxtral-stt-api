"""Miscellaneous printing helpers."""

from __future__ import annotations

import os
from collections.abc import Callable

from .fmt import dim, red


def print_file_not_found(
    filename: str,
    samples_dir: str,
    available_files: list[str],
    sink: Callable[[str], None] = print,
) -> None:
    sink(f"{red('ERROR')} File '{filename}' not found in {samples_dir}/")
    if available_files:
        names = [os.path.basename(f) for f in available_files]
        sink(f"{dim('Available files:')} {names}")


__all__ = ["print_file_not_found"]
