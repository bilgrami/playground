"""Unit tests for collectors module."""

import pytest

from scripts.collectors import (
    filter_tables,
    matches_pattern,
    parse_desc_reduced,
    parse_show_reduced,
    parse_single_col_tsv,
    q_data_fingerprint,
    q_get_table_ddl,
    sql_like_to_fnmatch,
)


class TestQDataFingerprint:
    """Tests for q_data_fingerprint function."""

    def test_simple_table_name(self) -> None:
        """Test fingerprint query for simple table name."""
        query = q_data_fingerprint("MY_DB", "MY_SCHEMA", "MY_TABLE")
        assert '"MY_TABLE"' in query  # Quoted alias
        assert '"MY_DB"."MY_SCHEMA"."MY_TABLE"' in query  # Quoted FQ name
        assert "HASH_AGG(HASH" in query
        assert "COUNT(*)" in query

    def test_table_name_with_spaces(self) -> None:
        """Test fingerprint query handles table names with spaces."""
        query = q_data_fingerprint("MY_DB", "MY_SCHEMA", "MY TABLE")
        assert '"MY TABLE"' in query  # Must be quoted
        assert '"MY_DB"."MY_SCHEMA"."MY TABLE"' in query

    def test_table_name_with_special_chars(self) -> None:
        """Test fingerprint query handles special characters."""
        query = q_data_fingerprint("MY_DB", "MY_SCHEMA", "TABLE-WITH-DASHES")
        assert '"TABLE-WITH-DASHES"' in query
        # Query should be valid SQL with proper quoting
        assert 'FROM "MY_DB"."MY_SCHEMA"."TABLE-WITH-DASHES"' in query

    def test_reserved_word_table_name(self) -> None:
        """Test fingerprint query handles SQL reserved words."""
        query = q_data_fingerprint("MY_DB", "MY_SCHEMA", "SELECT")
        assert '"SELECT"' in query  # Must be quoted to avoid syntax error


class TestSqlLikeToFnmatch:
    """Tests for sql_like_to_fnmatch function."""

    def test_percent_to_asterisk(self) -> None:
        """Test SQL % becomes fnmatch *."""
        assert sql_like_to_fnmatch("FACT%") == "FACT*"
        assert sql_like_to_fnmatch("%TABLE") == "*TABLE"

    def test_underscore_to_question(self) -> None:
        """Test SQL _ becomes fnmatch ?."""
        assert sql_like_to_fnmatch("TABLE_A") == "TABLE?A"

    def test_combined_patterns(self) -> None:
        """Test combined patterns."""
        assert sql_like_to_fnmatch("%FACT_%") == "*FACT?*"


class TestMatchesPattern:
    """Tests for matches_pattern function."""

    def test_like_pattern_match(self) -> None:
        """Test LIKE-style pattern matching."""
        assert matches_pattern("FACT_SALES", "FACT_%")
        assert matches_pattern("DIM_CUSTOMER", "DIM_%")

    def test_like_pattern_no_match(self) -> None:
        """Test LIKE-style pattern non-match."""
        assert not matches_pattern("TMP_TABLE", "FACT_%")

    def test_regex_pattern_match(self) -> None:
        """Test regex pattern matching with re: prefix."""
        assert matches_pattern("FACT_SALES_2024", "re:^FACT_.*\\d{4}$")
        assert matches_pattern("ORDER_123", "re:ORDER_\\d+")

    def test_regex_pattern_no_match(self) -> None:
        """Test regex pattern non-match."""
        assert not matches_pattern("FACT_SALES", "re:^DIM_")

    def test_case_insensitive_by_default(self) -> None:
        """Test that pattern matching is case-insensitive by default."""
        # Lowercase pattern should match uppercase table name
        assert matches_pattern("FACT_SALES", "fact_%")
        # Uppercase pattern should match mixed case table name
        assert matches_pattern("Fact_Sales", "FACT_%")

    def test_case_sensitive_when_enabled(self) -> None:
        """Test case-sensitive matching when explicitly enabled."""
        # Should not match when case differs
        assert not matches_pattern("FACT_SALES", "fact_%", case_sensitive=True)
        # Should match when case matches
        assert matches_pattern("FACT_SALES", "FACT_%", case_sensitive=True)

    def test_regex_case_insensitive_by_default(self) -> None:
        """Test regex patterns are case-insensitive by default."""
        assert matches_pattern("FACT_SALES", "re:^fact_")
        assert matches_pattern("fact_sales", "re:^FACT_")

    def test_regex_case_sensitive_when_enabled(self) -> None:
        """Test regex patterns are case-sensitive when enabled."""
        assert not matches_pattern("FACT_SALES", "re:^fact_", case_sensitive=True)
        assert matches_pattern("fact_sales", "re:^fact_", case_sensitive=True)


