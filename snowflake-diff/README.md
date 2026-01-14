# Snowflake Diff (SnowCLI) — Bash + Python + YAML config

Compare two Snowflake targets (db/schema/role/warehouse) using `snow sql`.  
Outputs:
- unified diff files for:
  - table list
  - column metadata
  - table DDLs
  - optional data fingerprints (row_count + hash)
  - stored procedure DDLs
- `out/SUMMARY.md` (Markdown summary with links to diffs)
- `out/report.txt`
- `out/snapshots/left` and `out/snapshots/right` (raw captures)

---

## Requirements
- Python 3.10+
- Snowflake CLI (`snow`) installed and authenticated
- Install Python deps:

```bash
pip install -r requirements.txt
