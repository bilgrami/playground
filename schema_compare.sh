#!/usr/bin/env bash
# snowflake_diff.sh
#
# Compares TWO Snowflake targets (db/schema/role) for:
#   1) TABLE schema (columns: name/type/nullable/default)
#   2) TABLE DDL (GET_DDL)
#   3) TABLE data fingerprints (row_count + HASH_AGG over all columns)
#   4) STORED PROCEDURES DDL (GET_DDL)
#
# Requires:
#   - Snowflake CLI: `snow sql ...` (SnowCLI)
#   - `diff`, `mktemp`, `sed`, `awk` available (macOS/Linux OK)
#
# Notes:
# - Data fingerprints are deterministic only if table contents are stable. If rows are changing, hashes will differ.
# - For very large tables, data hashing can be expensive. You can disable it with --no-data.
#
# Usage example:
#   ./snowflake_diff.sh \
#     --left-account ACCT --left-user ME --left-auth externalbrowser --left-role ROLE_A --left-db DB_A --left-schema SCHEMA_A --left-warehouse WH \
#     --right-account ACCT --right-user ME --right-auth externalbrowser --right-role ROLE_B --right-db DB_B --right-schema SCHEMA_B --right-warehouse WH \
#     --out ./diff_out
#
set -euo pipefail

########################################
# Helpers
########################################
die(){ echo "ERROR: $*" >&2; exit 1; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"; }

# Run snow sql and return TSV without headers
snow_sql() {
  local account="$1" user="$2" auth="$3" role="$4" warehouse="$5" database="$6" schema="$7" query="$8"
  # `snow sql` flags vary slightly by version; these are common.
  # If your SnowCLI uses different flags, adjust here.
  snow sql \
    --account "$account" \
    --user "$user" \
    --authenticator "$auth" \
    --role "$role" \
    --warehouse "$warehouse" \
    --database "$database" \
    --schema "$schema" \
    --query "$query" \
    --format tsv \
    --header false
}

# Safe filename
safe_name() {
  echo "$1" | sed 's/[^A-Za-z0-9._-]/_/g'
}

########################################
# Args
########################################
OUT_DIR="./snowflake_diff_out"
DO_DATA=1
DO_TABLE_DDL=1
DO_SCHEMA=1
DO_PROCS=1

# Left target
L_ACCOUNT="" L_USER="" L_AUTH="externalbrowser" L_ROLE="" L_WH="" L_DB="" L_SCHEMA=""

# Right target
R_ACCOUNT="" R_USER="" R_AUTH="externalbrowser" R_ROLE="" R_WH="" R_DB="" R_SCHEMA=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT_DIR="$2"; shift 2;;
    --no-data) DO_DATA=0; shift;;
    --no-table-ddl) DO_TABLE_DDL=0; shift;;
    --no-schema) DO_SCHEMA=0; shift;;
    --no-procs) DO_PROCS=0; shift;;

    --left-account) L_ACCOUNT="$2"; shift 2;;
    --left-user) L_USER="$2"; shift 2;;
    --left-auth) L_AUTH="$2"; shift 2;;
    --left-role) L_ROLE="$2"; shift 2;;
    --left-warehouse) L_WH="$2"; shift 2;;
    --left-db) L_DB="$2"; shift 2;;
    --left-schema) L_SCHEMA="$2"; shift 2;;

    --right-account) R_ACCOUNT="$2"; shift 2;;
    --right-user) R_USER="$2"; shift 2;;
    --right-auth) R_AUTH="$2"; shift 2;;
    --right-role) R_ROLE="$2"; shift 2;;
    --right-warehouse) R_WH="$2"; shift 2;;
    --right-db) R_DB="$2"; shift 2;;
    --right-schema) R_SCHEMA="$2"; shift 2;;

    -h|--help)
      cat <<EOF
Snowflake DB/Schema diff using SnowCLI (snow sql)

Required (LEFT):
  --left-account --left-user --left-role --left-warehouse --left-db --left-schema
Optional:
  --left-auth (default: externalbrowser)

Required (RIGHT):
  --right-account --right-user --right-role --right-warehouse --right-db --right-schema
Optional:
  --right-auth (default: externalbrowser)

