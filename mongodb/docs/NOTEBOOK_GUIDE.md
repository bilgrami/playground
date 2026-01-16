# Jupyter Notebook Guide

## Overview

The `examples/demo.ipynb` notebook is a comprehensive, interactive guide for data engineers and data scientists working with JSON flattening. It's organized into 10 self-contained milestones, each focusing on specific aspects of JSON processing.

## Quick Start

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start Jupyter
jupyter notebook examples/demo.ipynb
```

### Running in Docker

```bash
# Using Docker Compose (recommended)
docker-compose -f docker/docker-compose-notebook.yml up

# Access at http://localhost:8888
```

## Notebook Structure

### Milestone 1: Foundations & Core Concepts
**Learning Objectives:**
- Understand JSON flattening fundamentals
- Learn nested structure handling
- Explore list policies (index vs join)
- Master custom separators

**Key Concepts:**
- What is nesting and why it's a problem
- How flattening works recursively
- Custom separator usage

### Milestone 2: Array Handling Strategies
**Learning Objectives:**
- Compare index vs join policies
- Understand array explosion
- Learn cartesian product creation

**Key Concepts:**
- When to use index policy
- When to use join policy
- Array explosion for multiple records

### Milestone 3: Complex Structures
**Learning Objectives:**
- Handle deep nesting
- Process mixed types
- Manage null and empty values
- Work with nested arrays

**Key Concepts:**
- Deep nesting patterns
- Type inference
- Edge case handling

### Milestone 4: E-commerce Data Use Cases
**Learning Objectives:**
- Process order data
- Handle product catalogs
- Manage customer information
- Analyze transactions

**Real-World Examples:**
- Order processing pipelines
- Product catalog flattening
- Customer data normalization

### Milestone 5: API & Event Data Use Cases
**Learning Objectives:**
- Process API responses
- Handle webhook data
- Manage event logs
- Work with time-series data

**Real-World Examples:**
- REST API response processing
- Webhook payload flattening
- Event log analysis

### Milestone 6: CSV Operations & Pipelines
**Learning Objectives:**
- Read and write CSV files
- Build data transformation pipelines
- Handle batch processing
- Manage errors gracefully

**Key Concepts:**
- CSV I/O operations
- Pipeline patterns
- Batch processing strategies

### Milestone 7: MongoDB Integration
**Learning Objectives:**
- Ingest data into MongoDB
- Query MongoDB collections
- Understand type inference
- Optimize batch operations

**Key Concepts:**
- MongoDB connection patterns
- Type conversion strategies
- Query optimization

### Milestone 8: Snowflake Integration
**Learning Objectives:**
- Generate table schemas
- Ingest into Snowflake
- Execute SQL queries
- Handle data types

**Key Concepts:**
- Schema generation
- Snowflake data types
- Ingestion strategies

### Milestone 9: Advanced Patterns & Best Practices
**Learning Objectives:**
- Optimize performance
- Manage memory efficiently
- Handle errors robustly
- Apply best practices

**Key Concepts:**
- Performance optimization
- Memory management
- Error handling patterns
- Production considerations

### Milestone 10: End-to-End Workflows
**Learning Objectives:**
- Build complete pipelines
- Integrate multiple systems
- Handle production scenarios
- Monitor and debug

**Key Concepts:**
- Complete pipeline examples
- System integration
- Production patterns
- Monitoring strategies

## PySpark Integration

The notebook includes PySpark examples for large-scale processing:

### When to Use PySpark

- **Large files**: JSON files > 1GB
- **Distributed processing**: Need parallel processing
- **Memory constraints**: Single machine insufficient
- **Performance**: Need faster processing

### PySpark Features Demonstrated

1. **Distributed Flattening**: Process large JSON files across cluster
2. **Parallel Array Explosion**: Explode arrays in parallel
3. **Memory Efficiency**: Handle datasets that don't fit in memory
4. **Performance Optimization**: Spark SQL optimizations

### Example Usage

```python
# Initialize Spark session (done automatically in notebook)
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("JSONFlattening").getOrCreate()

# Read large JSON file
df = spark.read.json("large_file.json")

# Flatten using Spark SQL
flattened_df = df.select(
    col("order_id"),
    explode(col("items")).alias("item")
).select(
    col("order_id"),
    col("item.sku").alias("item_sku"),
    col("item.qty").alias("item_qty")
)
```

## Large Document Scenarios

The notebook includes specific scenarios for handling large documents:

1. **Memory-Efficient Processing**: Streaming large files
2. **Batch Processing**: Process in chunks
3. **Distributed Processing**: Use PySpark for scale
4. **Performance Monitoring**: Measure and optimize

## Best Practices

### For Junior Developers

1. **Start with Milestone 1**: Understand basics before advanced topics
2. **Run cells sequentially**: Each cell builds on previous ones
3. **Read markdown cells**: They explain concepts thoroughly
4. **Experiment**: Modify examples to understand behavior
5. **Ask questions**: Use markdown explanations as reference

### For Data Engineers

1. **Focus on Milestones 6-10**: Production-focused content
2. **Study PySpark examples**: Large-scale processing patterns
3. **Review integration patterns**: MongoDB and Snowflake
4. **Understand performance**: Optimization techniques

### For Data Scientists

1. **Focus on Milestones 1-5**: Data transformation patterns
2. **Study use cases**: Real-world examples
3. **Understand array handling**: Critical for analysis
4. **Learn CSV operations**: Common data format

## Troubleshooting

### Common Issues

**PySpark not initializing:**
- Ensure Java is installed
- Set JAVA_HOME environment variable
- Check `findspark` is installed

**Import errors:**
- Run the first cell (imports) first
- Check all dependencies installed: `pip install -r requirements.txt`
- Restart kernel if needed

**Memory issues:**
- Use PySpark for large datasets
- Process in batches
- Increase Docker memory allocation

**Docker issues:**
- Ensure port 8888 is available
- Check Docker has sufficient memory (4GB+)
- Verify volume mounts work correctly

## Additional Resources

- **README.md**: Project overview and quick start
- **docs/scenarios.md**: Detailed scenario descriptions
- **DEVELOPMENT.md**: Development setup and workflow
- **PRD.md**: Product requirements
- **TDD.md**: Test strategy

## Contributing

When adding to the notebook:

1. **Follow milestone structure**: Keep content organized
2. **Add markdown explanations**: Help junior developers
3. **Include examples**: Show, don't just tell
4. **Test in Docker**: Ensure Docker compatibility
5. **Update this guide**: Document new features
