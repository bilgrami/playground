"""Tests for JSON flattening functionality."""

import pytest

from json_flatten.flattener import flatten_json, flatten_records


def test_flatten_nested_dict() -> None:
    """Test flattening nested dictionaries."""
    data = {"a": {"b": 1}, "c": "x"}
    assert flatten_json(data) == {"a.b": 1, "c": "x"}


def test_flatten_list_index() -> None:
    """Test flattening lists with index policy."""
    data = {"tags": ["a", "b"]}
    assert flatten_json(data) == {"tags.0": "a", "tags.1": "b"}


def test_flatten_list_join() -> None:
    """Test flattening lists with join policy."""
    data = {"tags": ["a", "b"]}
    assert flatten_json(data, list_policy="join") == {"tags": "a,b"}


def test_flatten_list_join_with_none() -> None:
    """Test join policy with None values."""
    data = {"tags": ["a", None, "b"]}
    result = flatten_json(data, list_policy="join")
    assert result == {"tags": "a,,b"}


def test_flatten_records_explode() -> None:
    """Test exploding arrays into multiple records."""
    data = {"order_id": 1, "items": [{"sku": "A"}, {"sku": "B"}]}
    records = flatten_records(data, explode_paths=["items"])
    assert records == [
        {"order_id": 1, "items.sku": "A"},
        {"order_id": 1, "items.sku": "B"},
    ]


def test_flatten_records_multi_path_explode() -> None:
    """Test exploding multiple paths (cartesian product)."""
    data = {
        "order_id": 1,
        "items": [{"sku": "A"}, {"sku": "B"}],
        "discounts": [{"code": "X"}, {"code": "Y"}],
    }
    records = flatten_records(data, explode_paths=["items", "discounts"])
    assert len(records) == 4
    assert {"discounts.code": "X", "items.sku": "A", "order_id": 1} in records
    assert {"discounts.code": "Y", "items.sku": "A", "order_id": 1} in records
    assert {"discounts.code": "X", "items.sku": "B", "order_id": 1} in records
    assert {"discounts.code": "Y", "items.sku": "B", "order_id": 1} in records


def test_flatten_empty_list() -> None:
    """Test flattening empty lists."""
    data = {"items": []}
    result = flatten_json(data)
    assert result == {}


def test_flatten_none_value() -> None:
    """Test flattening None values."""
    data = {"field": None, "other": "value"}
    result = flatten_json(data)
    assert result == {"field": None, "other": "value"}


def test_flatten_deep_nesting() -> None:
    """Test flattening deeply nested structures."""
    data = {"a": {"b": {"c": {"d": {"e": 5}}}}}
    result = flatten_json(data)
    assert result == {"a.b.c.d.e": 5}


def test_flatten_mixed_types() -> None:
    """Test flattening structures with mixed types."""
    data = {
        "string": "text",
        "number": 42,
        "float": 3.14,
        "boolean": True,
        "null": None,
    }
    result = flatten_json(data)
    assert result["string"] == "text"
    assert result["number"] == 42
    assert result["float"] == 3.14
    assert result["boolean"] is True
    assert result["null"] is None


def test_flatten_invalid_list_policy() -> None:
    """Test that invalid list_policy raises ValueError."""
    data = {"tags": ["a", "b"]}
    with pytest.raises(ValueError, match="list_policy"):
        flatten_json(data, list_policy="invalid")


def test_flatten_records_empty_explode_paths() -> None:
    """Test flatten_records with empty explode_paths."""
    data = {"order_id": 1, "items": [{"sku": "A"}]}
    records = flatten_records(data, explode_paths=[])
    assert len(records) == 1
    assert "items.0.sku" in records[0]


def test_flatten_records_invalid_explode_path() -> None:
    """Test that invalid explode_path raises ValueError."""
    data = {"order_id": 1}
    with pytest.raises(ValueError, match="explode_paths"):
        flatten_records(data, explode_paths=[""])


def test_flatten_custom_separator() -> None:
    """Test flattening with custom separator."""
    data = {"a": {"b": 1}}
    result = flatten_json(data, sep="_")
    assert result == {"a_b": 1}
