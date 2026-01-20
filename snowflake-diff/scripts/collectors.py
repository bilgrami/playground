"""
collectors
==========

Snapshot collection for Snowflake drift detection.

This module is responsible for collecting raw "left" and "right" snapshots via
SnowCLI (`snow sql`), storing them under:

- ``out/snapshots/left/``
- ``out/snapshots/right/``

The orchestration layer (:mod:`scripts.snowdiff`) drives which collectors run.

Design choices
--------------
- Table filtering is applied to *table-level* collectors (DDL, data, DESC column comments).
- Schema-wide column metadata (INFORMATION_SCHEMA.COLUMNS) is collected for the entire schema.
- SHOW/DESC parsing is conservative when headers are disabled (stable diffs).

Public helpers
--------------
- :func:`filter_tables` (include/exclude patterns)
- "collect_*" functions for snapshots

"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from .auth import SnowTarget, run_sql
from .diffing import write_text
from .utils import safe_name


@dataclass(frozen=True)
class Options:
    """Boolean switches controlling which comparisons to run."""
    schema: bool = True
    table_ddl: bool = True
    data: bool = True
    procs: bool = True
    comments: bool = True
    last_changed: bool = True


@dataclass(frozen=True)
class TableFilter:
    """Include/exclude patterns for table selection.

    Attributes
    ----------
    include : List[str]
        Patterns to include tables (LIKE-style or regex with ``re:`` prefix).
    exclude : List[str]
        Patterns to exclude tables.
    case_sensitive : bool
        If False (default), pattern matching is case-insensitive, which is
        recommended for Snowflake where unquoted identifiers are case-insensitive.
    """
    include: List[str]
    exclude: List[str]
    case_sensitive: bool = False


@dataclass(frozen=True)
class CommentCollection:
    """Controls how column comments are collected."""
    column_mode: str  # "desc" | "account_usage"


# ---- common queries ----
Q_LIST_TABLES = """
SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = CURRENT_SCHEMA()
  AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;
"""

Q_COLUMNS_META = """
SELECT
  TABLE_NAME,
  ORDINAL_POSITION,
  COLUMN_NAME,
  DATA_TYPE,
  COALESCE(CHARACTER_MAXIMUM_LENGTH::STRING, '') AS CHAR_LEN,
  COALESCE(NUMERIC_PRECISION::STRING, '') AS NUM_PREC,
  COALESCE(NUMERIC_SCALE::STRING, '') AS NUM_SCALE,
  IS_NULLABLE,
  COALESCE(COLUMN_DEFAULT::STRING, '') AS COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = CURRENT_SCHEMA()
ORDER BY TABLE_NAME, ORDINAL_POSITION;
"""

Q_LIST_PROCS = """
SELECT
  PROCEDURE_NAME,
  COALESCE(ARGUMENT_SIGNATURE, '') AS ARGUMENT_SIGNATURE
FROM INFORMATION_SCHEMA.PROCEDURES
WHERE PROCEDURE_SCHEMA = CURRENT_SCHEMA()
ORDER BY PROCEDURE_NAME, ARGUMENT_SIGNATURE;
"""


def parse_single_col_tsv(tsv: str) -> List[str]:
    """Parse a single-column TSV into a list of values."""
    out: List[str] = []
    for line in tsv.splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(line.split("\t")[0].strip())
    return out


# ---- table filter helpers ----
def sql_like_to_fnmatch(pattern: str) -> str:
    """Convert SQL LIKE patterns (% and _) to fnmatch syntax (* and ?)."""
    return pattern.replace("%", "*").replace("_", "?")


def matches_pattern(name: str, pattern: str, case_sensitive: bool = False) -> bool:
    """Return True if name matches pattern (LIKE by default, regex via ``re:``).

    Parameters
    ----------
    name : str
        The table name to check.
    pattern : str
        The pattern to match against. Use ``re:`` prefix for regex patterns.
    case_sensitive : bool
        If False (default), matching is case-insensitive. This is recommended
        for Snowflake where unquoted identifiers are case-insensitive.

    Returns
    -------
    bool
        True if the name matches the pattern.
    """
    if pattern.startswith("re:"):
        flags = 0 if case_sensitive else re.IGNORECASE
        return re.search(pattern[3:], name, flags) is not None

    fn_pattern = sql_like_to_fnmatch(pattern)
    if case_sensitive:
        return fnmatch.fnmatchcase(name, fn_pattern)
    else:
        # Case-insensitive matching: compare uppercase versions
        return fnmatch.fnmatch(name.upper(), fn_pattern.upper())


def filter_tables(
    tables: Sequence[str],
    include: Sequence[str],
    exclude: Sequence[str],
    case_sensitive: bool = False,
) -> List[str]:
    """Filter tables using include/exclude patterns.

    Parameters
    ----------
    tables : Sequence[str]
        List of table names to filter.
    include : Sequence[str]
        Patterns to include (keeps tables matching *any* include pattern).
    exclude : Sequence[str]
        Patterns to exclude (drops tables matching *any* exclude pattern).
    case_sensitive : bool
        If False (default), pattern matching is case-insensitive.

    Returns
    -------
    List[str]
        Filtered and sorted list of table names.
    """
    result = list(tables)
    if include:
        result = [t for t in result if any(matches_pattern(t, p, case_sensitive) for p in include)]
    if exclude:
        result = [t for t in result if not any(matches_pattern(t, p, case_sensitive) for p in exclude)]
    return sorted(set(result))


# ---- DDL + data queries ----
def q_get_table_ddl(db: str, schema: str, table: str) -> str:
    """GET_DDL query for a table."""
    return f"SELECT GET_DDL('TABLE', '{db}.{schema}.{table}');"


def q_data_fingerprint(db: str, schema: str, table: str) -> str:
    """Fingerprint query: count + hash_agg(hash(row)).

    Note: The table alias is quoted with double quotes to handle table names
    containing spaces, special characters, or SQL reserved keywords.
    """
    # Quote identifiers to handle special characters and reserved words
    quoted_table = f'"{table}"'
    fq = f'"{db}"."{schema}"."{table}"'
    return f"""