Output:
  --out DIR (default: ./snowflake_diff_out)

Disable parts:
  --no-schema --no-table-ddl --no-data --no-procs

EOF
      exit 0
      ;;
    *) die "Unknown arg: $1";;
  esac
done

# Validate
need_cmd snow
need_cmd diff
need_cmd mktemp
need_cmd sed
need_cmd awk

[[ -n "$L_ACCOUNT" && -n "$L_USER" && -n "$L_ROLE" && -n "$L_WH" && -n "$L_DB" && -n "$L_SCHEMA" ]] || die "Missing LEFT args. Run with --help."
[[ -n "$R_ACCOUNT" && -n "$R_USER" && -n "$R_ROLE" && -n "$R_WH" && -n "$R_DB" && -n "$R_SCHEMA" ]] || die "Missing RIGHT args. Run with --help."

mkdir -p "$OUT_DIR"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

L_DIR="$WORK/left"
R_DIR="$WORK/right"
mkdir -p "$L_DIR" "$R_DIR"

REPORT="$OUT_DIR/report.txt"
: > "$REPORT"

echo "Writing output to: $OUT_DIR"
echo "Temporary work dir: $WORK"

########################################
# Queries
########################################
# List base tables (exclude views)
Q_LIST_TABLES="
SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = CURRENT_SCHEMA()
  AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;
"

