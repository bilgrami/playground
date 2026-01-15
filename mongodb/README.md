# JSON Flattening Toolkit for Data Engineers

[![Tests](https://github.com/bilgrami/playground/actions/workflows/mongodb-tests.yml/badge.svg?branch=main)](https://github.com/bilgrami/playground/actions/workflows/mongodb-tests.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://bilgrami.github.io/playground/mongodb/badges/coverage.json)](https://github.com/bilgrami/playground/actions/workflows/mongodb-tests.yml)
[![Unit Tests](https://img.shields.io/endpoint?url=https://bilgrami.github.io/playground/mongodb/badges/tests.json)](https://github.com/bilgrami/playground/actions/workflows/mongodb-tests.yml)

A comprehensive Python toolkit for flattening complex JSON structures into CSV format
and ingesting them into MongoDB and Snowflake. Designed to address real-world challenges
faced by data engineers and data scientists when working with nested JSON data.

## Key Features

- **Advanced JSON Flattening**: Handle nested objects, arrays, mixed types, and complex structures
- **Flexible Array Handling**: Index arrays or join primitives with configurable policies
- **Array Explosion**: Create multiple records from arrays (cartesian product support)
- **MongoDB Integration**: Ingest flattened data into MongoDB with automatic type inference
- **Snowflake Integration**: Export to Snowflake data warehouse with schema generation
- **PySpark Support**: Large-scale document processing with distributed computing
- **Comprehensive Scenarios**: Pre-built examples covering common data engineering challenges
- **Interactive Notebook**: World-class Jupyter notebook with 10 self-contained milestones
- **Production Ready**: Full test coverage, CI/CD integration, and comprehensive documentation

## Common Challenges Addressed

### 1. Complex Nested Structures
Handle deeply nested JSON objects with multiple levels of nesting:
```python
data = {"a": {"b": {"c": {"d": 7}}}}
# Flattens to: {"a.b.c.d": 7}
```

### 2. Arrays with Mixed Types
Process arrays containing both primitives and objects:
```python
data = {"values": [1, 2, {"special": True}]}
# Handles mixed types intelligently
```

### 3. Array Explosion (Cartesian Products)
Create multiple records from arrays, supporting cartesian expansion:
```python
data = {
    "order_id": 1,
    "items": [{"sku": "A"}, {"sku": "B"}],
    "discounts": [{"code": "X"}, {"code": "Y"}]
}
# Creates 4 records (2×2 cartesian product)
```

### 4. Date and DateTime Handling
Properly serialize datetime objects for database ingestion:
```python
from datetime import datetime
data = {"created_at": datetime.now()}
# Automatically converts to ISO format
```

### 5. Null and Empty Value Handling
Robust handling of None values, empty arrays, and missing keys:
```python
data = {"field": None, "empty_list": [], "optional": {}}
# Handles all edge cases gracefully
```

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

## Installation

### Basic Installation

```bash
pip install -r requirements.txt
```

### With PySpark (for large-scale processing)

PySpark is included in `requirements.txt`. If you need to install it separately:

```bash
pip install pyspark>=3.5.0 findspark>=2.0.0
```

**Note**: PySpark requires Java. Install Java first:
- **macOS**: `brew install openjdk`
- **Linux**: `sudo apt-get install default-jdk`
- **Windows**: Download from [Adoptium](https://adoptium.net/)

### Docker Installation

For a complete environment with Jupyter and PySpark:

```bash
# Using Docker Compose
docker-compose -f docker/docker-compose-notebook.yml up

# Or using Docker directly
docker run -it --rm \
  -p 8888:8888 \
  -v $(pwd):/workspace \
  -w /workspace \
  jupyter/pyspark-notebook:latest \
  jupyter notebook --ip=0.0.0.0 --allow-root examples/demo.ipynb
```

## Quick Start

### Basic JSON Flattening

```python
from json_flatten import flatten_json, write_csv

data = {
    "user": {"id": 42, "profile": {"name": "Alice"}},
    "tags": ["alpha", "beta"]
}

flattened = flatten_json(data)
# Result: {"user.id": 42, "user.profile.name": "Alice", "tags.0": "alpha", "tags.1": "beta"}

write_csv([flattened], "output.csv")
```

### Array Explosion

```python
from json_flatten import flatten_records, write_csv

data = {
    "order_id": 1001,
    "items": [{"sku": "A1", "qty": 2}, {"sku": "B2", "qty": 1}]
}

records = flatten_records(data, explode_paths=["items"])
# Creates 2 records, one per item

write_csv(records, "orders.csv")
```

### MongoDB Ingestion

```python
from json_flatten import flatten_records, write_csv, read_csv
from json_flatten.mongodb_io import ingest_csv_to_mongodb

# Flatten and write to CSV
records = flatten_records(data, explode_paths=["items"])
write_csv(records, "output.csv")

# Read CSV and ingest into MongoDB
csv_records = read_csv("output.csv")
count = ingest_csv_to_mongodb(
    csv_records,
    mongo_uri="mongodb://localhost:27017",
    database_name="mydb",
    collection_name="orders"
)
print(f"Inserted {count} documents")
```

### Snowflake Integration

```python
from json_flatten.snowflake_io import ingest_csv_to_snowflake, create_table_schema

# Generate table schema
sql = create_table_schema(records, "orders_table", "public")
print(sql)

# Ingest into Snowflake
count = ingest_csv_to_snowflake(
    csv_records,
    account="your_account",
    user="your_user",
    password="your_password",
    warehouse="COMPUTE_WH",
    database="mydb",
    schema="public",
    table_name="orders_table"
)
```

## Command Line Interface

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

## Docker helpers

Start only the MongoDB service:

```bash
scripts/docker_up.sh
```

Stop containers and remove volumes:

```bash
scripts/docker_down.sh
```

Ingest any CSV file into MongoDB:

```bash
scripts/ingest_csv.sh out/scenarios/list_of_objects_explode/output.csv
```

The Docker compose file mounts `CSV_PATH` into the ingest container, so you can also run:

```bash
CSV_PATH=../out/scenarios/multi_path_explosion/output.csv docker compose -f docker/docker-compose.yml up --build --abort-on-container-exit ingest
```

## Scenarios

The toolkit includes 11 pre-built scenarios covering various complexity levels:

1. **nested_objects**: Basic nested structures
2. **list_of_primitives**: Arrays of simple values
3. **list_of_objects_explode**: Exploding object arrays
4. **multi_path_explosion**: Cartesian product expansion
5. **mixed_types**: Handling mixed data types
6. **deep_nesting**: Deeply nested structures
7. **nested_arrays**: Arrays within arrays
8. **complex_mixed_types**: Complex mixed type scenarios
9. **empty_and_null_handling**: Edge cases with nulls/empties
10. **date_and_datetime**: Temporal data handling
11. **large_cartesian_product**: Performance testing scenarios

Run all scenarios:

```bash
make scenarios
```

See `docs/scenarios.md` for detailed descriptions.

## Testing

Run unit tests:

```bash
make test
```

Run integration tests (requires MongoDB):

```bash
MONGO_URI=mongodb://localhost:27017 pytest tests/test_integration.py
```

## API Documentation

### Core Functions

- `flatten_json(data, sep=".", list_policy="index")`: Flatten JSON to single dict
- `flatten_records(data, explode_paths=None, sep=".", list_policy="index")`: Flatten to multiple records
- `write_csv(records, output_path)`: Write records to CSV
- `read_csv(input_path)`: Read CSV into list of dicts

### MongoDB Functions

- `ingest_csv_to_mongodb(csv_records, mongo_uri, database_name, collection_name)`: Ingest records
- `query_mongodb(mongo_uri, database_name, collection_name, filter_dict=None)`: Query collection

### Snowflake Functions

- `create_table_schema(records, table_name, schema_name=None)`: Generate CREATE TABLE SQL
- `ingest_csv_to_snowflake(csv_records, account, user, password, ...)`: Ingest records
- `query_snowflake(account, user, password, warehouse, database, schema, query)`: Execute SQL

## Developer Documentation

- `PRD.md` - Product requirements document
- `TDD.md` - Test-driven development strategy
- `DEVELOPMENT.md` - Local setup and workflow notes
- `docs/scenarios.md` - Detailed scenario descriptions

## Jupyter Notebook

### Comprehensive Interactive Guide

The project includes a **world-class Jupyter notebook** (`examples/demo.ipynb`) designed for data engineers and data scientists. The notebook is organized into **10 self-contained milestones**, each focusing on specific aspects of JSON flattening.

#### Notebook Features

- **📚 Educational Content**: Extensive markdown documentation explaining concepts for junior developers
- **🎯 Milestone-Based Structure**: 10 self-contained milestones covering:
  1. Foundations & Core Concepts
  2. Array Handling Strategies
  3. Complex Structures
  4. E-commerce Data Use Cases
  5. API & Event Data Use Cases
  6. CSV Operations & Pipelines
  7. MongoDB Integration
  8. Snowflake Integration
  9. Advanced Patterns & Best Practices
  10. End-to-End Workflows

- **⚡ PySpark Integration**: Large-scale document processing with distributed computing
- **🐳 Docker Support**: Designed to run in Docker containers with PySpark support
- **📊 Performance Analysis**: Examples of handling large documents and optimization techniques

#### Running the Notebook

**Option 1: Using Makefile (Recommended)**
```bash
# Local Jupyter
make notebook

# Docker with PySpark
make notebook-docker

# Stop Docker notebook
make notebook-stop
```

**Option 2: Using Script**
```bash
# Local Jupyter
./scripts/notebook.sh local

# Docker with PySpark
./scripts/notebook.sh docker

# Stop Docker notebook
./scripts/notebook.sh stop
```

**Option 3: Direct Commands**
```bash
# Local Jupyter
jupyter notebook examples/demo.ipynb

# Docker Compose
docker-compose -f docker/docker-compose-notebook.yml up
```

#### Notebook Highlights

- **All imports at the top** of cells for clarity
- **Helper functions** for visualization and analysis
- **Real-world examples** from e-commerce, APIs, and event data
- **Performance comparisons** between single-threaded and PySpark approaches
- **Large document scenarios** demonstrating scalability

#### PySpark Features

The notebook includes PySpark integration for:
- Processing large JSON files efficiently
- Distributed flattening operations
- Performance optimization techniques
- Memory-efficient batch processing
- Parallel array explosion operations

See `examples/demo.ipynb` for the complete interactive demonstration.

## License

See root license in the parent repository.
