"""
utils
=====

Small, shared utilities used across the codebase.

This module intentionally contains only low-level helpers that are safe to
import from anywhere (no SnowCLI calls, no heavy imports).

Functions
---------
- :func:`safe_name`:
  Convert an arbitrary identifier (table/proc name, signature, etc.) into a
  filesystem-safe filename component.
"""

from __future__ import annotations

import re


def safe_name(value: str) -> str:
    """Return a filesystem-safe version of *value*.

    This helper is used for naming snapshot files and diff files consistently
    across modules.

    Parameters
    ----------
    value:
        The input string to sanitize (e.g., a table name or procedure signature).

    Returns
    -------
    str
        A sanitized string containing only ``[A-Za-z0-9._-]`` plus underscores,
        with surrounding underscores removed. Returns ``"unnamed"`` if the
        result would otherwise be empty.

    Examples
    --------
    >>> safe_name("FACT SALES$2025")
    'FACT_SALES_2025'
    >>> safe_name("")
    'unnamed'
    """
    out = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return out or "unnamed"
