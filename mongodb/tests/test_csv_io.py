"""Tests for CSV I/O operations."""

from pathlib import Path

import pytest

from json_flatten.csv_io import read_csv, write_csv


def test_write_csv_writes_headers(tmp_path: Path) -> None:
    """Test that CSV writer includes headers."""
    output = tmp_path / "out.csv"
    write_csv([{"a": 1}, {"b": 2}], output)
    content = output.read_text(encoding="utf-8")
    assert content.splitlines()[0] == "a,b"


def test_write_csv_creates_directories(tmp_path: Path) -> None:
    """Test that CSV writer creates parent directories."""
    output = tmp_path / "nested" / "dir" / "out.csv"
    write_csv([{"a": 1}], output)
    assert output.exists()


def test_read_csv(tmp_path: Path) -> None:
    """Test reading CSV files."""
    output = tmp_path / "test.csv"
    write_csv([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}], output)
    
    records = read_csv(output)
    assert len(records) == 2
    assert records[0]["a"] == "1"  # CSV reads as strings
    assert records[0]["b"] == "x"


def test_read_csv_nonexistent(tmp_path: Path) -> None:
    """Test that reading nonexistent CSV raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        read_csv(tmp_path / "nonexistent.csv")


def test_write_csv_empty(tmp_path: Path) -> None:
    """Test writing empty CSV."""
    output = tmp_path / "empty.csv"
    write_csv([], output)
    assert output.exists()
    assert output.read_text() == ""
