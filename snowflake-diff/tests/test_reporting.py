from pathlib import Path

from scripts.reporting import generate_summary_md


def test_generate_summary_md_writes_sections(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    diff_dir = out_dir / "diffs"
    diff_dir.mkdir(parents=True)
    diff_file = diff_dir / "table.diff"
    diff_file.write_text("--- left\n+++ right\n", encoding="utf-8")

    header_lines = ["- config: config.yml", "- left: dev", "- right: prod"]
    sections = [("Tables", [diff_file])]

    summary_path = generate_summary_md(out_dir, header_lines, sections)
    content = summary_path.read_text(encoding="utf-8")

    assert "# Snowflake Diff Summary" in content
    assert "## Tables" in content
    assert "table.diff" in content
