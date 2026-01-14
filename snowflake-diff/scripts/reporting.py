"""
reporting
=========

Markdown report generation.

This module generates a summary report that links to diff files, making it easy
to review changes without manually navigating directories.

Primary API
-----------
- :func:`generate_summary_md`

"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import List, Tuple

from .diffing import md_anchor, rel_link, write_text


def generate_summary_md(out_dir: Path, header_lines: List[str], sections: List[Tuple[str, List[Path]]]) -> Path:
    """Generate a Markdown summary linking to diff files.

    Parameters
    ----------
    out_dir:
        Output directory where ``SUMMARY.md`` is written.
    header_lines:
        Bullet-style lines to include near the top (config/targets/options).
    sections:
        A list of ``(title, files)`` tuples. Each file should be a path under
        ``out_dir`` (typically ``out/diffs/...``).

    Returns
    -------
    pathlib.Path
        The path to the generated ``SUMMARY.md``.

    Notes
    -----
    Links are written as *relative* paths so the whole output directory can be
    moved or archived while preserving navigation.
    """
    summary_path = out_dir / "SUMMARY.md"
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: List[str] = []
    lines.append("# Snowflake Diff Summary\n\n")
    lines.append(f"_Generated: {now}_\n\n")

    if header_lines:
        for h in header_lines:
            lines.append(h + "\n")
        lines.append("\n")

    lines.append("## Contents\n")
    for title, _ in sections:
        lines.append(f"- [{title}](#{md_anchor(title)})\n")
    lines.append("\n")

    for title, files in sections:
        lines.append(f"## {title}\n\n")
        if not files:
            lines.append("- ✅ No differences\n\n")
            continue
        for f in sorted(files):
            lines.append(f"- [{f.name}]({rel_link(summary_path, f)})\n")
        lines.append("\n")

    write_text(summary_path, "".join(lines))
    return summary_path