class TestFilterTables:
    """Tests for filter_tables function."""

    def test_include_only(self) -> None:
        """Test filtering with include patterns only."""
        tables = ["FACT_A", "FACT_B", "DIM_C", "TMP_D"]
        result = filter_tables(tables, include=["FACT_%"], exclude=[])
        assert result == ["FACT_A", "FACT_B"]

    def test_exclude_only(self) -> None:
        """Test filtering with exclude patterns only."""
        tables = ["FACT_A", "FACT_B", "TMP_C", "TMP_D"]
        result = filter_tables(tables, include=[], exclude=["TMP_%"])
        assert result == ["FACT_A", "FACT_B"]

    def test_include_and_exclude(self) -> None:
        """Test filtering with both include and exclude."""
        tables = ["FACT_A", "FACT_TMP", "DIM_B", "TMP_C"]
        result = filter_tables(tables, include=["FACT_%", "DIM_%"], exclude=["%TMP%"])
        # FACT_TMP matches include but also matches exclude
        assert result == ["DIM_B", "FACT_A"]

    def test_empty_patterns_returns_all(self) -> None:
        """Test empty patterns return all tables."""
        tables = ["A", "B", "C"]
        result = filter_tables(tables, include=[], exclude=[])
        assert result == ["A", "B", "C"]

    def test_regex_patterns(self) -> None:
        """Test regex patterns in filter."""
        tables = ["FACT_2024", "FACT_2023", "DIM_OLD"]
        result = filter_tables(tables, include=["re:^FACT_\\d{4}$"], exclude=[])
        assert result == ["FACT_2023", "FACT_2024"]

    def test_case_insensitive_by_default(self) -> None:
        """Test case-insensitive filtering (default behavior)."""
        tables = ["FACT_SALES", "fact_orders", "DIM_CUSTOMER"]
        # Lowercase pattern should match all FACT tables regardless of case
        result = filter_tables(tables, include=["fact_%"], exclude=[])
        assert result == ["FACT_SALES", "fact_orders"]

    def test_case_sensitive_when_enabled(self) -> None:
        """Test case-sensitive filtering when explicitly enabled."""
        tables = ["FACT_SALES", "fact_orders", "DIM_CUSTOMER"]
        # Lowercase pattern should only match lowercase table
        result = filter_tables(tables, include=["fact_%"], exclude=[], case_sensitive=True)
        assert result == ["fact_orders"]


class TestParseShowReduced:
    """Tests for parse_show_reduced function."""

    def test_normal_output(self) -> None:
        """Test parsing normal SHOW output."""
        tsv = "TABLE1\tcol1\tcol2\nTABLE2\tcol1\tcol2\n"
        result = parse_show_reduced(tsv, "TABLE")
        assert "TABLE\tTABLE1" in result
        assert "TABLE\tTABLE2" in result

    def test_error_output(self) -> None:
        """Test parsing error output passes through."""
        tsv = "__ERROR__\t1\tSome error\n"
        result = parse_show_reduced(tsv, "TABLE")
        assert result == tsv

    def test_empty_output(self) -> None:
        """Test parsing empty output."""
        result = parse_show_reduced("", "TABLE")
        assert result == ""


class TestParseDescReduced:
    """Tests for parse_desc_reduced function."""

    def test_normal_output(self) -> None:
        """Test parsing normal DESC output."""
        tsv = "COL1\tVARCHAR\nCOL2\tINT\n"
        result = parse_desc_reduced(tsv, "MY_TABLE")
        assert "MY_TABLE\tCOL1" in result
        assert "MY_TABLE\tCOL2" in result

    def test_error_output(self) -> None:
        """Test parsing error output includes table name."""
        tsv = "__ERROR__\t1\tTable not found\n"
        result = parse_desc_reduced(tsv, "MISSING_TABLE")
        assert "MISSING_TABLE" in result
        assert "__ERROR__" in result


class TestParseSingleColTsv:
    """Tests for parse_single_col_tsv function."""

    def test_normal_input(self) -> None:
        """Test parsing single column TSV."""
        tsv = "VALUE1\nVALUE2\nVALUE3\n"
        result = parse_single_col_tsv(tsv)
        assert result == ["VALUE1", "VALUE2", "VALUE3"]

    def test_multicolumn_takes_first(self) -> None:
        """Test multi-column input takes first column."""
        tsv = "VALUE1\textra\nVALUE2\textra\n"
        result = parse_single_col_tsv(tsv)
        assert result == ["VALUE1", "VALUE2"]

    def test_empty_input(self) -> None:
        """Test empty input returns empty list."""
        assert parse_single_col_tsv("") == []
        assert parse_single_col_tsv("\n\n") == []