SELECT
  '{db}.{schema}.{table}' AS TABLE_FQN,
  COUNT(*) AS ROW_COUNT,
  HASH_AGG(HASH({quoted_table}.*)) AS HASH_ALL_COLUMNS
FROM {fq} {quoted_table};
""".strip()


def q_get_proc_ddl(db: str, schema: str, pname: str, argsig: str) -> str:
    """GET_DDL query for a procedure (name + signature)."""
    return f"SELECT GET_DDL('PROCEDURE', '{db}.{schema}.{pname}{argsig}');"


# ---- SHOW/DESC queries ----
def q_show_tables(db: str, schema: str) -> str:
    return f"SHOW TABLES IN SCHEMA {db}.{schema};"


def q_show_views(db: str, schema: str) -> str:
    return f"SHOW VIEWS IN SCHEMA {db}.{schema};"


def q_show_procedures(db: str, schema: str) -> str:
    return f"SHOW PROCEDURES IN SCHEMA {db}.{schema};"


def q_desc_table(db: str, schema: str, table: str) -> str:
    return f"DESC TABLE {db}.{schema}.{table};"


def q_account_usage_column_comments(db: str, schema: str) -> str:
    """Column comments from ACCOUNT_USAGE (requires privileges; may lag)."""
    return f"""
SELECT
  TABLE_NAME,
  COLUMN_NAME,
  COALESCE(COMMENT::STRING, '') AS COMMENT
FROM {db}.ACCOUNT_USAGE.COLUMNS
WHERE TABLE_SCHEMA = '{schema}'
  AND TABLE_CATALOG = '{db}'
