# Development Guide

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run unit tests

```bash
make test
```

## Run scenarios

```bash
make scenarios
```

## Docker ingestion

```bash
scripts/seed_mongo.sh
```

## Layout
- `json_flatten/` core Python package.
- `scripts/` helpers for scenarios and ingestion.
- `docker/` Docker image and compose file.
- `docs/` scenario documentation.
