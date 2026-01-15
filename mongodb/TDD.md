# Test-Driven Development (TDD) Notes

## Unit test scope
- JSON flattening utilities (`json_flatten/flattener.py`).
- CSV writer (`json_flatten/csv_io.py`).
- Scenario definitions (`json_flatten/scenarios.py`).

## What is not unit tested
- Docker-based ingestion (covered by manual run and CI build only).
- MongoDB connectivity (assumed available when running Docker compose).

## Test strategy
- Small, focused tests for edge cases (lists, mixed types, nulls).
- Deterministic outputs for scenario fixtures.

## Running tests

```bash
make test
```
