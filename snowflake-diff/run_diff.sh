#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Set PYTHON_BIN or install Python 3.10+." >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("ERROR: Python 3.10+ required. Found: " + sys.version)
print("Python OK:", sys.version.split()[0])
PY

if ! command -v snow >/dev/null 2>&1; then
  echo "ERROR: 'snow' CLI not found in PATH. Install Snowflake CLI and ensure 'snow sql' works." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$PYTHON_BIN" "$SCRIPT_DIR/scripts/snowdiff.py" "$@"
