from json_flatten.flattener import flatten_json, flatten_records


def test_flatten_nested_dict() -> None:
    data = {"a": {"b": 1}, "c": "x"}
    assert flatten_json(data) == {"a.b": 1, "c": "x"}


def test_flatten_list_index() -> None:
    data = {"tags": ["a", "b"]}
    assert flatten_json(data) == {"tags.0": "a", "tags.1": "b"}


def test_flatten_list_join() -> None:
    data = {"tags": ["a", "b"]}
    assert flatten_json(data, list_policy="join") == {"tags": "a,b"}


def test_flatten_records_explode() -> None:
    data = {"order_id": 1, "items": [{"sku": "A"}, {"sku": "B"}]}
    records = flatten_records(data, explode_paths=["items"])
    assert records == [
        {"order_id": 1, "items.sku": "A"},
        {"order_id": 1, "items.sku": "B"},
    ]


def test_flatten_records_multi_path_explode() -> None:
    data = {
        "order_id": 1,
        "items": [{"sku": "A"}, {"sku": "B"}],
        "discounts": [{"code": "X"}, {"code": "Y"}],
    }
    records = flatten_records(data, explode_paths=["items", "discounts"])
    assert records == [
        {"discounts.code": "X", "items.sku": "A", "order_id": 1},
        {"discounts.code": "Y", "items.sku": "A", "order_id": 1},
        {"discounts.code": "X", "items.sku": "B", "order_id": 1},
        {"discounts.code": "Y", "items.sku": "B", "order_id": 1},
    ]
