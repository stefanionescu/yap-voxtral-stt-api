"""Runtime package.

Keep this module dependency-light: importing `src.runtime.*` in CPU-only tooling
and unit tests should not require vLLM or CUDA.
"""

__all__: list[str] = []
