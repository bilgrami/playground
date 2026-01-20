"""Unit tests for auth module."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from scripts.auth import DEFAULT_TIMEOUT_SECONDS, SnowTarget, run_sql


@pytest.fixture
def mock_target() -> SnowTarget:
    """Create a mock SnowTarget for testing."""
    return SnowTarget(
        connection="test_conn",
        role="TEST_ROLE",
        warehouse="TEST_WH",
        database="TEST_DB",
        schema="TEST_SCHEMA",
        label="test",
    )


class TestRunSql:
    """Tests for run_sql function."""

    def test_run_sql_success(self, mock_target: SnowTarget) -> None:
        """Test successful SQL execution returns TSV output."""
        with patch("scripts.auth.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="col1\tcol2\nval1\tval2\n",
                stderr="",
            )
            result = run_sql(mock_target, "SELECT 1")
            assert result == "col1\tcol2\nval1\tval2\n"
            mock_run.assert_called_once()

    def test_run_sql_error_returns_error_sentinel(self, mock_target: SnowTarget) -> None:
        """Test failed SQL execution returns __ERROR__ sentinel."""
        with patch("scripts.auth.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="SQL compilation error",
            )
            result = run_sql(mock_target, "SELECT bad_syntax")
            assert result.startswith("__ERROR__")
            assert "1" in result
            assert "SQL compilation error" in result

    def test_run_sql_timeout_returns_error_sentinel(self, mock_target: SnowTarget) -> None:
        """Test query timeout returns __ERROR__ sentinel with TIMEOUT."""
        with patch("scripts.auth.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="snow", timeout=30)
            result = run_sql(mock_target, "SELECT * FROM huge_table", timeout=30)
            assert result.startswith("__ERROR__")
            assert "TIMEOUT" in result
            assert "30 seconds" in result

    def test_run_sql_uses_default_timeout(self, mock_target: SnowTarget) -> None:
        """Test run_sql uses default timeout when not specified."""
        with patch("scripts.auth.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            run_sql(mock_target, "SELECT 1")
            # Verify timeout was passed to subprocess.run
            call_kwargs = mock_run.call_args.kwargs
            assert call_kwargs.get("timeout") == DEFAULT_TIMEOUT_SECONDS

    def test_run_sql_custom_timeout(self, mock_target: SnowTarget) -> None:
        """Test run_sql uses custom timeout when specified."""
        with patch("scripts.auth.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            run_sql(mock_target, "SELECT 1", timeout=60)
            call_kwargs = mock_run.call_args.kwargs
            assert call_kwargs.get("timeout") == 60

    def test_run_sql_normalizes_newlines(self, mock_target: SnowTarget) -> None:
        """Test that Windows-style newlines are normalized."""
        with patch("scripts.auth.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="line1\r\nline2\rline3\n",
                stderr="",
            )
            result = run_sql(mock_target, "SELECT 1")
            assert result == "line1\nline2\nline3\n"
            assert "\r" not in result
