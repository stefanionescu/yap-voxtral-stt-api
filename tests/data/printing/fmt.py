"""Clean, readable output formatting for test utilities.

This module provides consistent formatting helpers for displaying test
results in a readable, scannable format across all test scripts.

All console formatting should be routed through this module to ensure
consistent styling and automatic TTY detection for ANSI color support.
"""

from __future__ import annotations

import sys
from collections.abc import Callable

# ANSI color codes (disabled if not a tty)
_USE_COLOR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    """Wrap text in ANSI color codes if output is a tty."""
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


# ============================================================================
# Color Helpers
# ============================================================================


def dim(text: str) -> str:
    """Apply dim/faint styling to text."""
    return _c("2", text)


def bold(text: str) -> str:
    """Apply bold styling to text."""
    return _c("1", text)


def green(text: str) -> str:
    """Apply green color to text."""
    return _c("32", text)


def red(text: str) -> str:
    """Apply red color to text."""
    return _c("31", text)


def cyan(text: str) -> str:
    """Apply cyan color to text."""
    return _c("36", text)


def yellow(text: str) -> str:
    """Apply yellow color to text."""
    return _c("33", text)


def magenta(text: str) -> str:
    """Apply magenta color to text."""
    return _c("35", text)


# ============================================================================
# Visual Separators
# ============================================================================


def section_header(title: str, width: int = 60) -> str:
    """Create a prominent section header with surrounding decoration."""
    padding = width - len(title) - 4
    left = padding // 2
    right = padding - left
    return bold(f"{'─' * left}[ {title} ]{'─' * right}")


def test_header(name: str) -> str:
    """Create a test case header with newline prefix."""
    return f"\n{section_header(name)}"


def metrics_header(title: str = "Metrics") -> str:
    """Create a metrics section header."""
    return f"\n{dim('───')} {bold(title)} {dim('───')}"


def segment_header(segment_num: int) -> str:
    """Create a segment header for multi-segment tests."""
    return f"\n{dim('───')} {bold(f'Segment {segment_num}')} {dim('───')}"


# ============================================================================
# Test Result Formatting
# ============================================================================


def format_pass(label: str) -> str:
    """Format a passing test result."""
    return f"{green('✓ PASS')}  {label}"


def format_fail(label: str, reason: str = "") -> str:
    """Format a failing test result."""
    suffix = f": {reason}" if reason else ""
    return f"{red('✗ FAIL')}  {label}{suffix}"


def format_info(text: str) -> str:
    """Format informational text with indent."""
    return dim(f"  {text}")


def format_error(label: str, detail: str = "") -> str:
    """Format an error message."""
    suffix = f": {detail}" if detail else ""
    return f"{red('ERROR')}  {label}{suffix}"


def format_warning(label: str, detail: str = "") -> str:
    """Format a warning message."""
    suffix = f": {detail}" if detail else ""
    return f"{yellow('WARN')}  {label}{suffix}"


# ============================================================================
# Metric Value Formatting
# ============================================================================


def format_metric(label: str, value: str, *, width: int = 16) -> str:
    """Format a single metric label and value with consistent alignment."""
    return f"{label:<{width}} {value}"


def format_metric_line(
    label: str,
    *,
    avg: float | None = None,
    p50: float | None = None,
    p95: float | None = None,
    unit: str = "",
    count: int | None = None,
) -> str:
    """Format a metric statistics line with avg/p50/p95."""
    parts = []
    if avg is not None:
        parts.append(f"avg={avg:.4f}{unit}")
    if p50 is not None:
        parts.append(f"p50={p50:.4f}{unit}")
    if p95 is not None:
        parts.append(f"p95={p95:.4f}{unit}")
    line = f"{label:<14} | {'  '.join(parts)}"
    if count is not None:
        line += f"  {dim(f'(n={count})')}"
    return line


def format_metric_ms(
    label: str,
    *,
    avg: float | None = None,
    p50: float | None = None,
    p95: float | None = None,
    count: int | None = None,
) -> str:
    """Format a millisecond metric statistics line."""
    parts = []
    if avg is not None:
        parts.append(f"avg={avg:.1f}ms")
    if p50 is not None:
        parts.append(f"p50={p50:.1f}ms")
    if p95 is not None:
        parts.append(f"p95={p95:.1f}ms")
    line = f"{label:<18} | {'  '.join(parts)}"
    if count is not None:
        line += f"  {dim(f'(n={count})')}"
    return line


# ============================================================================
# Summary Formatting
# ============================================================================


def format_summary_header(title: str) -> str:
    """Format a summary section header."""
    return f"\n{bold('══')} {title} {bold('══')}"


def format_count_line(total: int, success: int = 0, failed: int = 0) -> str:
    """Format a count summary line with colored success/fail counts."""
    parts = [f"n={total}"]
    if success > 0:
        parts.append(green(f"{success} ok"))
    if failed > 0:
        parts.append(red(f"{failed} failed"))
    return "  ".join(parts)


# ============================================================================
# Multi-line Emitter Pattern
# ============================================================================


def emit_section(
    title: str,
    lines: list[str],
    sink: Callable[[str], None] = print,
) -> None:
    """Emit a titled section with multiple lines using the sink pattern."""
    sink(section_header(title))
    for line in lines:
        sink(line)


__all__ = [
    "bold",
    "cyan",
    "dim",
    "emit_section",
    "format_count_line",
    "format_error",
    "format_fail",
    "format_info",
    "format_metric",
    "format_metric_line",
    "format_metric_ms",
    "format_pass",
    "format_summary_header",
    "format_warning",
    "green",
    "magenta",
    "metrics_header",
    "red",
    "section_header",
    "segment_header",
    "test_header",
    "yellow",
]