# Column metadata snapshot
Q_COLUMNS_META='
SELECT
  TABLE_NAME,
  ORDINAL_POSITION,
  COLUMN_NAME,
  DATA_TYPE,
  COALESCE(CHARACTER_MAXIMUM_LENGTH::STRING, '''') AS CHAR_LEN,
  COALESCE(NUMERIC_PRECISION::STRING, '''') AS NUM_PREC,
  COALESCE(NUMERIC_SCALE::STRING, '''') AS NUM_SCALE,
  IS_NULLABLE,
  COALESCE(COLUMN_DEFAULT::STRING, '''') AS COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = CURRENT_SCHEMA()
ORDER BY TABLE_NAME, ORDINAL_POSITION;
'

# List procedures with signature-ish info.
# Snowflake PROCEDURES view includes ARGUMENT_SIGNATURE and DATA_TYPE etc.
Q_LIST_PROCS='
SELECT
  PROCEDURE_NAME,
  COALESCE(ARGUMENT_SIGNATURE, '''') AS ARGUMENT_SIGNATURE
FROM INFORMATION_SCHEMA.PROCEDURES
WHERE PROCEDURE_SCHEMA = CURRENT_SCHEMA()
ORDER BY PROCEDURE_NAME, ARGUMENT_SIGNATURE;
'

########################################
# Collect: Tables list
########################################
echo "Collecting table lists..."
snow_sql "$L_ACCOUNT" "$L_USER" "$L_AUTH" "$L_ROLE" "$L_WH" "$L_DB" "$L_SCHEMA" "$Q_LIST_TABLES" > "$L_DIR/tables.tsv" || true
snow_sql "$R_ACCOUNT" "$R_USER" "$R_AUTH" "$R_ROLE" "$R_WH" "$R_DB" "$R_SCHEMA" "$Q_LIST_TABLES" > "$R_DIR/tables.tsv" || true

# Normalize whitespace
sed -i.bak 's/\r$//' "$L_DIR/tables.tsv" "$R_DIR/tables.tsv" 2>/dev/null || true
rm -f "$L_DIR/tables.tsv.bak" "$R_DIR/tables.tsv.bak" 2>/dev/null || true

########################################
# Collect: Schema (columns)
########################################
if [[ "$DO_SCHEMA" -eq 1 ]]; then
  echo "Collecting column metadata..."
  snow_sql "$L_ACCOUNT" "$L_USER" "$L_AUTH" "$L_ROLE" "$L_WH" "$L_DB" "$L_SCHEMA" "$Q_COLUMNS_META" > "$L_DIR/columns_meta.tsv" || true
  snow_sql "$R_ACCOUNT" "$R_USER" "$R_AUTH" "$R_ROLE" "$R_WH" "$R_DB" "$R_SCHEMA" "$Q_COLUMNS_META" > "$R_DIR/columns_meta.tsv" || true
fi

########################################
# Collect: Table DDLs (GET_DDL)
########################################
if [[ "$DO_TABLE_DDL" -eq 1 ]]; then
  echo "Collecting table DDLs..."
  while IFS=$'\t' read -r tname; do
    [[ -z "$tname" ]] && continue
    fq_l="${L_DB}.${L_SCHEMA}.${tname}"
    fq_r="${R_DB}.${R_SCHEMA}.${tname}"

    out_l="$L_DIR/table_ddl_$(safe_name "$tname").sql"
    out_r="$R_DIR/table_ddl_$(safe_name "$tname").sql"

    snow_sql "$L_ACCOUNT" "$L_USER" "$L_AUTH" "$L_ROLE" "$L_WH" "$L_DB" "$L_SCHEMA" \
      "SELECT GET_DDL('TABLE', '${fq_l}');" > "$out_l" 2>/dev/null || echo "-- missing on LEFT: ${fq_l}" > "$out_l"

    snow_sql "$R_ACCOUNT" "$R_USER" "$R_AUTH" "$R_ROLE" "$R_WH" "$R_DB" "$R_SCHEMA" \
      "SELECT GET_DDL('TABLE', '${fq_r}');" > "$out_r" 2>/dev/null || echo "-- missing on RIGHT: ${fq_r}" > "$out_r"
  done < <(sort -u <(cat "$L_DIR/tables.tsv" 2>/dev/null; cat "$R_DIR/tables.tsv" 2>/dev/null))
fi

########################################
# Collect: Data fingerprints (row_count + hash_agg over all columns)
########################################
if [[ "$DO_DATA" -eq 1 ]]; then
  echo "Collecting data fingerprints (may be expensive on large tables)..."
  mkdir -p "$L_DIR/data" "$R_DIR/data"

  # For each table, build a hash expression using the table's columns.
  # We compute: ROW_COUNT and HASH_AGG(HASH(col1, col2, ...))
  # If a table has 0 columns (shouldn't), we skip.
  while IFS=$'\t' read -r tname; do
    [[ -z "$tname" ]] && continue

    # Build column list for left (if table missing left, query will fail; handle)
    build_hash_query() {
      local side="$1" db="$2" schema="$3" table="$4"
      cat <<SQL
WITH cols AS (
  SELECT COLUMN_NAME
  FROM ${db}.INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = '${schema}'
    AND TABLE_NAME = '${table}'
  ORDER BY ORDINAL_POSITION
),
expr AS (
  SELECT LISTAGG('NVL(TO_VARCHAR(' || IDENTIFIER(COLUMN_NAME) || '), ''<NULL>'')', ', ') WITHIN GROUP (ORDER BY COLUMN_NAME) AS col_expr
  FROM cols
)
SELECT
  '${db}.${schema}.${table}' AS TABLE_FQN,
  (SELECT COUNT(*) FROM ${db}.${schema}.${table}) AS ROW_COUNT,
  (SELECT HASH_AGG(HASH(${db}.${schema}.${table}.*)) FROM ${db}.${schema}.${table}) AS HASH_ALL_COLUMNS
;
SQL
    }

    # NOTE: HASH(table.*) is supported in Snowflake to hash a row based on all columns (order-defined).
    # Then HASH_AGG aggregates across rows.
    # If this causes issues in your Snowflake version, tell me and I’ll switch to explicit column hashing.
    ql="
SELECT
  '${L_DB}.${L_SCHEMA}.${tname}' AS TABLE_FQN,
  COUNT(*) AS ROW_COUNT,
  HASH_AGG(HASH(${tname}.*)) AS HASH_ALL_COLUMNS
FROM ${L_DB}.${L_SCHEMA}.${tname} ${tname};
"
    qr="
SELECT
  '${R_DB}.${R_SCHEMA}.${tname}' AS TABLE_FQN,
  COUNT(*) AS ROW_COUNT,
  HASH_AGG(HASH(${tname}.*)) AS HASH_ALL_COLUMNS
FROM ${R_DB}.${R_SCHEMA}.${tname} ${tname};
"

    out_l="$L_DIR/data/$(safe_name "$tname").tsv"
    out_r="$R_DIR/data/$(safe_name "$tname").tsv"

    snow_sql "$L_ACCOUNT" "$L_USER" "$L_AUTH" "$L_ROLE" "$L_WH" "$L_DB" "$L_SCHEMA" "$ql" > "$out_l" 2>/dev/null \
      || echo -e "${L_DB}.${L_SCHEMA}.${tname}\tMISSING_OR_ERROR\tMISSING_OR_ERROR" > "$out_l"

    snow_sql "$R_ACCOUNT" "$R_USER" "$R_AUTH" "$R_ROLE" "$R_WH" "$R_DB" "$R_SCHEMA" "$qr" > "$out_r" 2>/dev/null \
      || echo -e "${R_DB}.${R_SCHEMA}.${tname}\tMISSING_OR_ERROR\tMISSING_OR_ERROR" > "$out_r"
  done < <(sort -u <(cat "$L_DIR/tables.tsv" 2>/dev/null; cat "$R_DIR/tables.tsv" 2>/dev/null))
fi

########################################
# Collect: Stored procedures DDLs
########################################
if [[ "$DO_PROCS" -eq 1 ]]; then
  echo "Collecting stored procedures..."
  snow_sql "$L_ACCOUNT" "$L_USER" "$L_AUTH" "$L_ROLE" "$L_WH" "$L_DB" "$L_SCHEMA" "$Q_LIST_PROCS" > "$L_DIR/procs.tsv" || true
  snow_sql "$R_ACCOUNT" "$R_USER" "$R_AUTH" "$R_ROLE" "$R_WH" "$R_DB" "$R_SCHEMA" "$Q_LIST_PROCS" > "$R_DIR/procs.tsv" || true

  mkdir -p "$L_DIR/procs" "$R_DIR/procs"

  # Union of proc name + argument signature
  sort -u <(cat "$L_DIR/procs.tsv" 2>/dev/null; cat "$R_DIR/procs.tsv" 2>/dev/null) | \
  while IFS=$'\t' read -r pname argsig; do
    [[ -z "$pname" ]] && continue
    # argsig comes like "(ARG1 TYPE, ARG2 TYPE)" or empty.
    # GET_DDL needs fully qualified + signature: db.schema.proc(type, type)
    # We'll attempt to use the argument signature directly after name.
    # If your account returns signature with argument NAMES, Snowflake still accepts it in many cases.
    # If it fails, we’ll need to build a type-only signature.
    sig="${argsig}"
    fq_l="${L_DB}.${L_SCHEMA}.${pname}${sig}"
    fq_r="${R_DB}.${R_SCHEMA}.${pname}${sig}"

    out_l="$L_DIR/procs/proc_$(safe_name "${pname}${sig}").sql"
    out_r="$R_DIR/procs/proc_$(safe_name "${pname}${sig}").sql"

    snow_sql "$L_ACCOUNT" "$L_USER" "$L_AUTH" "$L_ROLE" "$L_WH" "$L_DB" "$L_SCHEMA" \
      "SELECT GET_DDL('PROCEDURE', '${fq_l}');" > "$out_l" 2>/dev/null || echo "-- missing or error on LEFT: ${fq_l}" > "$out_l"

    snow_sql "$R_ACCOUNT" "$R_USER" "$R_AUTH" "$R_ROLE" "$R_WH" "$R_DB" "$R_SCHEMA" \
      "SELECT GET_DDL('PROCEDURE', '${fq_r}');" > "$out_r" 2>/dev/null || echo "-- missing or error on RIGHT: ${fq_r}" > "$out_r"
  done
fi

########################################
# Compare & write diffs
########################################
mkdir -p "$OUT_DIR/diffs"

echo "== Snowflake Diff Report ==" >> "$REPORT"
echo "LEFT : account=$L_ACCOUNT role=$L_ROLE db=$L_DB schema=$L_SCHEMA wh=$L_WH" >> "$REPORT"
echo "RIGHT: account=$R_ACCOUNT role=$R_ROLE db=$R_DB schema=$R_SCHEMA wh=$R_WH" >> "$REPORT"
echo "" >> "$REPORT"

# Table list diff
echo "## Table list diff" >> "$REPORT"
diff -u "$L_DIR/tables.tsv" "$R_DIR/tables.tsv" > "$OUT_DIR/diffs/tables_list.diff" || true
if [[ -s "$OUT_DIR/diffs/tables_list.diff" ]]; then
  echo "  - Differences found: diffs/tables_list.diff" >> "$REPORT"
else
  echo "  - No differences." >> "$REPORT"
fi
echo "" >> "$REPORT"

# Columns meta diff
if [[ "$DO_SCHEMA" -eq 1 ]]; then
  echo "## Column metadata diff" >> "$REPORT"
  diff -u "$L_DIR/columns_meta.tsv" "$R_DIR/columns_meta.tsv" > "$OUT_DIR/diffs/columns_meta.diff" || true
  if [[ -s "$OUT_DIR/diffs/columns_meta.diff" ]]; then
    echo "  - Differences found: diffs/columns_meta.diff" >> "$REPORT"
  else
    echo "  - No differences." >> "$REPORT"
  fi
  echo "" >> "$REPORT"
fi

# Table DDL diffs
if [[ "$DO_TABLE_DDL" -eq 1 ]]; then
  echo "## Table DDL diffs" >> "$REPORT"
  ddl_diff_dir="$OUT_DIR/diffs/table_ddls"
  mkdir -p "$ddl_diff_dir"
  any=0
  for f in "$L_DIR"/table_ddl_*.sql; do
    [[ -e "$f" ]] || continue
    base="$(basename "$f")"
    lf="$f"
    rf="$R_DIR/$base"
    out="$ddl_diff_dir/${base%.sql}.diff"
    diff -u "$lf" "$rf" > "$out" || true
    if [[ -s "$out" ]]; then any=1; fi
  done
  if [[ "$any" -eq 1 ]]; then
    echo "  - Differences found under: diffs/table_ddls/" >> "$REPORT"
  else
    echo "  - No differences." >> "$REPORT"
  fi
  echo "" >> "$REPORT"
fi

# Data fingerprints diff
if [[ "$DO_DATA" -eq 1 ]]; then
  echo "## Data fingerprint diffs (row_count + hash)" >> "$REPORT"
  data_diff_dir="$OUT_DIR/diffs/data"
  mkdir -p "$data_diff_dir"
  any=0
  for f in "$L_DIR"/data/*.tsv; do
    [[ -e "$f" ]] || continue
    base="$(basename "$f")"
    lf="$f"
    rf="$R_DIR/data/$base"
    out="$data_diff_dir/${base%.tsv}.diff"
    diff -u "$lf" "$rf" > "$out" || true
    if [[ -s "$out" ]]; then any=1; fi
  done
  if [[ "$any" -eq 1 ]]; then
    echo "  - Differences found under: diffs/data/" >> "$REPORT"
  else
    echo "  - No differences." >> "$REPORT"
  fi
  echo "" >> "$REPORT"
fi

# Procedure DDL diffs
if [[ "$DO_PROCS" -eq 1 ]]; then
  echo "## Stored procedure DDL diffs" >> "$REPORT"
  proc_diff_dir="$OUT_DIR/diffs/procs"
  mkdir -p "$proc_diff_dir"
  any=0
  for f in "$L_DIR"/procs/proc_*.sql; do
    [[ -e "$f" ]] || continue
    base="$(basename "$f")"
    lf="$f"
    rf="$R_DIR/procs/$base"
    out="$proc_diff_dir/${base%.sql}.diff"
    diff -u "$lf" "$rf" > "$out" || true
    if [[ -s "$out" ]]; then any=1; fi
  done
  if [[ "$any" -eq 1 ]]; then
    echo "  - Differences found under: diffs/procs/" >> "$REPORT"
  else
    echo "  - No differences." >> "$REPORT"
  fi
  echo "" >> "$REPORT"
fi

# Copy raw snapshots too (handy)
mkdir -p "$OUT_DIR/snapshots/left" "$OUT_DIR/snapshots/right"
cp -R "$L_DIR"/* "$OUT_DIR/snapshots/left/" 2>/dev/null || true
cp -R "$R_DIR"/* "$OUT_DIR/snapshots/right/" 2>/dev/null || true

echo "Done."
echo "Report: $REPORT"
echo "Diffs : $OUT_DIR/diffs/"

