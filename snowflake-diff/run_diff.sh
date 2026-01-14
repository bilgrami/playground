#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("ERROR: Python 3.10+ required. Found: " + sys.version)
print("Python OK:", sys.version.split()[0])
PY

"$PYTHON_BIN" scripts/snowdiff.py "$@"
