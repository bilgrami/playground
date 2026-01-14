#!/usr/bin/env python3
"""
snowdiff
========

Compare two Snowflake targets (database/schema/role/warehouse) using Snowflake CLI
(`snow sql`) and produce unified diffs plus a Markdown summary.

This tool captures "left" and "right" snapshots of:

- Table list
- Column metadata (INFORMATION_SCHEMA.COLUMNS)
- Table DDL (GET_DDL('TABLE', ...))
- Optional data fingerprints (COUNT(*) + HASH_AGG(HASH(t.*)))
- Stored procedure DDL (GET_DDL('PROCEDURE', ...))

Then it produces unified diff files under ``out/diffs/`` and a clickable
Markdown summary at ``out/SUMMARY.md``.

Table filtering
---------------

You can filter which tables are compared using include/exclude patterns:

- include: keep only tables that match ANY include pattern
- exclude: drop tables that match ANY exclude pattern

Patterns support:
- SQL LIKE wildcards: ``%`` and ``_`` (default)
- Regex patterns if you prefix with ``re:``

Examples:
- include: ["FACT_%", "DIM_%"]        (SQL LIKE)
- exclude: ["TMP_%", "re:^ZZ_.*$"]    (mix LIKE + regex)

Patterns can be set in YAML config or passed via CLI:

YAML::

    table_filter:
      include: ["FACT_%"]
      exclude: ["TMP_%"]

CLI::

    python3 scripts/snowdiff.py --config config.yml --include "FACT_%" --exclude "TMP_%"

Configuration
-------------

Example ``config.yml``::

    out_dir: out
    options:
      schema: true
      table_ddl: true
      data: true
      procs: true

    table_filter:
      include: ["FACT_%"]
      exclude: ["TMP_%", "re:^ZZ_"]

    left:
      account: "YOUR_ACCOUNT"
      user: "YOUR_USER"
      authenticator: "externalbrowser"
      role: "ROLE_A"
      warehouse: "WH"
      database: "DB_A"
      schema: "SCHEMA_A"

    right:
      account: "YOUR_ACCOUNT"
      user: "YOUR_USER"
      authenticator: "externalbrowser"
      role: "ROLE_B"
      warehouse: "WH"
      database: "DB_B"
      schema: "SCHEMA_B"

CLI Usage
---------

Basic run::

    python3 scripts/snowdiff.py --config config.yml

Override output directory::

    python3 scripts/snowdiff.py --config config.yml --out out_prod_vs_stage

Disable expensive checks::

    python3 scripts/snowdiff.py --config config.yml --no-data --no-procs

Override a single parameter from config (example: right role)::

    python3 scripts/snowdiff.py --config config.yml --right-role NEW_ROLE

Autodoc / Documentation generation (Sphinx)
-------------------------------------------

Example ``docs/index.rst``::

    .. automodule:: scripts.snowdiff
        :members:
        :undoc-members:
        :show-inheritance:

"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import fnmatch
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import yaml


# -----------------------------
# Models
# -----------------------------
@dataclass(frozen=True)
class Target:
    """A Snowflake target environment for snapshot collection.

    Attributes:
        account: Snowflake account identifier (as used by SnowCLI).
        user: Snowflake username.
        auth: SnowCLI authenticator (e.g. ``externalbrowser``).
        role: Snowflake role.
        warehouse: Warehouse to use for queries.
        database: Database name.
        schema: Schema name.
        label: Logical label for reporting (typically ``left`` or ``right``).
    """

    account: str
    user: str
    auth: str
    role: str
    warehouse: str
    database: str
    schema: str
    label: str  # "left" or "right"

    def describe(self) -> str:
        """Return a human-readable description for logs/reports."""
        return (
            f"{self.label.upper()}: account={self.account} role={self.role} "
            f"db={self.database} schema={self.schema} wh={self.warehouse}"
        )


# -----------------------------
# Utilities
# -----------------------------
def safe_name(s: str) -> str:
    """Return a filesystem-safe name."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_") or "unnamed"


def ensure_cmd(cmd: str) -> None:
    """Fail fast if a required command is missing from PATH."""
    if shutil.which(cmd) is None:
        raise SystemExit(f"ERROR: missing command in PATH: {cmd}")


