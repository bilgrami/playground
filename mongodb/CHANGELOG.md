# CHANGELOG

All notable changes to this project will be documented in this file.

---

## Format
- **Reverse chronological order** (newest at top)
- **Header format:** `YYYY-MM-DD | <category>: <title>`
- **Categories:**
  - 🚀 **feat**
  - 🐛 **fix**
  - 📘 **docs**
  - 🧹 **chore**
- **Sections included in every entry:**
  - 📄 **Summary**
  - 📁 **Files Changed**
  - 🧠 **Rationale**
  - 🔄 **Behavior / Compatibility Implications**
  - 🧪 **Testing Recommendations**
  - 📌 **Follow‑ups**

---

## 2026-01-14 | 🧹 chore: Makefile docker helpers

### 📄 Summary
- Added Makefile targets for Docker helpers and CSV ingestion.

### 📁 Files Changed
- `Makefile`
- `CHANGELOG.md`

### 🧠 Rationale
- Provide consistent CLI ergonomics for Docker workflows.

### 🔄 Behavior / Compatibility Implications
- Adds new Makefile targets only.

### 🧪 Testing Recommendations
- `make docker-up`
- `make ingest CSV=out/scenarios/list_of_objects_explode/output.csv`
- `make docker-down`

### 📌 Follow‑ups
- None.

## 2026-01-14 | 🧹 chore: docker helper scripts and docs

### 📄 Summary
- Added helper scripts to start/stop MongoDB and ingest arbitrary CSV files.
- Expanded README with a Docker helpers section.

### 📁 Files Changed
- `scripts/docker_up.sh`
- `scripts/docker_down.sh`
- `scripts/ingest_csv.sh`
- `README.md`
- `CHANGELOG.md`

### 🧠 Rationale
- Make Docker workflows repeatable and developer-friendly.

### 🔄 Behavior / Compatibility Implications
- Adds new scripts; no runtime changes to existing flows.

### 🧪 Testing Recommendations
- `scripts/docker_up.sh`
- `scripts/ingest_csv.sh out/scenarios/list_of_objects_explode/output.csv`
- `scripts/docker_down.sh`

### 📌 Follow‑ups
- None.

## 2026-01-14 | 🧹 chore: CI workflow and scenario upgrades

### 📄 Summary
- Added multi-path explosion scenario and sample JSON fixtures.
- Relocated CI workflow to repo root and refined badge publishing.
- Added scenario-aware MongoDB seeding.

### 📁 Files Changed
- json_flatten/scenarios.py
- tests/test_flattener.py
- docs/scenarios.md
- README.md
- scripts/seed_mongo.sh
- docker/docker-compose.yml
- data/sample.json
- data/orders.json
- .github/workflows/mongodb-tests.yml
- CHANGELOG.md

### 🧠 Rationale
- Expand advanced scenario coverage and align CI with repo structure.

### 🔄 Behavior / Compatibility Implications
- Adds a scenario parameter to MongoDB seeding.

### 🧪 Testing Recommendations
- make test

### 📌 Follow‑ups
- Consider adding a docker-compose profile per scenario.

## 2026-01-14 | feat: json flattening + mongo ingest toolkit

### 📄 Summary
- Added JSON flattening module, CLI, and scenarios.
- Added Docker-based CSV ingestion into MongoDB.
- Added CI workflow, badges, and developer documentation.

### 📁 Files Changed
- README.md
- PRD.md
- TDD.md
- DEVELOPMENT.md
- CHANGELOG.md
- requirements.txt
- Makefile
- .coveragerc
- .github/workflows/tests.yml
- json_flatten/__init__.py
- json_flatten/flattener.py
- json_flatten/csv_io.py
- json_flatten/scenarios.py
- json_flatten/cli.py
- scripts/run_scenarios.py
- scripts/run_scenarios.sh
- scripts/seed_mongo.sh
- docker/Dockerfile
- docker/docker-compose.yml
- docker/ingest_csv.py
- docs/scenarios.md
- tests/test_flattener.py
- tests/test_csv_io.py
- tests/test_scenarios.py

### 🧠 Rationale
- Provide a complete, developer-friendly JSON flattening and MongoDB ingestion toolkit.

### 🔄 Behavior / Compatibility Implications
- New feature set; no breaking changes in this branch.

### 🧪 Testing Recommendations
- make test

### 📌 Follow‑ups
- Add optional schema inference for CSV ingestion.
