"""Scenario definitions for challenging flattening cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Sequence


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    data: Any
    mode: str = "dict"
    list_policy: str = "index"
    explode_paths: Sequence[str] | None = None


def get_scenarios() -> List[Scenario]:
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
    ]
