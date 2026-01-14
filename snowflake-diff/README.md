# Snowflake Diff (SnowCLI)

A Python-first tool to compare two Snowflake environments (**left** vs **right**) using **SnowCLI** (`snow sql`).
It generates:
- Unified diff files under `out/diffs/`
- A clickable summary: `out/SUMMARY.md`
- A text report: `out/report.txt`
- Raw snapshots for audit: `out/snapshots/{left,right}/`

This is optimized for **drift detection** (dev/stage/prod), not full data reconciliation.

---

## Why “connection names” (SnowCLI profiles)

Instead of embedding credentials (account/user/authenticator), `config.yml` uses:

- `left.connection: <name>`
- `right.connection: <name>`

These names must exist in your SnowCLI configuration (often `snow.toml`).

---

## Requirements

- Python **3.10+**
- SnowCLI installed and working:
  ```bash
  snow sql --connection <name> --query "select 1"
  ```

### Python dependency:

  * `PyYAML>=6.0`

### Install deps:

```bash
pip install -r requirements.txt
```

---

## Project layout

```text
snowflake-diff/
├─ Makefile
├─ config.yml
├─ requirements.txt
└─ scripts/
   ├─ __init__.py
   ├─ utils.py       # safe_name() and tiny helpers
   ├─ auth.py        # SnowCLI runner using --connection
   ├─ collectors.py  # snapshot collectors
   ├─ diffing.py     # unified diff helpers
   ├─ reporting.py   # Markdown summary generator
   └─ snowdiff.py    # CLI orchestrator
```

Outputs:

```text
out/
├─ SUMMARY.md
├─ report.txt
├─ diffs/
└─ snapshots/
```

---

## Quick start (recommended)

1. Configure `config.yml` (see below)

2. Install dependencies:

```bash
make install
```

3. Test connections:

```bash
make connect-test
```

4. Run diff:

```bash
make diff
```

5. Review:

* `out/SUMMARY.md` (start here)
* `out/diffs/` for all diffs
* `out/snapshots/` for raw capture

---

## Configuration: `config.yml`

Example:

```yaml
out_dir: out

options:
  schema: true
  table_ddl: true
  data: true
  procs: true
  comments: true
  last_changed: true

table_filter:
  include: ["FACT_%"]
  exclude: ["TMP_%", "re:^ZZ_"]

comment_collection:
  column_mode: "desc"   # desc | account_usage

left:
  connection: "dev"
  role: "ROLE_A"
  warehouse: "WH"
  database: "DB_A"
  schema: "SCHEMA_A"

right:
  connection: "prod"
  role: "ROLE_B"
  warehouse: "WH"
  database: "DB_B"
  schema: "SCHEMA_B"
```

### What the toggles do

* `schema`: schema-wide drift from `INFORMATION_SCHEMA.COLUMNS`
* `table_ddl`: per-table DDL drift from `GET_DDL('TABLE', ...)`
* `data`: per-table fingerprints (COUNT + HASH_AGG(HASH(row))) — can be expensive
* `procs`: stored procedure DDL drift from `GET_DDL('PROCEDURE', ...)`
* `comments`: diff comments/metadata snapshots
* `last_changed`: diff “last changed” metadata drift (from SHOW outputs)

### Table filtering

`table_filter` applies to table-level collectors:

* table DDL
* data fingerprints
* column comments in `desc` mode

Pattern types:

* SQL LIKE patterns: `%` and `_`
* Regex: prefix with `re:` (e.g. `re:^FACT_.*$`)

### Column comment mode

* `desc` (default): runs `DESC TABLE` per table (accurate, slower)
* `account_usage`: reads `<DB>.ACCOUNT_USAGE.COLUMNS` (fast, may lag, requires privilege)

---

## Makefile commands

* `make connect-test` — validate both connections
* `make diff` — full diff (per config)
* `make diff-fast` — skip data + procs
* `make diff-ddl` — focus on schema + DDL (skip data/comments/last_changed)
* `make showreport` — print output paths
* `make clean` — remove output dir

---

## CLI usage examples

Connection test:

```bash
python3 scripts/snowdiff.py --config config.yml connect-test
```

Full diff:

```bash
python3 scripts/snowdiff.py --config config.yml diff --out out
```

Limit scope to FACT tables:

```bash
python3 scripts/snowdiff.py --config config.yml diff --include "FACT_%"
```

Regex include and exclude:

```bash
python3 scripts/snowdiff.py --config config.yml diff --include "re:^FACT_.*$" --exclude "re:^FACT_TMP_"
```

Disable expensive checks:

```bash
python3 scripts/snowdiff.py --config config.yml diff --no-data --no-procs
```

Switch column comment mode:

```bash
python3 scripts/snowdiff.py --config config.yml diff --column-comment-mode account_usage
```

Override right role at runtime:

```bash
python3 scripts/snowdiff.py --config config.yml diff --right-role NEW_ROLE
```

---

## Notes & caveats

### “Last changed” is not “deployment time”

Snowflake does not universally store deployment timestamps. This tool diffs metadata visible in `SHOW` output.
For real deployment tracking, consider:

* object TAGs like `DEPLOYED_AT`, `GIT_SHA`
* a CI/CD `DEPLOYMENT_LOG` table

### SHOW/DESC parsing is conservative

The tool requests TSV output without headers for stability. Without headers, robust parsing across accounts is hard.
So it diffs the full SHOW/DESC rows (prefixed) for reliability.

### ACCOUNT_USAGE lag

If using `account_usage` mode, remember ACCOUNT_USAGE can lag behind real-time changes.

### Cost

Data fingerprinting can be expensive on large tables. Prefer:

* `--no-data` for quick drift scans
* table filters to limit scope

---

## Sphinx documentation (autodoc)

You can generate API docs for all modules with Sphinx autodoc.

### 1) Install Sphinx

```bash
python -m pip install sphinx sphinx-autodoc-typehints
```

### 2) Create docs skeleton

```bash
sphinx-quickstart docs
```

### 3) Minimal `docs/conf.py` additions

In `docs/conf.py`, set:

```python
import os
import sys
sys.path.insert(0, os.path.abspath(".."))  # project root

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
]

autodoc_typehints = "description"
```

### 4) Example `docs/index.rst`

Replace `docs/index.rst` with:

```rst
Snowflake Diff API
==================

.. automodule:: scripts.snowdiff
   :members:

.. automodule:: scripts.auth
   :members:

.. automodule:: scripts.collectors
   :members:

.. automodule:: scripts.diffing
   :members:

.. automodule:: scripts.reporting
   :members:

.. automodule:: scripts.utils
   :members:
```

### 5) Build docs

```bash
make -C docs html
```

Open:

* `docs/_build/html/index.html`

---

## Troubleshooting

* `snow` not found: ensure SnowCLI is installed and on PATH.
* Connection test fails: run `make connect-test` and verify your SnowCLI profiles.
* `__ERROR__` appears in snapshots: check role privileges for `GET_DDL`, `SHOW`, or `ACCOUNT_USAGE`.
