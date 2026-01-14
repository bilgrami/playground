"""
snowdiff
========

CLI entry point for the Snowflake drift/diff tool.

This module is intentionally thin. It:
- loads config
- builds two :class:`scripts.auth.SnowTarget` objects
- runs snapshot collectors from :mod:`scripts.collectors`
- writes diffs using :mod:`scripts.diffing`
- generates a Markdown report using :mod:`scripts.reporting`

Usage
-----
Run a connection test:

.. code-block:: bash

   python3 scripts/snowdiff.py --config config.yml connect-test

Run a diff:

.. code-block:: bash

   python3 scripts/snowdiff.py --config config.yml diff --out out

Sphinx autodoc
--------------
You can document this CLI module (and the rest) using Sphinx autodoc. See the
repository README for a minimal working configuration.

"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from scripts.auth import SnowTarget, connection_test, ensure_snowcli
from scripts.collectors import (
    CommentCollection,
    Options,
    TableFilter,
    collect_columns_meta,
    collect_column_comments_account_usage,
    collect_column_comments_desc,
    collect_comments_and_metadata_from_show,
    collect_data_fingerprints,
    collect_procs_list,
    collect_proc_ddls,
    collect_show_outputs,
    collect_table_ddls,
    collect_table_list,
    filter_tables,
)
from scripts.diffing import write_diff_file, write_text
from scripts.reporting import generate_summary_md
from scripts.utils import safe_name


def deep_get(d: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """Safely get nested values from a dict."""
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def load_config(path: Path) -> Dict[str, Any]:
    """Load YAML config file."""
    if not path.exists():
        raise SystemExit(f"ERROR: config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_target(cfg: Dict[str, Any], side: str, overrides: Dict[str, str]) -> SnowTarget:
    """Build a SnowTarget from config + CLI overrides.

    Config expects:
      - <side>.connection (SnowCLI connection name)
      - <side>.role, warehouse, database, schema
    """
    scfg = cfg.get(side, {}) or {}

    connection = overrides.get(f"{side}_connection") or scfg.get("connection")
    if not connection:
        raise SystemExit(f"ERROR: missing {side}.connection in config (SnowCLI connection name).")

    def pick(field: str) -> str:
        v = overrides.get(f"{side}_{field}") or scfg.get(field)
        if not v:
            raise SystemExit(f"ERROR: missing {side}.{field} in config.")
        return v

    return SnowTarget(
        connection=connection,
        role=pick("role"),
        warehouse=pick("warehouse"),
        database=pick("database"),
        schema=pick("schema"),
        label=side,
    )


def read_options(cfg: Dict[str, Any], args: argparse.Namespace) -> Options:
    """Create Options from config + disable flags."""
    opt = Options(
        schema=bool(deep_get(cfg, ["options", "schema"], True)),
        table_ddl=bool(deep_get(cfg, ["options", "table_ddl"], True)),
        data=bool(deep_get(cfg, ["options", "data"], True)),
        procs=bool(deep_get(cfg, ["options", "procs"], True)),
        comments=bool(deep_get(cfg, ["options", "comments"], True)),
        last_changed=bool(deep_get(cfg, ["options", "last_changed"], True)),
    )

    updated = asdict(opt)
    if args.no_schema:
        updated["schema"] = False
    if args.no_table_ddl:
        updated["table_ddl"] = False
    if args.no_data:
        updated["data"] = False
    if args.no_procs:
        updated["procs"] = False
    if args.no_comments:
        updated["comments"] = False
    if args.no_last_changed:
        updated["last_changed"] = False

    return Options(**updated)


def read_table_filter(cfg: Dict[str, Any], args: argparse.Namespace) -> TableFilter:
    """Create TableFilter from config + CLI patterns."""
    cfg_incl = deep_get(cfg, ["table_filter", "include"], []) or []
    cfg_excl = deep_get(cfg, ["table_filter", "exclude"], []) or []
    incl = list(cfg_incl) + list(args.include or [])
    excl = list(cfg_excl) + list(args.exclude or [])
    return TableFilter(include=incl, exclude=excl)


def read_comment_collection(cfg: Dict[str, Any], args: argparse.Namespace) -> CommentCollection:
    """Create CommentCollection from config + CLI overrides."""
    cfg_mode = deep_get(cfg, ["comment_collection", "column_mode"], "desc")
    mode = args.column_comment_mode or cfg_mode
    if mode not in ("desc", "account_usage"):
        mode = "desc"
    return CommentCollection(column_mode=mode)


def cmd_connect_test(left: SnowTarget, right: SnowTarget) -> int:
    """Execute a simple left/right connection test."""
    ok_l, msg_l = connection_test(left)
    ok_r, msg_r = connection_test(right)

    print(f"[LEFT  {left.connection}] OK={ok_l}\n{msg_l}\n")
    print(f"[RIGHT {right.connection}] OK={ok_r}\n{msg_r}\n")

    return 0 if ok_l and ok_r else 1


def cmd_diff(
    cfg_path: Path,
    out_dir: Path,
    left: SnowTarget,
    right: SnowTarget,
    opt: Options,
    tf: TableFilter,
    cc: CommentCollection,
) -> int:
    """Run snapshot collection + diff generation + Markdown summary."""
    out_root = out_dir.resolve()
    diffs_dir = out_root / "diffs"
    snaps_dir = out_root / "snapshots"
    left_snap = snaps_dir / "left"
    right_snap = snaps_dir / "right"

    for p in (diffs_dir, left_snap, right_snap):
        p.mkdir(parents=True, exist_ok=True)

    # ----------------------------
    # Report header lines
    # ----------------------------
    report_lines: List[str] = []
    report_lines.append("== Snowflake Diff Report ==\n")
    report_lines.append(f"Config: {cfg_path}\n")
    report_lines.append(
        f"LEFT : connection={left.connection} role={left.role} db={left.database} schema={left.schema} wh={left.warehouse}\n"
    )
    report_lines.append(
        f"RIGHT: connection={right.connection} role={right.role} db={right.database} schema={right.schema} wh={right.warehouse}\n"
    )
    report_lines.append(f"Options: {opt}\n")
    report_lines.append(f"Table filters: include={tf.include if tf.include else '[]'} exclude={tf.exclude if tf.exclude else '[]'}\n")
    report_lines.append(f"Column comment mode: {cc.column_mode}\n\n")

    # ----------------------------
    # Collect core snapshots
    # ----------------------------
    print("Collecting table lists...")
    left_tables = collect_table_list(left, left_snap)
    right_tables = collect_table_list(right, right_snap)
    tables_union = sorted(set(left_tables) | set(right_tables))
    tables_filtered = filter_tables(tables_union, tf.include, tf.exclude)

    write_text(left_snap / "tables_filtered.tsv", "\n".join(tables_filtered) + ("\n" if tables_filtered else ""))
    write_text(right_snap / "tables_filtered.tsv", "\n".join(tables_filtered) + ("\n" if tables_filtered else ""))

    if opt.schema:
        print("Collecting column metadata...")
        collect_columns_meta(left, left_snap)
        collect_columns_meta(right, right_snap)

    if opt.table_ddl:
        print(f"Collecting table DDLs for {len(tables_filtered)} table(s)...")
        collect_table_ddls(left, right, tables_filtered, left_snap, right_snap)

    if opt.data:
        print(f"Collecting data fingerprints for {len(tables_filtered)} table(s) (can be expensive)...")
        collect_data_fingerprints(left, right, tables_filtered, left_snap, right_snap)

    procs_union: List[Tuple[str, str]] = []
    if opt.procs:
        print("Collecting procedure lists + DDLs...")
        left_procs = collect_procs_list(left, left_snap)
        right_procs = collect_procs_list(right, right_snap)
        procs_union = sorted(set(left_procs) | set(right_procs))
        collect_proc_ddls(left, right, procs_union, left_snap, right_snap)

    # ----------------------------
    # Collect comments + metadata snapshots
    # ----------------------------
    if opt.comments or opt.last_changed:
        print("Collecting SHOW outputs (tables/views/procs) for comments/metadata...")
        l_show = collect_show_outputs(left, left_snap)
        r_show = collect_show_outputs(right, right_snap)
        collect_comments_and_metadata_from_show(left_snap, l_show)
        collect_comments_and_metadata_from_show(right_snap, r_show)

        if opt.comments:
            if cc.column_mode == "desc":
                print("Collecting column comments via DESC TABLE...")
                collect_column_comments_desc(left, left_snap, tables_filtered)
                collect_column_comments_desc(right, right_snap, tables_filtered)
            else:
                print("Collecting column comments via ACCOUNT_USAGE.COLUMNS...")
                collect_column_comments_account_usage(left, left_snap)
                collect_column_comments_account_usage(right, right_snap)

    # ----------------------------
    # Produce diffs
    # ----------------------------
    summary_sections: List[Tuple[str, List[Path]]] = []

    print("Diffing table list (raw)...")
    tables_list_diff = diffs_dir / "tables_list.diff"
    has = write_diff_file(
        tables_list_diff,
        left_snap / "tables.tsv",
        right_snap / "tables.tsv",
        "left/tables.tsv",
        "right/tables.tsv",
    )
    summary_sections.append(("Table list (raw)", [tables_list_diff] if has else []))

    filtered_list = diffs_dir / "tables_filtered.txt"
    write_text(filtered_list, "\n".join(tables_filtered) + ("\n" if tables_filtered else ""))
    summary_sections.append(("Tables compared (filtered set)", [filtered_list]))

    if opt.schema:
        print("Diffing column metadata...")
        d = diffs_dir / "columns_meta.diff"
        has = write_diff_file(
            d,
            left_snap / "columns_meta.tsv",
            right_snap / "columns_meta.tsv",
            "left/columns_meta.tsv",
            "right/columns_meta.tsv",
        )
        summary_sections.append(("Column metadata (entire schema)", [d] if has else []))

    if opt.table_ddl:
        print("Diffing table DDLs...")
        out = diffs_dir / "table_ddls"
        out.mkdir(parents=True, exist_ok=True)
        ddls: List[Path] = []
        for t in tables_filtered:
            filename = f"{safe_name(t)}.sql"
            diffname = f"{safe_name(t)}.diff"
            lf = left_snap / "table_ddls" / filename
            rf = right_snap / "table_ddls" / filename
            od = out / diffname
            if write_diff_file(od, lf, rf, f"left/table_ddls/{t}.sql", f"right/table_ddls/{t}.sql"):
                ddls.append(od)
        summary_sections.append(("Table DDLs", ddls))

    if opt.data:
        print("Diffing data fingerprints...")
        out = diffs_dir / "data"
        out.mkdir(parents=True, exist_ok=True)
        dfs: List[Path] = []
        for t in tables_filtered:
            filename = f"{safe_name(t)}.tsv"
            diffname = f"{safe_name(t)}.diff"
            lf = left_snap / "data" / filename
            rf = right_snap / "data" / filename
            od = out / diffname
            if write_diff_file(od, lf, rf, f"left/data/{t}.tsv", f"right/data/{t}.tsv"):
                dfs.append(od)
        summary_sections.append(("Data fingerprints", dfs))

    if opt.procs:
        print("Diffing procedure DDLs...")
        out = diffs_dir / "procs"
        out.mkdir(parents=True, exist_ok=True)
        pds: List[Path] = []
        for pname, argsig in procs_union:
            key = f"{pname}{argsig}"
            filename = f"{safe_name(key)}.sql"
            diffname = f"{safe_name(key)}.diff"
            lf = left_snap / "procs" / filename
            rf = right_snap / "procs" / filename
            od = out / diffname
            if write_diff_file(od, lf, rf, f"left/procs/{key}.sql", f"right/procs/{key}.sql"):
                pds.append(od)
        summary_sections.append(("Stored procedures (DDL)", pds))

    if opt.comments:
        print("Diffing comments (from SHOW reduced snapshot)...")
        d = diffs_dir / "comments_show.diff"
        has = write_diff_file(
            d,
            left_snap / "comments_and_metadata_from_show.tsv",
            right_snap / "comments_and_metadata_from_show.tsv",
            "left/comments_and_metadata_from_show.tsv",
            "right/comments_and_metadata_from_show.tsv",
        )
        summary_sections.append(("Comments (tables/views/procs from SHOW)", [d] if has else []))

        if cc.column_mode == "desc":
            d2 = diffs_dir / "column_comments_desc.diff"
            has2 = write_diff_file(
                d2,
                left_snap / "column_comments_desc.tsv",
                right_snap / "column_comments_desc.tsv",
                "left/column_comments_desc.tsv",
                "right/column_comments_desc.tsv",
            )
            summary_sections.append(("Column comments (DESC TABLE)", [d2] if has2 else []))
        else:
            d2 = diffs_dir / "column_comments_account_usage.diff"
            has2 = write_diff_file(
                d2,
                left_snap / "column_comments_account_usage.tsv",
                right_snap / "column_comments_account_usage.tsv",
                "left/column_comments_account_usage.tsv",
                "right/column_comments_account_usage.tsv",
            )
            summary_sections.append(("Column comments (ACCOUNT_USAGE)", [d2] if has2 else []))

    if opt.last_changed:
        print("Diffing last-changed metadata (from SHOW reduced snapshot)...")
        d = diffs_dir / "last_changed_show.diff"
        has = write_diff_file(
            d,
            left_snap / "comments_and_metadata_from_show.tsv",
            right_snap / "comments_and_metadata_from_show.tsv",
            "left/comments_and_metadata_from_show.tsv",
            "right/comments_and_metadata_from_show.tsv",
        )
        summary_sections.append(("Last changed metadata (from SHOW)", [d] if has else []))

    report_path = out_root / "report.txt"
    write_text(report_path, "".join(report_lines))

    header_lines = [
        f"- Config: `{cfg_path.name}`",
        f"- LEFT connection: `{left.connection}` (role={left.role}, db={left.database}, schema={left.schema})",
        f"- RIGHT connection: `{right.connection}` (role={right.role}, db={right.database}, schema={right.schema})",
        f"- Options: schema={opt.schema} table_ddl={opt.table_ddl} data={opt.data} procs={opt.procs} comments={opt.comments} last_changed={opt.last_changed}",
        f"- Table filters: include={tf.include if tf.include else '[]'} exclude={tf.exclude if tf.exclude else '[]'}",
        f"- Column comment mode: {cc.column_mode}",
        f"- Tables compared (filtered): {len(tables_filtered)}",
    ]
    summary_path = generate_summary_md(out_root, header_lines, summary_sections)

    print("\nDone.")
    print(f"Summary: {summary_path}")
    print(f"Report : {report_path}")
    print(f"Diffs  : {diffs_dir}")
    print(f"Snaps  : {snaps_dir}")
    return 0


def main() -> None:
    """Parse CLI args and dispatch commands."""
    ensure_snowcli()

    ap = argparse.ArgumentParser(
        prog="snowdiff",
        description="Snowflake drift diff via SnowCLI connections + YAML config.",
    )
    ap.add_argument("--config", default="config.yml", help="Path to config.yml")

    # global toggles for diff
    ap.add_argument("--no-schema", action="store_true")
    ap.add_argument("--no-table-ddl", action="store_true")
    ap.add_argument("--no-data", action="store_true")
    ap.add_argument("--no-procs", action="store_true")
    ap.add_argument("--no-comments", action="store_true")
    ap.add_argument("--no-last-changed", action="store_true")

    # filters
    ap.add_argument("--include", action="append", default=[], help="Include table pattern (repeatable)")
    ap.add_argument("--exclude", action="append", default=[], help="Exclude table pattern (repeatable)")
    ap.add_argument("--column-comment-mode", choices=["desc", "account_usage"], default=None)

    # overrides
    for side in ("left", "right"):
        ap.add_argument(f"--{side}-connection", default=None)
        ap.add_argument(f"--{side}-role", default=None)
        ap.add_argument(f"--{side}-warehouse", default=None)
        ap.add_argument(f"--{side}-db", default=None)
        ap.add_argument(f"--{side}-schema", default=None)

    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("connect-test", help="Test SnowCLI connections for left/right")

    diffp = sub.add_parser("diff", help="Run diff according to config/options")
    diffp.add_argument("--out", default=None, help="Override output directory (default uses config out_dir)")

    args = ap.parse_args()
    cfg_path = Path(args.config).resolve()
    cfg = load_config(cfg_path)

    # CLI overrides mapping
    def normalize_overrides(side: str) -> dict[str, str]:
        m: dict[str, str] = {}
        for k in ("connection", "role", "warehouse", "schema"):
            v = getattr(args, f"{side}_{k}")
            if v:
                m[f"{side}_{k}"] = v
        vdb = getattr(args, f"{side}_db")
        if vdb:
            m[f"{side}_database"] = vdb
        return m

    overrides = {**normalize_overrides("left"), **normalize_overrides("right")}

    # Build targets
    left = build_target(cfg, "left", overrides)
    right = build_target(cfg, "right", overrides)

    if args.command == "connect-test":
        raise SystemExit(cmd_connect_test(left, right))

    # Diff command
    opt = read_options(cfg, args)
    tf = read_table_filter(cfg, args)
    cc = read_comment_collection(cfg, args)
    out_dir = Path(getattr(args, "out", None) or cfg.get("out_dir", "out"))

    raise SystemExit(cmd_diff(cfg_path, out_dir, left, right, opt, tf, cc))


if __name__ == "__main__":
    import sys

    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10+ required.")
    main()
