PYTHON ?= python3

.PHONY: help install test scenarios docker-up docker-down ingest notebook notebook-docker notebook-stop notebook-java notebook-java-stop

help:
	@echo "Targets:"
	@echo "  install         Install Python deps"
	@echo "  test            Run unit tests with coverage"
	@echo "  scenarios       Run JSON flattening scenarios"
	@echo "  docker-up       Start MongoDB container"
	@echo "  docker-down     Stop containers and remove volumes"
	@echo "  ingest          Ingest CSV via docker (CSV=path/to.csv)"
	@echo "  notebook        Start Jupyter notebook locally"
	@echo "  notebook-docker Start Jupyter notebook in Docker with PySpark"
	@echo "  notebook-stop   Stop Docker notebook container"
	@echo "  notebook-java   Start Java notebook in Docker with IJava kernel (port 8889)"
	@echo "  notebook-java-stop Stop Java Docker notebook container"

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

notebook:
	@echo "Starting Jupyter notebook locally..."
	@echo "Access at http://localhost:8888"
	$(PYTHON) -m jupyter notebook examples/demo.ipynb

notebook-docker:
	@scripts/notebook.sh docker

notebook-stop:
	@scripts/notebook.sh stop

notebook-java:
	@scripts/notebook-java.sh docker

notebook-java-stop:
	@scripts/notebook-java.sh stop
