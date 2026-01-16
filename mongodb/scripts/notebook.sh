#!/usr/bin/env bash
set -euo pipefail

# Script to start Jupyter notebook with PySpark support
# Usage: ./scripts/notebook.sh [local|docker]

MODE="${1:-local}"
NOTEBOOK_FILE="examples/demo.ipynb"
DOCKER_COMPOSE_FILE="docker/docker-compose-notebook.yml"

case "$MODE" in
  local)
    echo "Starting Jupyter notebook locally..."
    echo "Access at http://localhost:8888"
    python3 -m jupyter notebook "$NOTEBOOK_FILE"
    ;;
  docker)
    echo "Starting Jupyter notebook in Docker with PySpark..."
    echo "Access at http://localhost:8888"
    echo "Press Ctrl+C to stop"
    
    # Check if docker-compose or docker compose is available
    if command -v docker-compose &> /dev/null; then
      docker-compose -f "$DOCKER_COMPOSE_FILE" up
    elif docker compose version &> /dev/null; then
      docker compose -f "$DOCKER_COMPOSE_FILE" up
    else
      echo "Error: docker-compose or docker compose not found"
      exit 1
    fi
    ;;
  stop)
    echo "Stopping Docker notebook container..."
    if command -v docker-compose &> /dev/null; then
      docker-compose -f "$DOCKER_COMPOSE_FILE" down
    elif docker compose version &> /dev/null; then
      docker compose -f "$DOCKER_COMPOSE_FILE" down
    else
      echo "Error: docker-compose or docker compose not found"
      exit 1
    fi
    ;;
  *)
    echo "Usage: $0 [local|docker|stop]"
    echo ""
    echo "  local  - Start notebook locally (requires Jupyter installed)"
    echo "  docker - Start notebook in Docker with PySpark"
    echo "  stop   - Stop Docker notebook container"
    exit 1
    ;;
esac
