#!/usr/bin/env bash
set -euo pipefail

# Script to start Java Jupyter notebook with IJava kernel
# Usage: ./scripts/notebook-java.sh [local|docker|stop]

MODE="${1:-docker}"
NOTEBOOK_FILE="examples/demo_java.ipynb"
DOCKER_COMPOSE_FILE="docker/docker-compose-java-notebook.yml"

case "$MODE" in
  local)
    echo "Starting Java Jupyter notebook locally..."
    echo "Note: Requires IJava kernel installed (https://github.com/SpencerPark/IJava)"
    echo "Access at http://localhost:8888"
    python3 -m jupyter notebook "$NOTEBOOK_FILE"
    ;;
  docker)
    echo "Starting Java Jupyter notebook in Docker with IJava kernel..."
    echo "Note: First run will take longer to install IJava kernel"
    echo "Access at http://localhost:8889"
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
    echo "Stopping Java Docker notebook container..."
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
    echo "  local  - Start notebook locally (requires IJava kernel installed)"
    echo "  docker - Start notebook in Docker with IJava kernel (default)"
    echo "  stop   - Stop Docker notebook container"
    echo ""
    echo "Port: 8889 (different from Python notebook on 8888)"
    exit 1
    ;;
esac
