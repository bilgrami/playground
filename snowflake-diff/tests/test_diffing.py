from pathlib import Path

from scripts.diffing import (
    md_anchor,
    read_text,
    rel_link,
    unified_diff,
    write_diff_file,
    write_text,
)


def test_read_text_missing_returns_empty(tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"
    assert read_text(missing) == ""


def test_write_text_normalizes_newlines(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    write_text(path, "a\r\nb\rc")
    assert read_text(path) == "a\nb\nc"


def test_unified_diff_includes_headers() -> None:
    diff = unified_diff("a\n", "b\n", "left", "right")
    assert diff.startswith("--- left")
    assert "+b" in diff


def test_write_diff_file_writes_when_different(tmp_path: Path) -> None:
    left = tmp_path / "left.txt"
    right = tmp_path / "right.txt"
    out_path = tmp_path / "out.diff"
    write_text(left, "left\n")
    write_text(right, "right\n")
    assert write_diff_file(out_path, left, right, "left", "right") is True
    assert out_path.exists()


def test_rel_link_and_md_anchor(tmp_path: Path) -> None:
    from_file = tmp_path / "summary" / "SUMMARY.md"
    to_file = tmp_path / "diffs" / "table.diff"
    from_file.parent.mkdir(parents=True)
    to_file.parent.mkdir(parents=True)
    assert rel_link(from_file, to_file).endswith("diffs/table.diff")
    assert md_anchor("Hello World!") == "hello-world"
