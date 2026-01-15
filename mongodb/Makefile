PYTHON ?= python3

.PHONY: help install test scenarios

help:
	@echo "Targets:"
	@echo "  install    Install Python deps"
	@echo "  test       Run unit tests with coverage"
	@echo "  scenarios  Run JSON flattening scenarios"

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest --cov=json_flatten --cov-report=term-missing

scenarios:
	$(PYTHON) scripts/run_scenarios.py
