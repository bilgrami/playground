# Flattening Scenarios

This document describes all available JSON flattening scenarios, covering common challenges faced by data engineers and data scientists.

## Overview

The toolkit includes 11 pre-built scenarios that demonstrate various JSON flattening patterns:

1. **nested_objects** - Basic nested structures
2. **list_of_primitives** - Arrays of simple values
3. **list_of_objects_explode** - Exploding object arrays
4. **multi_path_explosion** - Cartesian product expansion
5. **mixed_types** - Handling mixed data types
6. **deep_nesting** - Deeply nested structures
7. **nested_arrays** - Arrays within arrays
8. **complex_mixed_types** - Complex mixed type scenarios
9. **empty_and_null_handling** - Edge cases with nulls/empties
10. **date_and_datetime** - Temporal data handling
11. **large_cartesian_product** - Performance testing scenarios

## Intermediate Scenarios

### 1. Nested Objects

**Description**: Basic nested dictionaries with scalar values.

**Input**:
```json
{
  "order": {
    "id": 42,
    "meta": {
      "source": "api"
    }
  },
  "customer": "acme"
}
```

**Output**: Single record with dot-delimited keys:
- `order.id`: 42
- `order.meta.source`: "api"
- `customer`: "acme"

**Use Case**: API responses with nested metadata.

### 2. Lists of Primitives

**Description**: Arrays of strings or numbers that can be joined.

**Input**:
```json
{
  "tags": ["blue", "green", "red"],
  "active": true
}
```

**Output** (with `list_policy="join"`):
- `tags`: "blue,green,red"
- `active`: true

**Output** (with `list_policy="index"`):
- `tags.0`: "blue"
- `tags.1`: "green"
- `tags.2`: "red"
- `active`: true

**Use Case**: Tags, categories, or simple lists that don't need individual records.

### 3. Lists of Objects (Exploded)

**Description**: Arrays of objects that should create multiple records.

**Input**:
```json
{
  "order_id": 1001,
  "items": [
    {"sku": "A1", "qty": 2},
    {"sku": "B2", "qty": 1}
  ]
}
```

**Output**: Two records (one per item):
- Record 1: `order_id`: 1001, `items.sku`: "A1", `items.qty`: 2
- Record 2: `order_id`: 1001, `items.sku`: "B2", `items.qty`: 1

**Use Case**: E-commerce orders, invoices, or any structure where array items represent distinct entities.

## Advanced Scenarios

### 4. Multi-Path Explosion

**Description**: Exploding multiple list paths to generate a cartesian product.

**Input**:
```json
{
  "order_id": 2001,
  "items": [{"sku": "A1"}, {"sku": "B2"}],
  "discounts": [{"code": "NEW10"}, {"code": "VIP"}]
}
```

**Output**: Four records (2×2 cartesian product):
- Record 1: `order_id`: 2001, `items.sku`: "A1", `discounts.code`: "NEW10"
- Record 2: `order_id`: 2001, `items.sku`: "A1", `discounts.code`: "VIP"
- Record 3: `order_id`: 2001, `items.sku`: "B2", `discounts.code`: "NEW10"
- Record 4: `order_id`: 2001, `items.sku`: "B2", `discounts.code`: "VIP"

**Use Case**: Analyzing combinations of products, regions, channels, etc.

### 5. Mixed Types

**Description**: Structures with mixed data types and null values.

**Input**:
```json
{
  "profile": {
    "age": null,
    "score": 9.5
  },
  "flags": [true, false]
}
```

**Output**: Handles nulls and mixed types gracefully:
- `profile.age`: null
- `profile.score`: 9.5
- `flags.0`: true
- `flags.1`: false

**Use Case**: Real-world data with missing or optional fields.

### 6. Deep Nesting

**Description**: Deeply nested structures with optional fields.

**Input**:
```json
{
  "a": {
    "b": {
      "c": {
        "d": 7
      }
    }
  },
  "optional": {}
}
```

**Output**:
- `a.b.c.d`: 7
- `optional`: {} (empty dict flattened to empty)

**Use Case**: Complex hierarchical data structures.

### 7. Nested Arrays

**Description**: Arrays containing nested arrays and objects.

**Input**:
```json
{
  "user_id": 123,
  "transactions": [
    {
      "id": "t1",
      "items": [
        {"name": "apple", "price": 1.5},
        {"name": "banana", "price": 0.8}
      ],
      "tags": ["food", "grocery"]
    },
    {
      "id": "t2",
      "items": [{"name": "book", "price": 15.0}],
      "tags": ["education"]
    }
  ]
}
```

**Output**: Two records (one per transaction), with nested items indexed:
- Record 1: `user_id`: 123, `transactions.id`: "t1", `transactions.items.0.name`: "apple", etc.
- Record 2: `user_id`: 123, `transactions.id`: "t2", `transactions.items.0.name`: "book", etc.

**Use Case**: Transactional data with line items.

### 8. Complex Mixed Types

**Description**: Complex structures with arrays mixing objects and primitives.

**Input**:
```json
{
  "event_id": "evt_001",
  "metadata": {
    "sources": ["api", "webhook", "batch"],
    "timestamps": ["2024-01-01T12:00:00"],
    "nested": {
      "values": [1, 2, {"special": true}]
    }
  },
  "status": "active"
}
```

**Output**: Handles mixed arrays intelligently, indexing all elements.

**Use Case**: Event logs with heterogeneous metadata.

### 9. Empty and Null Handling

**Description**: Edge cases with empty arrays, null values, and missing keys.

**Input**:
```json
{
  "id": 1,
  "name": "test",
  "empty_list": [],
  "null_field": null,
  "nested": {
    "present": "value",
    "missing": null
  },
  "optional": {}
}
```

**Output**: All edge cases handled gracefully:
- Empty arrays: omitted or handled according to policy
- Null values: preserved as null
- Missing keys: omitted from output

**Use Case**: Data validation and cleaning pipelines.

### 10. Date and DateTime

**Description**: Structures containing date and datetime values.

**Input**:
```json
{
  "order_id": 5001,
  "created_at": "2024-01-15T10:30:00",
  "events": [
    {"type": "created", "timestamp": "2024-01-15T10:30:00"},
    {"type": "updated", "timestamp": "2024-01-15T11:00:00"}
  ]
}
```

**Output**: Datetime values serialized to ISO format strings.

**Use Case**: Time-series data and event tracking.

### 11. Large Cartesian Product

**Description**: Large cartesian product from multiple array explosions.

**Input**:
```json
{
  "batch_id": "batch_001",
  "products": [{"id": "p1"}, {"id": "p2"}, {"id": "p3"}],
  "regions": [{"code": "R1"}, {"code": "R2"}],
  "channels": [{"name": "C1"}, {"name": "C2"}]
}
```

**Output**: 12 records (3×2×2 cartesian product).

**Use Case**: Performance testing and large-scale data transformations.

## Running Scenarios

To run all scenarios and generate output files:

```bash
make scenarios
```

This creates CSV files in `out/scenarios/<scenario_name>/output.csv` for each scenario.

To run a specific scenario programmatically:

```python
from json_flatten.scenarios import get_scenarios
from json_flatten import flatten_records, flatten_json, write_csv

scenarios = get_scenarios()
scenario = next(s for s in scenarios if s.name == "nested_arrays")

if scenario.mode == "records":
    records = flatten_records(
        scenario.data,
        explode_paths=scenario.explode_paths,
        list_policy=scenario.list_policy
    )
else:
    records = [flatten_json(scenario.data, list_policy=scenario.list_policy)]

write_csv(records, "output.csv")
```
