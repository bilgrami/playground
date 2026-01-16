"""Integration tests for JSON flattening, CSV I/O, and database ingestion.

These tests verify end-to-end workflows including:
- JSON flattening to CSV
- CSV reading/writing
- MongoDB ingestion (when available)
- Snowflake integration (when available)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from json_flatten.csv_io import read_csv, write_csv
from json_flatten.flattener import flatten_json, flatten_records
from json_flatten.scenarios import get_scenarios


class TestCSVIntegration:
    """Integration tests for CSV read/write operations."""

    def test_write_and_read_csv(self, tmp_path: Path) -> None:
        """Test writing and reading CSV files."""
        records = [
            {"a": 1, "b": "x", "c": 3.14},
            {"a": 2, "b": "y", "c": 2.71},
            {"a": 3, "b": "z", "d": "extra"},  # Different keys
        ]
        
        output_path = tmp_path / "test.csv"
        write_csv(records, output_path)
        
        assert output_path.exists()
        
        read_records = read_csv(output_path)
        assert len(read_records) == 3
        assert read_records[0]["a"] == "1"  # CSV reads as strings
        assert read_records[0]["b"] == "x"
        assert read_records[2]["d"] == "extra"

    def test_empty_csv(self, tmp_path: Path) -> None:
        """Test writing empty CSV."""
        output_path = tmp_path / "empty.csv"
        write_csv([], output_path)
        
        assert output_path.exists()
        content = output_path.read_text()
        assert content == ""

    def test_csv_with_special_characters(self, tmp_path: Path) -> None:
        """Test CSV with special characters and commas."""
        records = [
            {"name": "John, Doe", "quote": 'He said "Hello"', "newline": "line1\nline2"},
        ]
        
        output_path = tmp_path / "special.csv"
        write_csv(records, output_path)
        
        read_records = read_csv(output_path)
        assert len(read_records) == 1
        assert "John, Doe" in read_records[0]["name"]


class TestFlatteningIntegration:
    """Integration tests for JSON flattening workflows."""

    def test_flatten_to_csv_workflow(self, tmp_path: Path) -> None:
        """Test complete workflow: JSON -> flatten -> CSV."""
        data = {
            "order": {"id": 42, "meta": {"source": "api"}},
            "customer": "acme",
            "tags": ["alpha", "beta"],
        }
        
        flattened = flatten_json(data)
        assert "order.id" in flattened
        assert "order.meta.source" in flattened
        assert "customer" in flattened
        
        output_path = tmp_path / "output.csv"
        write_csv([flattened], output_path)
        
        assert output_path.exists()
        read_records = read_csv(output_path)
        assert len(read_records) == 1
        assert read_records[0]["order.id"] == "42"

    def test_explode_to_csv_workflow(self, tmp_path: Path) -> None:
        """Test workflow with array explosion."""
        data = {
            "order_id": 1001,
            "items": [
                {"sku": "A1", "qty": 2},
                {"sku": "B2", "qty": 1},
            ],
        }
        
        records = flatten_records(data, explode_paths=["items"])
        assert len(records) == 2
        
        output_path = tmp_path / "exploded.csv"
        write_csv(records, output_path)
        
        read_records = read_csv(output_path)
        assert len(read_records) == 2
        assert read_records[0]["items.sku"] == "A1"
        assert read_records[1]["items.sku"] == "B2"

    def test_all_scenarios_to_csv(self, tmp_path: Path) -> None:
        """Test that all scenarios can be flattened and written to CSV."""
        scenarios = get_scenarios()
        
        for scenario in scenarios:
            scenario_dir = tmp_path / scenario.name
            scenario_dir.mkdir(parents=True, exist_ok=True)
            
            if scenario.mode == "records":
                records = flatten_records(
                    scenario.data,
                    explode_paths=scenario.explode_paths,
                    list_policy=scenario.list_policy,
                )
            else:
                records = [flatten_json(scenario.data, list_policy=scenario.list_policy)]
            
            output_path = scenario_dir / "output.csv"
            write_csv(records, output_path)
            
            assert output_path.exists()
            assert output_path.stat().st_size > 0


class TestMongoDBIntegration:
    """Integration tests for MongoDB ingestion (requires MongoDB running)."""

    @pytest.mark.skipif(
        "MONGO_URI" not in __import__("os").environ,
        reason="MongoDB not available",
    )
    def test_mongodb_ingestion(self, tmp_path: Path) -> None:
        """Test ingesting CSV records into MongoDB."""
        import os
        
        try:
            from json_flatten.mongodb_io import ingest_csv_to_mongodb, query_mongodb
        except ImportError:
            pytest.skip("pymongo not available")
        
        records = [
            {"order_id": "1", "customer": "Alice", "amount": "100.50"},
            {"order_id": "2", "customer": "Bob", "amount": "200.75"},
        ]
        
        output_path = tmp_path / "test.csv"
        write_csv(records, output_path)
        
        csv_records = read_csv(output_path)
        mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
        
        count = ingest_csv_to_mongodb(
            csv_records,
            mongo_uri=mongo_uri,
            database_name="test_flattening",
            collection_name="test_orders",
            drop_collection=True,
        )
        
        assert count == 2
        
        # Query back
        results = query_mongodb(
            mongo_uri=mongo_uri,
            database_name="test_flattening",
            collection_name="test_orders",
        )
        
        assert len(results) == 2
        assert results[0]["order_id"] == 1  # Type inference should convert to int
        assert results[0]["customer"] == "Alice"


class TestSnowflakeIntegration:
    """Integration tests for Snowflake ingestion (requires Snowflake credentials)."""

    @pytest.mark.skipif(
        "SNOWFLAKE_ACCOUNT" not in __import__("os").environ,
        reason="Snowflake credentials not available",
    )
    def test_snowflake_schema_generation(self) -> None:
        """Test Snowflake table schema generation."""
        try:
            from json_flatten.snowflake_io import create_table_schema
        except ImportError:
            pytest.skip("snowflake-connector-python not available")
        
        records = [
            {"id": 1, "name": "test", "price": 10.5, "active": True},
            {"id": 2, "name": "demo", "price": 20.0, "active": False},
        ]
        
        sql = create_table_schema(records, "test_table", "test_schema")
        
        assert "CREATE TABLE" in sql.upper()
        assert "test_schema.test_table" in sql
        assert "id" in sql
        assert "name" in sql
        assert "price" in sql
        assert "active" in sql


class TestComplexScenarios:
    """Tests for complex real-world scenarios."""

    def test_nested_arrays_scenario(self, tmp_path: Path) -> None:
        """Test scenario with nested arrays."""
        scenario = next(s for s in get_scenarios() if s.name == "nested_arrays")
        
        records = flatten_records(
            scenario.data,
            explode_paths=scenario.explode_paths,
        )
        
        assert len(records) == 2  # Two transactions
        
        output_path = tmp_path / "nested.csv"
        write_csv(records, output_path)
        
        read_records = read_csv(output_path)
        assert len(read_records) == 2
        assert "transactions.id" in read_records[0]
        assert "transactions.items.0.name" in read_records[0]

    def test_large_cartesian_product(self, tmp_path: Path) -> None:
        """Test large cartesian product scenario."""
        scenario = next(s for s in get_scenarios() if s.name == "large_cartesian_product")
        
        records = flatten_records(
            scenario.data,
            explode_paths=scenario.explode_paths,
        )
        
        # 3 products * 2 regions * 2 channels = 12 records
        assert len(records) == 12
        
        output_path = tmp_path / "cartesian.csv"
        write_csv(records, output_path)
        
        read_records = read_csv(output_path)
        assert len(read_records) == 12
        # All records should have batch_id
        assert all("batch_id" in r for r in read_records)
