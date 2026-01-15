"""Core JSON flattening utilities."""

from __future__ import annotations

import copy
from typing import Any, Dict, Iterable, List, Mapping, Sequence


def is_scalar(value: Any) -> bool:
    """Return True when *value* is a JSON scalar."""
    return value is None or isinstance(value, (str, int, float, bool))


def flatten_json(
    data: Any,
    parent_key: str = "",
    sep: str = ".",
    list_policy: str = "index",
) -> Dict[str, Any]:
    """Flatten JSON-like data into a single dictionary.

    Parameters
    ----------
    data:
        JSON-like input (dict, list, or scalar).
    parent_key:
        Prefix for nested keys.
    sep:
        Separator used between key segments.
    list_policy:
        How to handle lists. Supported values:
        - "index": create indexed keys (e.g., items.0.name)
        - "join": join lists of scalars by comma, otherwise index
    """
    items: Dict[str, Any] = {}

    def _flatten(obj: Any, prefix: str) -> None:
        if isinstance(obj, Mapping):
            for key, value in obj.items():
                new_key = f"{prefix}{sep}{key}" if prefix else str(key)
                _flatten(value, new_key)
            return

        if isinstance(obj, list):
            if list_policy == "join" and all(is_scalar(x) for x in obj):
                joined = ",".join("" if x is None else str(x) for x in obj)
                items[prefix] = joined
                return
            for idx, value in enumerate(obj):
                new_key = f"{prefix}{sep}{idx}" if prefix else str(idx)
                _flatten(value, new_key)
            return

        items[prefix] = obj

    _flatten(data, parent_key)
    return items


def flatten_records(
    data: Any,
    explode_paths: Sequence[str] | None = None,
    sep: str = ".",
    list_policy: str = "index",
) -> List[Dict[str, Any]]:
    """Flatten JSON data into multiple records by exploding list paths.

    Parameters
    ----------
    data:
        JSON-like input (dict, list, or scalar).
    explode_paths:
        Dot-delimited paths pointing to lists to explode.
    sep:
        Separator used between key segments.
    list_policy:
        List handling policy passed to :func:`flatten_json`.
    """
    records: List[Any]
    if isinstance(data, list):
        records = list(data)
    else:
        records = [data]

    for path in explode_paths or []:
        records = _explode_at_path(records, path)

    return [flatten_json(record, sep=sep, list_policy=list_policy) for record in records]


def _explode_at_path(records: Iterable[Any], path: str) -> List[Any]:
    exploded: List[Any] = []
    for record in records:
        node = _get_by_path(record, path)
        if isinstance(node, list):
            if not node:
                exploded.append(record)
                continue
            for item in node:
                clone = copy.deepcopy(record)
                _set_by_path(clone, path, item)
                exploded.append(clone)
        else:
            exploded.append(record)
    return exploded


def _get_by_path(data: Any, path: str) -> Any:
    current = data
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _set_by_path(data: Any, path: str, value: Any) -> None:
    current = data
    parts = path.split(".")
    for part in parts[:-1]:
        if not isinstance(current, Mapping):
            return
        if part not in current or not isinstance(current[part], Mapping):
            current[part] = {}
        current = current[part]
    if isinstance(current, Mapping):
        current[parts[-1]] = value
