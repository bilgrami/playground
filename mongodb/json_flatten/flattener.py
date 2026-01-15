"""Core JSON flattening utilities.

This module provides functionality to flatten complex JSON structures into
flat dictionaries suitable for CSV export or database ingestion. It handles
nested objects, arrays, mixed types, and provides configurable policies
for array handling.
"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Sequence


def is_scalar(value: Any) -> bool:
    """Check if value is a JSON scalar type.
    
    Parameters
    ----------
    value : Any
        Value to check.
        
    Returns
    -------
    bool
        True if value is None, str, int, float, or bool.
    """
    return value is None or isinstance(value, (str, int, float, bool))


def _serialize_value(value: Any) -> Any:
    """Serialize non-JSON types to strings.
    
    Parameters
    ----------
    value : Any
        Value to serialize.
        
    Returns
    -------
    Any
        Serialized value (datetime objects become ISO strings).
    """
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def flatten_json(
    data: Any,
    parent_key: str = "",
    sep: str = ".",
    list_policy: str = "index",
) -> Dict[str, Any]:
    """Flatten JSON-like data into a single dictionary.

    This function recursively flattens nested JSON structures into a flat
    dictionary with dot-delimited keys. It handles nested objects, arrays,
    and mixed types according to the specified list policy.

    Parameters
    ----------
    data : Any
        JSON-like input (dict, list, or scalar).
    parent_key : str, optional
        Prefix for nested keys (used internally during recursion).
    sep : str, optional
        Separator used between key segments (default: ".").
    list_policy : str, optional
        How to handle lists. Supported values:
        - "index": create indexed keys (e.g., items.0.name)
        - "join": join lists of scalars by comma, otherwise index
        Default is "index".

    Returns
    -------
    Dict[str, Any]
        Flattened dictionary with dot-delimited keys.

    Examples
    --------
    >>> flatten_json({"a": {"b": 1}, "c": "x"})
    {'a.b': 1, 'c': 'x'}
    
    >>> flatten_json({"tags": ["a", "b"]}, list_policy="join")
    {'tags': 'a,b'}
    """
    if not isinstance(list_policy, str) or list_policy not in ("index", "join"):
        raise ValueError(f"list_policy must be 'index' or 'join', got {list_policy!r}")
    
    items: Dict[str, Any] = {}

    def _flatten(obj: Any, prefix: str) -> None:
        if isinstance(obj, Mapping):
            for key, value in obj.items():
                new_key = f"{prefix}{sep}{key}" if prefix else str(key)
                _flatten(value, new_key)
            return

        if isinstance(obj, list):
            if list_policy == "join" and all(is_scalar(x) for x in obj):
                joined = ",".join("" if x is None else str(_serialize_value(x)) for x in obj)
                items[prefix] = joined
                return
            for idx, value in enumerate(obj):
                new_key = f"{prefix}{sep}{idx}" if prefix else str(idx)
                _flatten(value, new_key)
            return

        items[prefix] = _serialize_value(obj)

    _flatten(data, parent_key)
    return items


def flatten_records(
    data: Any,
    explode_paths: Sequence[str] | None = None,
    sep: str = ".",
    list_policy: str = "index",
) -> List[Dict[str, Any]]:
    """Flatten JSON data into multiple records by exploding list paths.

    This function creates multiple flattened records by exploding arrays
    at specified paths. When multiple paths are provided, it performs
    a cartesian product expansion.

    Parameters
    ----------
    data : Any
        JSON-like input (dict, list, or scalar).
    explode_paths : Sequence[str] | None, optional
        Dot-delimited paths pointing to lists to explode. If None, no
        explosion is performed.
    sep : str, optional
        Separator used between key segments (default: ".").
    list_policy : str, optional
        List handling policy passed to :func:`flatten_json` (default: "index").

    Returns
    -------
    List[Dict[str, Any]]
        List of flattened dictionaries, one per exploded record.

    Examples
    --------
    >>> data = {"order_id": 1, "items": [{"sku": "A"}, {"sku": "B"}]}
    >>> flatten_records(data, explode_paths=["items"])
    [{'order_id': 1, 'items.sku': 'A'}, {'order_id': 1, 'items.sku': 'B'}]
    """
    records: List[Any]
    if isinstance(data, list):
        records = list(data)
    else:
        records = [data]

    if explode_paths:
        for path in explode_paths:
            if not isinstance(path, str) or not path:
                raise ValueError(f"explode_paths must contain non-empty strings, got {path!r}")
            records = _explode_at_path(records, path, sep)

    return [flatten_json(record, sep=sep, list_policy=list_policy) for record in records]


def _explode_at_path(records: Iterable[Any], path: str, sep: str = ".") -> List[Any]:
    """Explode records by replacing a list at path with individual items.
    
    Parameters
    ----------
    records : Iterable[Any]
        Records to explode.
    path : str
        Dot-delimited path to the list to explode.
    sep : str, optional
        Separator used in path (default: ".").
        
    Returns
    -------
    List[Any]
        Exploded records.
    """
    exploded: List[Any] = []
    for record in records:
        node = _get_by_path(record, path, sep)
        if isinstance(node, list):
            if not node:
                # Empty list: keep record but set path to None
                clone = copy.deepcopy(record)
                _set_by_path(clone, path, None, sep)
                exploded.append(clone)
                continue
            for item in node:
                clone = copy.deepcopy(record)
                _set_by_path(clone, path, item, sep)
                exploded.append(clone)
        else:
            exploded.append(record)
    return exploded


def _get_by_path(data: Any, path: str, sep: str = ".") -> Any:
    """Get value at dot-delimited path.
    
    Parameters
    ----------
    data : Any
        Data structure to traverse.
    path : str
        Dot-delimited path (e.g., "user.profile.name").
    sep : str, optional
        Separator used in path (default: ".").
        
    Returns
    -------
    Any
        Value at path, or None if path doesn't exist.
    """
    current = data
    for part in path.split(sep):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _set_by_path(data: Any, path: str, value: Any, sep: str = ".") -> None:
    """Set value at dot-delimited path, creating intermediate dicts as needed.
    
    Parameters
    ----------
    data : Any
        Data structure to modify.
    path : str
        Dot-delimited path (e.g., "user.profile.name").
    value : Any
        Value to set.
    sep : str, optional
        Separator used in path (default: ".").
    """
    if not isinstance(data, Mapping):
        return
        
    current = data
    parts = path.split(sep)
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], Mapping):
            current[part] = {}
        current = current[part]
        if not isinstance(current, Mapping):
            return
    if isinstance(current, Mapping):
        current[parts[-1]] = value