def write_text(path: Path, content: str) -> None:
    """Write UTF-8 text with normalized newlines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    path.write_text(content, encoding="utf-8")


def read_text(path: Path) -> str:
    """Read UTF-8 text; return empty string if file doesn't exist."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def unified_diff(a_text: str, b_text: str, fromfile: str, tofile: str) -> str:
    """Return unified diff between two strings."""
    a_lines = a_text.splitlines(keepends=True)
    b_lines = b_text.splitlines(keepends=True)
    diff = difflib.unified_diff(a_lines, b_lines, fromfile=fromfile, tofile=tofile)
    return "".join(diff)


def list_union(a: Iterable[str], b: Iterable[str]) -> List[str]:
    """Return sorted union of two iterables of strings (excluding blanks)."""
    return sorted(set(x for x in a if x) | set(y for y in b if y))


def parse_single_col_tsv(tsv: str) -> List[str]:
    """Parse a single-column TSV into a list of values."""
    out: List[str] = []
    for line in tsv.splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(line.split("\t")[0].strip())
    return out


def load_yaml(path: Path) -> Dict[str, Any]:
    """Load YAML config file."""
    if not path.exists():
        raise SystemExit(f"ERROR: config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def deep_get(d: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """Safely get nested dict value with default."""
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def pick(val_cli: Optional[str], val_cfg: Optional[str], field: str) -> str:
    """Pick a value from CLI override or config; error if missing."""
    v = val_cli if (val_cli is not None and val_cli != "") else (val_cfg or "")
    if not v:
        raise SystemExit(f"ERROR: missing required field: {field}")
    return v


def run_snow_sql(target: Target, query: str) -> str:
    """Execute a SQL query via SnowCLI and return stdout as TSV.

    Args:
        target: Connection/namespace parameters for SnowCLI.
        query: SQL query text.

    Returns:
        TSV output as a string. If SnowCLI fails, returns a sentinel string
        beginning with ``__ERROR__`` containing exit code and stderr text.

    Notes:
        Uses ``--format tsv --header false`` for stable diffs.
        If your SnowCLI uses different flags, adjust this function only.
    """
    cmd = [
        "snow",
        "sql",
        "--account",
        target.account,
        "--user",
        target.user,
        "--authenticator",
        target.auth,
        "--role",
        target.role,
        "--warehouse",
        target.warehouse,
        "--database",
        target.database,
        "--schema",
        target.schema,
        "--query",
        query,
        "--format",
        "tsv",
        "--header",
        "false",
    ]
    p = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if p.returncode != 0:
        return f"__ERROR__\t{p.returncode}\t{p.stderr.strip()}\n"
    return p.stdout or ""


# -----------------------------
# Table filtering (include/exclude patterns)
# -----------------------------
def sql_like_to_fnmatch(pattern: str) -> str:
    """Convert SQL LIKE pattern (% and _) to fnmatch (* and ?)."""
    return pattern.replace("%", "*").replace("_", "?")


def matches_pattern(name: str, pattern: str) -> bool:
    """Return True if `name` matches `pattern`.

    Pattern rules:
    - If pattern starts with ``re:``, treat the rest as a regex.
    - Else treat as SQL LIKE (supports % and _), case-sensitive.
    """
    if pattern.startswith("re:"):
        rx = pattern[3:]
        return re.search(rx, name) is not None
    # SQL LIKE -> fnmatch
    fm = sql_like_to_fnmatch(pattern)
    return fnmatch.fnmatchcase(name, fm)


def filter_tables(
    tables: Sequence[str],
    include: Sequence[str],
    exclude: Sequence[str],
) -> List[str]:
    """Filter table names based on include/exclude patterns.

    Args:
        tables: List of table names.
        include: Keep only tables matching any include pattern (if non-empty).
        exclude: Drop tables matching any exclude pattern.

    Returns:
        Filtered list (sorted).
    """
    result = list(tables)

    if include:
        kept = []
        for t in result:
            if any(matches_pattern(t, p) for p in include):
                kept.append(t)
        result = kept

    if exclude:
        kept = []
        for t in result:
            if not any(matches_pattern(t, p) for p in exclude):
                kept.append(t)
        result = kept

    return sorted(set(result))


# -----------------------------
# Queries
# -----------------------------
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


def q_get_table_ddl(db: str, schema: str, table: str) -> str:
    """Return a GET_DDL query for a table."""
    fq = f"{db}.{schema}.{table}"
    return f"SELECT GET_DDL('TABLE', '{fq}');"


def q_get_proc_ddl(db: str, schema: str, proc_name: str, arg_sig: str) -> str:
    """Return a GET_DDL query for a stored procedure."""
    fq = f"{db}.{schema}.{proc_name}{arg_sig}"
    return f"SELECT GET_DDL('PROCEDURE', '{fq}');"


def q_data_fingerprint(db: str, schema: str, table: str) -> str:
    """Return a query that computes count + hash_agg over all table columns."""
    alias = table
    fq = f"{db}.{schema}.{table}"
    return f"""
SELECT
  '{fq}' AS TABLE_FQN,
  COUNT(*) AS ROW_COUNT,
  HASH_AGG(HASH({alias}.*)) AS HASH_ALL_COLUMNS
FROM {fq} {alias};
""".strip()


# -----------------------------
# Collectors
# -----------------------------
def collect_tables(target: Target, out_dir: Path) -> List[str]:
    """Collect table list snapshot; return list of table names."""
    tsv = run_snow_sql(target, Q_LIST_TABLES)
    write_text(out_dir / "tables.tsv", tsv)
    return parse_single_col_tsv(tsv)


def collect_columns_meta(target: Target, out_dir: Path) -> None:
    """Collect column metadata snapshot."""
    tsv = run_snow_sql(target, Q_COLUMNS_META)
    write_text(out_dir / "columns_meta.tsv", tsv)


def collect_table_ddls(
    left: Target,
    right: Target,
    tables: List[str],
    left_dir: Path,
    right_dir: Path,
) -> None:
    """Collect table DDL snapshots for both targets."""
    for t in tables:
        lf = left_dir / "table_ddls" / f"{safe_name(t)}.sql"
        rf = right_dir / "table_ddls" / f"{safe_name(t)}.sql"

        lout = run_snow_sql(left, q_get_table_ddl(left.database, left.schema, t))
        rout = run_snow_sql(right, q_get_table_ddl(right.database, right.schema, t))

        if lout.startswith("__ERROR__"):
            lout = f"-- missing or error on LEFT: {left.database}.{left.schema}.{t}\n{lout}"
        if rout.startswith("__ERROR__"):
            rout = f"-- missing or error on RIGHT: {right.database}.{right.schema}.{t}\n{rout}"

        write_text(lf, lout)
        write_text(rf, rout)


def collect_data_fingerprints(
    left: Target,
    right: Target,
    tables: List[str],
    left_dir: Path,
    right_dir: Path,
) -> None:
    """Collect data fingerprints for both targets."""
    for t in tables:
        lf = left_dir / "data" / f"{safe_name(t)}.tsv"
        rf = right_dir / "data" / f"{safe_name(t)}.tsv"

        lout = run_snow_sql(left, q_data_fingerprint(left.database, left.schema, t))
        rout = run_snow_sql(right, q_data_fingerprint(right.database, right.schema, t))

        if lout.startswith("__ERROR__"):
            lout = f"{left.database}.{left.schema}.{t}\tMISSING_OR_ERROR\tMISSING_OR_ERROR\n{lout}"
        if rout.startswith("__ERROR__"):
            rout = f"{right.database}.{right.schema}.{t}\tMISSING_OR_ERROR\tMISSING_OR_ERROR\n{rout}"

        write_text(lf, lout)
        write_text(rf, rout)


def collect_procs(target: Target, out_dir: Path) -> List[Tuple[str, str]]:
    """Collect stored procedure list (name + argument signature)."""
    tsv = run_snow_sql(target, Q_LIST_PROCS)
    write_text(out_dir / "procs.tsv", tsv)

    out: List[Tuple[str, str]] = []
    for line in tsv.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        pname = (parts[0] if len(parts) > 0 else "").strip()
        args = (parts[1] if len(parts) > 1 else "").strip()
        if pname:
            out.append((pname, args))
    return out


def collect_proc_ddls(
    left: Target,
    right: Target,
    procs_union: List[Tuple[str, str]],
    left_dir: Path,
    right_dir: Path,
) -> None:
    """Collect stored procedure DDL snapshots for both targets."""
    for pname, argsig in procs_union:
        key = f"{pname}{argsig}"
        lf = left_dir / "procs" / f"{safe_name(key)}.sql"
        rf = right_dir / "procs" / f"{safe_name(key)}.sql"

        lout = run_snow_sql(left, q_get_proc_ddl(left.database, left.schema, pname, argsig))
        rout = run_snow_sql(right, q_get_proc_ddl(right.database, right.schema, pname, argsig))

        if lout.startswith("__ERROR__"):
            lout = f"-- missing or error on LEFT: {left.database}.{left.schema}.{pname}{argsig}\n{lout}"
        if rout.startswith("__ERROR__"):
            rout = f"-- missing or error on RIGHT: {right.database}.{right.schema}.{pname}{argsig}\n{rout}"

        write_text(lf, lout)
        write_text(rf, rout)


# -----------------------------
# Diff & Summary
# -----------------------------
def write_diff_file(
    out_path: Path,
    left_path: Path,
    right_path: Path,
    label_left: str,
    label_right: str,
) -> bool:
    """Write a unified diff file if differences exist."""
    a = read_text(left_path)
    b = read_text(right_path)
    diff = unified_diff(a, b, fromfile=label_left, tofile=label_right)
    if diff.strip():
        write_text(out_path, diff)
        return True
    return False


def rel_link(from_file: Path, to_file: Path) -> str:
    """Create a relative link from one file to another (portable in markdown)."""
    return os.path.relpath(to_file, start=from_file.parent).replace("\\", "/")


def generate_summary_md(out_dir: Path, header: List[str], sections: List[Tuple[str, List[Path]]]) -> None:
    """Generate a Markdown summary containing links to diff files."""
    summary_path = out_dir / "SUMMARY.md"
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: List[str] = []
    lines.append("# Snowflake Diff Summary\n\n")
    lines.append(f"_Generated: {now}_\n\n")
    if header:
        lines.extend([h + "\n" for h in header])
        lines.append("\n")

    lines.append("## Contents\n")
    for title, _ in sections:
        anchor = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        lines.append(f"- [{title}](#{anchor})\n")
    lines.append("\n")

    for title, files in sections:
        lines.append(f"## {title}\n\n")
        if not files:
            lines.append("- ✅ No differences\n\n")
            continue
        for f in sorted(files):
            link = rel_link(summary_path, f)
            lines.append(f"- [{f.name}]({link})\n")
        lines.append("\n")

    write_text(summary_path, "".join(lines))


# -----------------------------
# Entry point
# -----------------------------
def main() -> None:
    """Run the CLI entry-point."""
    ensure_cmd("snow")

    ap = argparse.ArgumentParser(
        description="Snowflake diff via SnowCLI (snow sql) with YAML config + Markdown summary + table include/exclude filters."
    )
    ap.add_argument("--config", default="config.yml", help="Path to config.yml (default: config.yml)")
    ap.add_argument("--out", default=None, help="Override out_dir from config")

    # toggles
    ap.add_argument("--no-schema", action="store_true", help="Disable column metadata diff")
    ap.add_argument("--no-table-ddl", action="store_true", help="Disable table DDL diff")
    ap.add_argument("--no-data", action="store_true", help="Disable data fingerprints diff")
    ap.add_argument("--no-procs", action="store_true", help="Disable stored procedure DDL diff")

    # include/exclude table filters (repeatable)
    ap.add_argument(
        "--include",
        action="append",
        default=[],
        help="Include table pattern (repeatable). SQL LIKE (% _) or regex via re:... e.g. --include 'FACT_%'",
    )
    ap.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude table pattern (repeatable). SQL LIKE (% _) or regex via re:... e.g. --exclude 'TMP_%'",
    )

    # optional overrides (override config from CLI)
    for side in ("left", "right"):
        ap.add_argument(f"--{side}-account", default=None)
        ap.add_argument(f"--{side}-user", default=None)
        ap.add_argument(f"--{side}-auth", default=None)
        ap.add_argument(f"--{side}-role", default=None)
        ap.add_argument(f"--{side}-warehouse", default=None)
        ap.add_argument(f"--{side}-db", default=None)
        ap.add_argument(f"--{side}-schema", default=None)

    args = ap.parse_args()

    cfg_path = Path(args.config).resolve()
    cfg = load_yaml(cfg_path)

    out_dir_cfg = cfg.get("out_dir", "out")
    out_root = Path(args.out or out_dir_cfg).resolve()

    # options defaults from config
    opt_schema = bool(deep_get(cfg, ["options", "schema"], True))
    opt_table_ddl = bool(deep_get(cfg, ["options", "table_ddl"], True))
    opt_data = bool(deep_get(cfg, ["options", "data"], True))
    opt_procs = bool(deep_get(cfg, ["options", "procs"], True))

    # CLI "no-*" overrides
    if args.no_schema:
        opt_schema = False
    if args.no_table_ddl:
        opt_table_ddl = False
    if args.no_data:
        opt_data = False
    if args.no_procs:
        opt_procs = False

    # table filters from config + CLI
    cfg_includes = deep_get(cfg, ["table_filter", "include"], []) or []
    cfg_excludes = deep_get(cfg, ["table_filter", "exclude"], []) or []
    # CLI patterns extend config patterns
    includes = list(cfg_includes) + list(args.include or [])
    excludes = list(cfg_excludes) + list(args.exclude or [])

    def build_target(side: str) -> Target:
        scfg = cfg.get(side, {}) or {}
        auth_cfg = scfg.get("authenticator", scfg.get("auth", "externalbrowser"))
        return Target(
            account=pick(getattr(args, f"{side}_account"), scfg.get("account"), f"{side}.account"),
            user=pick(getattr(args, f"{side}_user"), scfg.get("user"), f"{side}.user"),
            auth=pick(getattr(args, f"{side}_auth"), auth_cfg, f"{side}.authenticator"),
            role=pick(getattr(args, f"{side}_role"), scfg.get("role"), f"{side}.role"),
            warehouse=pick(getattr(args, f"{side}_warehouse"), scfg.get("warehouse"), f"{side}.warehouse"),
            database=pick(getattr(args, f"{side}_db"), scfg.get("database"), f"{side}.database"),
            schema=pick(getattr(args, f"{side}_schema"), scfg.get("schema"), f"{side}.schema"),
            label=side,
        )

    left = build_target("left")
    right = build_target("right")

    snapshots = out_root / "snapshots"
    diffs_dir = out_root / "diffs"
    left_snap = snapshots / "left"
    right_snap = snapshots / "right"

    left_snap.mkdir(parents=True, exist_ok=True)
    right_snap.mkdir(parents=True, exist_ok=True)
    diffs_dir.mkdir(parents=True, exist_ok=True)

    report_path = out_root / "report.txt"
    report_lines: List[str] = []
    report_lines.append("== Snowflake Diff Report ==\n")
    report_lines.append(f"Config: {cfg_path}\n")
    report_lines.append(left.describe() + "\n")
    report_lines.append(right.describe() + "\n")
    report_lines.append(f"Options: schema={opt_schema} table_ddl={opt_table_ddl} data={opt_data} procs={opt_procs}\n")
    report_lines.append(f"Table filters: include={includes if includes else '[]'} exclude={excludes if excludes else '[]'}\n\n")

    # Collect
    print("Collecting table lists...")
    left_tables = collect_tables(left, left_snap)
    right_tables = collect_tables(right, right_snap)
    tables_union = list_union(left_tables, right_tables)

    # Apply include/exclude filtering on the union
    tables_union_filtered = filter_tables(tables_union, includes, excludes)

    # Write filtered list snapshot (for traceability)
    write_text(left_snap / "tables_filtered.tsv", "\n".join(tables_union_filtered) + ("\n" if tables_union_filtered else ""))
    write_text(right_snap / "tables_filtered.tsv", "\n".join(tables_union_filtered) + ("\n" if tables_union_filtered else ""))

    if opt_schema:
        print("Collecting column metadata...")
        collect_columns_meta(left, left_snap)
        collect_columns_meta(right, right_snap)

    if opt_table_ddl:
        print(f"Collecting table DDLs for {len(tables_union_filtered)} table(s)...")
        collect_table_ddls(left, right, tables_union_filtered, left_snap, right_snap)

    if opt_data:
        print(f"Collecting data fingerprints for {len(tables_union_filtered)} table(s) (can be expensive)...")
        collect_data_fingerprints(left, right, tables_union_filtered, left_snap, right_snap)

    procs_union: List[Tuple[str, str]] = []
    if opt_procs:
        print("Collecting stored procedures and DDLs...")
        left_procs = collect_procs(left, left_snap)
        right_procs = collect_procs(right, right_snap)
        procs_union = sorted(set(left_procs) | set(right_procs))
        collect_proc_ddls(left, right, procs_union, left_snap, right_snap)

    # Diff + Summary
    summary_sections: List[Tuple[str, List[Path]]] = []

    # Table list diff (unfiltered raw lists)
    print("Diffing table list (raw)...")
    tables_diff_path = diffs_dir / "tables_list.diff"
    has_tables_diff = write_diff_file(
        tables_diff_path,
        left_snap / "tables.tsv",
        right_snap / "tables.tsv",
        "left/tables.tsv",
        "right/tables.tsv",
    )
    summary_sections.append(("Table list (raw)", [tables_diff_path] if has_tables_diff else []))
    report_lines.append(f"Table list diff (raw): {'FOUND' if has_tables_diff else 'none'} -> diffs/tables_list.diff\n")

    # Filtered table list diff (same file both sides, but still useful to show what ran)
    print("Writing filtered table set info...")
    filtered_list_path = diffs_dir / "tables_filtered.txt"
    write_text(filtered_list_path, "\n".join(tables_union_filtered) + ("\n" if tables_union_filtered else ""))
    summary_sections.append(("Tables compared (filtered set)", [filtered_list_path]))
    report_lines.append(f"Tables compared (filtered set): {len(tables_union_filtered)} -> diffs/tables_filtered.txt\n")

    # Columns meta diff (still global; not filtered by table list)
    if opt_schema:
        print("Diffing column metadata...")
        cols_diff_path = diffs_dir / "columns_meta.diff"
        has_cols_diff = write_diff_file(
            cols_diff_path,
            left_snap / "columns_meta.tsv",
            right_snap / "columns_meta.tsv",
            "left/columns_meta.tsv",
            "right/columns_meta.tsv",
        )
        summary_sections.append(("Column metadata (entire schema)", [cols_diff_path] if has_cols_diff else []))
        report_lines.append(f"Column metadata diff: {'FOUND' if has_cols_diff else 'none'} -> diffs/columns_meta.diff\n")

    # Table DDL diffs
    if opt_table_ddl:
        print("Diffing table DDLs...")
        table_ddl_diffs: List[Path] = []
        out_table_ddls = diffs_dir / "table_ddls"
        out_table_ddls.mkdir(parents=True, exist_ok=True)

        for t in tables_union_filtered:
            lf = left_snap / "table_ddls" / f"{safe_name(t)}.sql"
            rf = right_snap / "table_ddls" / f"{safe_name(t)}.sql"
            od = out_table_ddls / f"{safe_name(t)}.diff"
            if write_diff_file(od, lf, rf, f"left/table_ddls/{t}.sql", f"right/table_ddls/{t}.sql"):
                table_ddl_diffs.append(od)

        summary_sections.append(("Table DDLs", table_ddl_diffs))
        report_lines.append(f"Table DDL diffs: {len(table_ddl_diffs)} file(s) -> diffs/table_ddls/\n")

    # Data fingerprint diffs
    if opt_data:
        print("Diffing data fingerprints...")
        data_diffs: List[Path] = []
        out_data = diffs_dir / "data"
        out_data.mkdir(parents=True, exist_ok=True)

        for t in tables_union_filtered:
            lf = left_snap / "data" / f"{safe_name(t)}.tsv"
            rf = right_snap / "data" / f"{safe_name(t)}.tsv"
            od = out_data / f"{safe_name(t)}.diff"
            if write_diff_file(od, lf, rf, f"left/data/{t}.tsv", f"right/data/{t}.tsv"):
                data_diffs.append(od)

        summary_sections.append(("Data fingerprints", data_diffs))
        report_lines.append(f"Data fingerprint diffs: {len(data_diffs)} file(s) -> diffs/data/\n")

    # Procedure diffs
    if opt_procs:
        print("Diffing stored procedures...")
        proc_diffs: List[Path] = []
        out_procs = diffs_dir / "procs"
        out_procs.mkdir(parents=True, exist_ok=True)

        for pname, argsig in procs_union:
            key = f"{pname}{argsig}"
            lf = left_snap / "procs" / f"{safe_name(key)}.sql"
            rf = right_snap / "procs" / f"{safe_name(key)}.sql"
            od = out_procs / f"{safe_name(key)}.diff"
            if write_diff_file(od, lf, rf, f"left/procs/{key}.sql", f"right/procs/{key}.sql"):
                proc_diffs.append(od)

        summary_sections.append(("Stored procedures", proc_diffs))
        report_lines.append(f"Stored procedure diffs: {len(proc_diffs)} file(s) -> diffs/procs/\n")

    # Write outputs
    write_text(report_path, "".join(report_lines))

    header = [
        f"- Config: `{cfg_path.name}`",
        f"- {left.describe()}",
        f"- {right.describe()}",
        f"- Options: schema={opt_schema} table_ddl={opt_table_ddl} data={opt_data} procs={opt_procs}",
        f"- Table filters: include={includes if includes else '[]'} exclude={excludes if excludes else '[]'}",
        f"- Tables compared (filtered): {len(tables_union_filtered)}",
    ]
    generate_summary_md(out_root, header, summary_sections)

    print("\nDone.")
    print(f"Report : {report_path}")
    print(f"Summary: {out_root / 'SUMMARY.md'}")
    print(f"Diffs  : {diffs_dir}")


if __name__ == "__main__":
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10+ required.")
    main()
