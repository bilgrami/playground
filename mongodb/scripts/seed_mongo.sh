#!/usr/bin/env bash
set -euo pipefail

python3 scripts/run_scenarios.py

scenario="${1:-list_of_objects_explode}"
csv_path="out/scenarios/${scenario}/output.csv"
if [ ! -f "$csv_path" ]; then
  echo "CSV not found: $csv_path"
  echo "Available scenarios:"
  ls -1 out/scenarios || true
  exit 1
fi

CSV_PATH="../${csv_path}" docker compose -f docker/docker-compose.yml up --build --abort-on-container-exit
