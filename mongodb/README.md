# MongoDB JSON Flattening Toolkit

[![Tests](https://github.com/bilgrami/playground/actions/workflows/mongodb-tests.yml/badge.svg?branch=main)](https://github.com/bilgrami/playground/actions/workflows/mongodb-tests.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://bilgrami.github.io/playground/mongodb/badges/coverage.json)](https://github.com/bilgrami/playground/actions/workflows/mongodb-tests.yml)
[![Unit Tests](https://img.shields.io/endpoint?url=https://bilgrami.github.io/playground/mongodb/badges/tests.json)](https://github.com/bilgrami/playground/actions/workflows/mongodb-tests.yml)

A Python-first toolkit to flatten JSON into CSV and ingest it into MongoDB. It focuses on
challenging real-world structures (nested objects, arrays of objects, mixed types) and
provides repeatable scenarios for testing and demos.

## Features
- Flatten JSON into key/value dictionaries with configurable list handling.
- Explode arrays into multiple records for CSV output.
- Scenario runner for intermediate and advanced flattening cases.
- Dockerized CSV ingestion into MongoDB.

## Quick start

1) Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2) Install dependencies:

```bash
pip install -r requirements.txt
```

3) Run unit tests:

```bash
make test
```

4) Run scenarios (writes outputs to `out/`):

```bash
make scenarios
```

## JSON flattening CLI

Flatten a JSON file into a single record:

```bash
python -m json_flatten.cli flatten --input data/sample.json --output out/flat.csv
```

Flatten with array explosion into multiple records:

```bash
python -m json_flatten.cli records --input data/orders.json --output out/orders.csv --explode items
```

Explode multiple list paths (cartesian expansion):

```bash
python -m json_flatten.cli records --input data/orders.json --output out/orders.csv --explode items --explode discounts
```

## Docker-based MongoDB ingestion

1) Start MongoDB and ingest a CSV (from scenario outputs):

```bash
scripts/seed_mongo.sh
```

Pick a scenario to seed:

```bash
scripts/seed_mongo.sh multi_path_explosion
```

2) Connect to MongoDB locally:

```bash
mongosh mongodb://localhost:27017
```

## Scenarios

See `docs/scenarios.md` for intermediate and advanced cases and how they map to output CSV.

## Developer documentation

- `PRD.md` for product requirements
- `TDD.md` for test strategy
- `DEVELOPMENT.md` for local setup and workflow notes

## License

See root license in the parent repository.
