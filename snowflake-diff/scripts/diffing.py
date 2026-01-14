"""
diffing
=======

Unified diff and markdown-link helpers.

This module contains:
- reading/writing normalized UTF-8 text
- generating unified diffs
- writing diff files only when differences exist
- generating relative links for Markdown reports

These utilities keep the orchestration code in :mod:`scripts.snowdiff` small
and easy to reason about.

"""

from __future__ import annotations

import difflib
import os
import re
from pathlib import Path


def read_text(path: Path) -> str:
    """Read UTF-8 text from *path*.

    Parameters
    ----------
    path:
        File path.

    Returns
    -------
    str
        File contents, or an empty string if the file does not exist.
    """
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, content: str) -> None:
    """Write UTF-8 text to *path* with normalized newlines.

    Parameters
    ----------
    path:
        File path to write.
    content:
        Text content.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    path.write_text(content, encoding="utf-8")


def unified_diff(a_text: str, b_text: str, fromfile: str, tofile: str) -> str:
    """Return a unified diff between two strings.

    Parameters
    ----------
    a_text, b_text:
        Input texts.
    fromfile, tofile:
        Labels used in diff headers.

    Returns
    -------
    str
        Unified diff output.
    """
    a_lines = a_text.splitlines(keepends=True)
    b_lines = b_text.splitlines(keepends=True)
    return "".join(difflib.unified_diff(a_lines, b_lines, fromfile=fromfile, tofile=tofile))


def write_diff_file(out_path: Path, left_path: Path, right_path: Path, label_left: str, label_right: str) -> bool:
    """Write a diff file if *left_path* and *right_path* differ.

    Parameters
    ----------
    out_path:
        Where to write the diff.
    left_path, right_path:
        Files to compare.
    label_left, label_right:
        Labels for diff headers.

    Returns
    -------
    bool
        True if a diff file was written (differences exist), otherwise False.
    """
    a = read_text(left_path)
    b = read_text(right_path)
    diff = unified_diff(a, b, label_left, label_right)
    if diff.strip():
        write_text(out_path, diff)
        return True
    return False


def rel_link(from_file: Path, to_file: Path) -> str:
    """Create a portable relative link for Markdown.

    Parameters
    ----------
    from_file:
        The file that will contain the link (e.g., SUMMARY.md).
    to_file:
        The target file (e.g., a diff file).

    Returns
    -------
    str
        Relative path suitable for Markdown links.
    """
    return os.path.relpath(to_file, start=from_file.parent).replace("\\", "/")


def md_anchor(title: str) -> str:
    """Create an approximate GitHub-style markdown anchor from a section title."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
