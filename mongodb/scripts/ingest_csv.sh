#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

csv_path="${1:-}"
if [ -z "$csv_path" ]; then
  echo "Usage: scripts/ingest_csv.sh <path-to-csv>"
  exit 1
fi

if [ ! -f "$csv_path" ]; then
  echo "CSV not found: $csv_path"
  exit 1
fi

CSV_PATH="../$csv_path" docker compose -f docker/docker-compose.yml up --build --abort-on-container-exit ingest
