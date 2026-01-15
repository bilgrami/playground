from pathlib import Path

from json_flatten.csv_io import write_csv


def test_write_csv_writes_headers(tmp_path: Path) -> None:
    output = tmp_path / "out.csv"
    write_csv([{"a": 1}, {"b": 2}], output)
    content = output.read_text(encoding="utf-8")
    assert content.splitlines()[0] == "a,b"
