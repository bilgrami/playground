"""Scenario definitions for challenging flattening cases.

This module defines various JSON structures that represent common challenges
faced by data engineers and data scientists when working with nested JSON data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Sequence


@dataclass(frozen=True)
class Scenario:
    """A test scenario for JSON flattening.
    
    Attributes
    ----------
    name : str
        Unique identifier for the scenario.
    description : str
        Human-readable description of what the scenario tests.
    data : Any
        JSON-like data structure to flatten.
    mode : str, optional
        Flattening mode: "dict" for single record, "records" for multiple (default: "dict").
    list_policy : str, optional
        How to handle lists: "index" or "join" (default: "index").
    explode_paths : Sequence[str] | None, optional
        Paths to arrays that should be exploded into multiple records (default: None).
    """
    name: str
    description: str
    data: Any
    mode: str = "dict"
    list_policy: str = "index"
    explode_paths: Sequence[str] | None = None


def get_scenarios() -> List[Scenario]:
    """Get all available flattening scenarios.
    
    Returns
    -------
    List[Scenario]
        List of scenario definitions covering various JSON structures.
    """
    return [
        Scenario(
            name="nested_objects",
            description="Nested objects with scalar fields.",
            data={"order": {"id": 42, "meta": {"source": "api"}}, "customer": "acme"},
        ),
        Scenario(
            name="list_of_primitives",
            description="Array of primitives joined into a single field.",
            data={"tags": ["blue", "green", "red"], "active": True},
            list_policy="join",
        ),
        Scenario(
            name="list_of_objects_explode",
            description="Explode list of objects into multiple records.",
            data={
                "order_id": 1001,
                "items": [
                    {"sku": "A1", "qty": 2},
                    {"sku": "B2", "qty": 1},
                ],
            },
            mode="records",
            explode_paths=["items"],
        ),
        Scenario(
            name="multi_path_explosion",
            description="Explode multiple list paths for cartesian expansion.",
            data={
                "order_id": 2001,
                "items": [{"sku": "A1"}, {"sku": "B2"}],
                "discounts": [{"code": "NEW10"}, {"code": "VIP"}],
            },
            mode="records",
            explode_paths=["items", "discounts"],
        ),
        Scenario(
            name="mixed_types",
            description="Mixed types and null values across nested fields.",
            data={"profile": {"age": None, "score": 9.5}, "flags": [True, False]},
        ),
        Scenario(
            name="deep_nesting",
            description="Deeply nested structures with optional fields.",
            data={"a": {"b": {"c": {"d": 7}}}, "optional": {}},
        ),
        Scenario(
            name="nested_arrays",
            description="Arrays containing nested arrays and objects.",
            data={
                "user_id": 123,
                "transactions": [
                    {
                        "id": "t1",
                        "items": [{"name": "apple", "price": 1.5}, {"name": "banana", "price": 0.8}],
                        "tags": ["food", "grocery"],
                    },
                    {
                        "id": "t2",
                        "items": [{"name": "book", "price": 15.0}],
                        "tags": ["education"],
                    },
                ],
            },
            mode="records",
            explode_paths=["transactions"],
        ),
        Scenario(
            name="complex_mixed_types",
            description="Complex structure with arrays mixing objects and primitives.",
            data={
                "event_id": "evt_001",
                "metadata": {
                    "sources": ["api", "webhook", "batch"],
                    "timestamps": [datetime(2024, 1, 1, 12, 0, 0).isoformat()],
                    "nested": {
                        "values": [1, 2, {"special": True}],
                    },
                },
                "status": "active",
            },
        ),
        Scenario(
            name="empty_and_null_handling",
            description="Handling of empty arrays, null values, and missing keys.",
            data={
                "id": 1,
                "name": "test",
                "empty_list": [],
                "null_field": None,
                "nested": {
                    "present": "value",
                    "missing": None,
                },
                "optional": {},
            },
        ),
        Scenario(
            name="date_and_datetime",
            description="Structures containing date and datetime values.",
            data={
                "order_id": 5001,
                "created_at": datetime(2024, 1, 15, 10, 30, 0).isoformat(),
                "events": [
                    {"type": "created", "timestamp": datetime(2024, 1, 15, 10, 30, 0).isoformat()},
                    {"type": "updated", "timestamp": datetime(2024, 1, 15, 11, 0, 0).isoformat()},
                ],
            },
            mode="records",
            explode_paths=["events"],
        ),
        Scenario(
            name="large_cartesian_product",
            description="Large cartesian product from multiple array explosions.",
            data={
                "batch_id": "batch_001",
                "products": [{"id": f"p{i}"} for i in range(1, 4)],
                "regions": [{"code": f"R{i}"} for i in range(1, 3)],
                "channels": [{"name": f"C{i}"} for i in range(1, 3)],
            },
            mode="records",
            explode_paths=["products", "regions", "channels"],
        ),
    ]