ORDER BY TABLE_NAME, COLUMN_NAME;
""".strip()


def parse_show_reduced(show_tsv: str, object_type: str) -> str:
    """Conservative reduced SHOW snapshot: prefix type + raw row."""
    if show_tsv.startswith("__ERROR__"):
        return show_tsv
    lines = []
    for row in show_tsv.splitlines():
        if row.strip():
            lines.append(f"{object_type}\t{row}")
    return "\n".join(lines) + ("\n" if lines else "")


def parse_desc_reduced(desc_tsv: str, table_name: str) -> str:
    """Conservative reduced DESC snapshot: prefix table + raw row."""
    if desc_tsv.startswith("__ERROR__"):
        return f"{table_name}\t{desc_tsv}\n"
    lines = []
    for row in desc_tsv.splitlines():
        if row.strip():
            lines.append(f"{table_name}\t{row}")
    return "\n".join(lines) + ("\n" if lines else "")


# ---- collection functions ----
def collect_table_list(target: SnowTarget, snap_dir: Path) -> List[str]:
    """Collect table list snapshot; returns list of table names."""
    out = run_sql(target, Q_LIST_TABLES)
    write_text(snap_dir / "tables.tsv", out)
    return parse_single_col_tsv(out)


def collect_columns_meta(target: SnowTarget, snap_dir: Path) -> None:
    """Collect schema-wide column metadata snapshot."""
    out = run_sql(target, Q_COLUMNS_META)
    write_text(snap_dir / "columns_meta.tsv", out)


def collect_table_ddls(left: SnowTarget, right: SnowTarget, tables: List[str], left_snap: Path, right_snap: Path) -> None:
    """Collect table DDL snapshots for both targets."""
    for t in tables:
        lf = left_snap / "table_ddls" / f"{safe_name(t)}.sql"
        rf = right_snap / "table_ddls" / f"{safe_name(t)}.sql"

        lout = run_sql(left, q_get_table_ddl(left.database, left.schema, t))
        rout = run_sql(right, q_get_table_ddl(right.database, right.schema, t))

        if lout.startswith("__ERROR__"):
            lout = f"-- missing or error on LEFT: {left.database}.{left.schema}.{t}\n{lout}"
        if rout.startswith("__ERROR__"):
            rout = f"-- missing or error on RIGHT: {right.database}.{right.schema}.{t}\n{rout}"

        write_text(lf, lout)
        write_text(rf, rout)


def collect_data_fingerprints(left: SnowTarget, right: SnowTarget, tables: List[str], left_snap: Path, right_snap: Path) -> None:
    """Collect data fingerprint snapshots for both targets."""
    for t in tables:
        lf = left_snap / "data" / f"{safe_name(t)}.tsv"
        rf = right_snap / "data" / f"{safe_name(t)}.tsv"

        lout = run_sql(left, q_data_fingerprint(left.database, left.schema, t))
        rout = run_sql(right, q_data_fingerprint(right.database, right.schema, t))

        if lout.startswith("__ERROR__"):
            lout = f"{left.database}.{left.schema}.{t}\tMISSING_OR_ERROR\tMISSING_OR_ERROR\n{lout}"
        if rout.startswith("__ERROR__"):
            rout = f"{right.database}.{right.schema}.{t}\tMISSING_OR_ERROR\tMISSING_OR_ERROR\n{rout}"

        write_text(lf, lout)
        write_text(rf, rout)


def collect_procs_list(target: SnowTarget, snap_dir: Path) -> List[Tuple[str, str]]:
    """Collect procedure list (name + argument signature)."""
    out = run_sql(target, Q_LIST_PROCS)
    write_text(snap_dir / "procs.tsv", out)

    procs: List[Tuple[str, str]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        pname = (parts[0] if len(parts) > 0 else "").strip()
        argsig = (parts[1] if len(parts) > 1 else "").strip()
        if pname:
            procs.append((pname, argsig))
    return procs


def collect_proc_ddls(left: SnowTarget, right: SnowTarget, procs: List[Tuple[str, str]], left_snap: Path, right_snap: Path) -> None:
    """Collect procedure DDL snapshots for both targets."""
    for pname, argsig in procs:
        key = f"{pname}{argsig}"
        lf = left_snap / "procs" / f"{safe_name(key)}.sql"
        rf = right_snap / "procs" / f"{safe_name(key)}.sql"

        lout = run_sql(left, q_get_proc_ddl(left.database, left.schema, pname, argsig))
        rout = run_sql(right, q_get_proc_ddl(right.database, right.schema, pname, argsig))

        if lout.startswith("__ERROR__"):
            lout = f"-- missing or error on LEFT: {left.database}.{left.schema}.{pname}{argsig}\n{lout}"
        if rout.startswith("__ERROR__"):
            rout = f"-- missing or error on RIGHT: {right.database}.{right.schema}.{pname}{argsig}\n{rout}"

        write_text(lf, lout)
        write_text(rf, rout)


def collect_show_outputs(target: SnowTarget, snap_dir: Path) -> Dict[str, str]:
    """Collect raw SHOW outputs (tables, views, procedures) and write snapshots."""
    tables = run_sql(target, q_show_tables(target.database, target.schema))
    views = run_sql(target, q_show_views(target.database, target.schema))
    procs = run_sql(target, q_show_procedures(target.database, target.schema))

    write_text(snap_dir / "show_tables.tsv", tables)
    write_text(snap_dir / "show_views.tsv", views)
    write_text(snap_dir / "show_procedures.tsv", procs)

    return {"tables": tables, "views": views, "procs": procs}


def collect_comments_and_metadata_from_show(snap_dir: Path, show_map: Dict[str, str]) -> None:
    """Build a reduced SHOW snapshot used for comments + last-changed drift diffs."""
    reduced = []
    reduced.append(parse_show_reduced(show_map["tables"], "TABLE"))
    reduced.append(parse_show_reduced(show_map["views"], "VIEW"))
    reduced.append(parse_show_reduced(show_map["procs"], "PROCEDURE"))
    write_text(snap_dir / "comments_and_metadata_from_show.tsv", "".join(reduced))


def collect_column_comments_desc(target: SnowTarget, snap_dir: Path, tables: List[str]) -> None:
    """Collect column comments via DESC TABLE per table (accurate, slower)."""
    desc_dir = snap_dir / "desc_tables"
    combined: List[str] = []

    for t in tables:
        out = run_sql(target, q_desc_table(target.database, target.schema, t))
        write_text(desc_dir / f"{safe_name(t)}.tsv", out)
        combined.append(parse_desc_reduced(out, t))

    write_text(snap_dir / "column_comments_desc.tsv", "".join(combined))


def collect_column_comments_account_usage(target: SnowTarget, snap_dir: Path) -> None:
    """Collect column comments via ACCOUNT_USAGE.COLUMNS (fast if allowed; may lag)."""
    out = run_sql(target, q_account_usage_column_comments(target.database, target.schema))
    write_text(snap_dir / "column_comments_account_usage.tsv", out)
