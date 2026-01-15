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

## Jupyter Notebook Development

### Local Development

```bash
# Install dependencies (includes PySpark)
pip install -r requirements.txt

# Start Jupyter notebook server
jupyter notebook examples/demo.ipynb
```

### Docker Development with PySpark

The notebook is designed to run in Docker containers with PySpark support for large-scale processing.

#### Option 1: Using Jupyter PySpark Image

```bash
docker run -it --rm \
  -p 8888:8888 \
  -v $(pwd):/home/jovyan/work \
  -w /home/jovyan/work \
  jupyter/pyspark-notebook:latest \
  jupyter notebook --ip=0.0.0.0 --allow-root examples/demo.ipynb
```

Access the notebook at `http://localhost:8888`

#### Option 2: Custom Docker Compose

Create `docker/docker-compose-notebook.yml`:

```yaml
version: '3.8'
services:
  jupyter:
    image: jupyter/pyspark-notebook:latest
    ports:
      - "8888:8888"
    volumes:
      - ..:/home/jovyan/work
    working_dir: /home/jovyan/work/mongodb
    command: jupyter notebook --ip=0.0.0.0 --allow-root --no-browser
    environment:
      - JUPYTER_ENABLE_LAB=yes
```

Run with:
```bash
docker-compose -f docker/docker-compose-notebook.yml up
```

#### Option 3: Local PySpark Setup

If running locally without Docker:

1. Install Java (required for PySpark):
   ```bash
   # macOS
   brew install openjdk
   
   # Linux
   sudo apt-get install default-jdk
   ```

2. Set JAVA_HOME:
   ```bash
   export JAVA_HOME=/usr/lib/jvm/default-java  # Adjust path as needed
   ```

3. Install PySpark:
   ```bash
   pip install pyspark findspark
   ```

4. Start Jupyter:
   ```bash
   jupyter notebook examples/demo.ipynb
   ```

### Notebook Structure

The notebook (`examples/demo.ipynb`) is organized into milestones:

1. **Milestone 1**: Foundations & Core Concepts
2. **Milestone 2**: Array Handling Strategies
3. **Milestone 3**: Complex Structures
4. **Milestone 4**: E-commerce Data Use Cases
5. **Milestone 5**: API & Event Data Use Cases
6. **Milestone 6**: CSV Operations & Pipelines
7. **Milestone 7**: MongoDB Integration
8. **Milestone 8**: Snowflake Integration
9. **Milestone 9**: Advanced Patterns & Best Practices
10. **Milestone 10**: End-to-End Workflows

Each milestone is self-contained and can be run independently.

### Large Document Processing

The notebook includes PySpark examples for:
- Processing large JSON files (>1GB)
- Distributed flattening operations
- Memory-efficient batch processing
- Performance optimization techniques

### Troubleshooting

**PySpark not initializing:**
- Ensure Java is installed and JAVA_HOME is set
- Check that `findspark` is installed: `pip install findspark`
- Verify Spark is available: `python -c "import findspark; findspark.init(); from pyspark.sql import SparkSession"`

**Docker issues:**
- Ensure Docker has sufficient memory (recommend 4GB+)
- Check port 8888 is not already in use
- Verify volume mounts are working correctly

**Notebook kernel issues:**
- Restart kernel: `Kernel > Restart`
- Clear outputs: `Cell > All Output > Clear`
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

## Layout
- `json_flatten/` - Core Python package
- `scripts/` - Helpers for scenarios and ingestion
- `docker/` - Docker image and compose files
- `docs/` - Scenario documentation
- `examples/` - Jupyter notebook and examples
- `tests/` - Unit and integration tests
