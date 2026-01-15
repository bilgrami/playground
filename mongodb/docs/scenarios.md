# Flattening Scenarios

This document lists intermediate and advanced JSON structures and how the toolkit handles them.

## Intermediate scenarios

### 1) Nested objects
- Input: nested dictionaries with scalar values.
- Output: dot-delimited keys in a single record.

### 2) Lists of primitives
- Input: arrays of strings or numbers.
- Output: list entries flattened by index or joined by comma.

### 3) Lists of objects (exploded)
- Input: arrays of objects under a key (e.g., `items`).
- Output: multiple records created by exploding the list.

## Advanced scenarios

### 4) Deep nesting with optional fields
- Missing keys are left blank in CSV output.

### 5) Mixed types
- Arrays mixing objects and primitives are indexed to preserve data.

### 6) Multi-path explosion
- Explode more than one list path to generate a cartesian expansion.

Example: exploding `items` and `discounts` produces a cross-product of records.
