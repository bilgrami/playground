PYTHON ?= python3

.PHONY: help install test scenarios docker-up docker-down ingest

help:
	@echo "Targets:"
	@echo "  install    Install Python deps"
	@echo "  test       Run unit tests with coverage"
	@echo "  scenarios  Run JSON flattening scenarios"
	@echo "  docker-up  Start MongoDB container"
	@echo "  docker-down  Stop containers and remove volumes"
	@echo "  ingest     Ingest CSV via docker (CSV=path/to.csv)"

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest --cov=json_flatten --cov-report=term-missing

scenarios:
	$(PYTHON) scripts/run_scenarios.py

docker-up:
	scripts/docker_up.sh

docker-down:
	scripts/docker_down.sh

ingest:
	@if [ -z "$(CSV)" ]; then echo "Usage: make ingest CSV=path/to.csv"; exit 1; fi
	scripts/ingest_csv.sh $(CSV)
